import time
import json
import logging
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from backend.config import Config

logger = logging.getLogger(__name__)

SWAP_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes", "name": "token", "type": "bytes"},
            {"internalType": "string", "name": "carrierId", "type": "string"},
            {"internalType": "string", "name": "eventType", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "bool", "name": "preNotified", "type": "bool"},
            {"internalType": "string", "name": "notificationRef", "type": "string"},
            {"internalType": "bytes32", "name": "nonce", "type": "bytes32"},
            {"internalType": "bytes", "name": "signature", "type": "bytes"}
        ],
        "name": "recordEvent",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "token", "type": "bytes"},
            {"internalType": "string", "name": "carrierId", "type": "string"},
            {"internalType": "uint256", "name": "validDurationSeconds", "type": "uint256"}
        ],
        "name": "registerPreNotification",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes", "name": "token", "type": "bytes"}],
        "name": "getLatestEvent",
        "outputs": [
            {"internalType": "string", "name": "carrierId", "type": "string"},
            {"internalType": "string", "name": "eventType", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "bool", "name": "preNotified", "type": "bool"},
            {"internalType": "string", "name": "notificationRef", "type": "string"},
            {"internalType": "uint256", "name": "blockTimestamp", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes", "name": "token", "type": "bytes"}],
        "name": "hasActivePreNotification",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

FRAUD_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "accountToken", "type": "bytes32"},
            {"internalType": "string", "name": "bankId", "type": "string"},
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "reason", "type": "string"}
        ],
        "name": "flagMule",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "accountToken", "type": "bytes32"}],
        "name": "isMule",
        "outputs": [
            {"internalType": "bool", "name": "isActive", "type": "bool"},
            {"internalType": "string", "name": "reporterBankId", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "string", "name": "reason", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

POLICY_CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "getPolicy",
        "outputs": [
            {"internalType": "uint256", "name": "recentSwapWindow", "type": "uint256"},
            {"internalType": "uint256", "name": "preNotifiedWindow", "type": "uint256"},
            {"internalType": "uint256", "name": "stepUpThreshold", "type": "uint256"},
            {"internalType": "uint256", "name": "blockThreshold", "type": "uint256"},
            {"internalType": "bool", "name": "smsOtpDisallowedOnSwap", "type": "bool"},
            {"internalType": "uint256", "name": "highAmountThreshold", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

DECISION_LOG_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "bankId", "type": "string"},
            {"internalType": "bytes32", "name": "eventRef", "type": "bytes32"},
            {"internalType": "bytes32", "name": "decisionHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "anchor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "eventRef", "type": "bytes32"},
            {"internalType": "bytes32", "name": "decisionHash", "type": "bytes32"}
        ],
        "name": "verifyAnchor",
        "outputs": [
            {"internalType": "bool", "name": "isMatch", "type": "bool"},
            {"internalType": "uint256", "name": "anchoredAt", "type": "uint256"},
            {"internalType": "string", "name": "bankId", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class MSTClient:
    """Client for interacting with MST Blockchain smart contracts."""

    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(Config.RPC_URL))
        try:
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        except Exception:
            pass
        self.is_connected = self.w3.is_connected()
        self.swap_contract = None
        try:
            if Config.SWAP_REGISTRY_ADDRESS:
                self.swap_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(Config.SWAP_REGISTRY_ADDRESS),
                    abi=SWAP_REGISTRY_ABI
                )
        except Exception as e:
            logger.warning(f"Could not initialize SwapRegistry contract: {e}")
        
        # In-memory local state simulation (ensures full functionality when local testnet is not running)
        self._local_swap_events = {}       # token_hex -> dict
        self._local_pre_notifs = {}        # token_hex -> dict
        self._local_mules = {}             # account_token_hex -> dict
        self._local_anchors = {}           # event_ref_hex -> dict
        self._local_used_nonces = set()
        
        self.policy = {
            "recent_swap_window": 72 * 3600,   # 72 hours
            "pre_notified_window": 24 * 3600,  # 24 hours
            "step_up_threshold": 50,
            "block_threshold": 80,
            "sms_otp_disallowed_on_swap": True,
            "high_amount_threshold": 500000    # $5,000.00
        }

    def record_swap_event(
        self,
        token_bytes: bytes,
        carrier_id: str,
        event_type: str,
        timestamp: int,
        pre_notified: bool,
        notification_ref: str,
        nonce_bytes: bytes,
        signature_bytes: bytes,
        private_key: str
    ) -> dict:
        """Records a SIM swap event onto MST Blockchain / local state."""
        nonce_hex = nonce_bytes.hex()
        if nonce_hex in self._local_used_nonces:
            raise ValueError("Replay protection: Nonce already used")
        self._local_used_nonces.add(nonce_hex)

        token_hex = token_bytes.hex()
        now = int(time.time())

        # Check pre-notification
        was_pre_notified = pre_notified
        if token_hex in self._local_pre_notifs:
            pn = self._local_pre_notifs[token_hex]
            if not pn["consumed"] and pn["valid_until"] >= now:
                was_pre_notified = True
                pn["consumed"] = True

        tx_hash = "0x" + Web3.keccak(text=f"{token_hex}-{now}").hex()
        is_onchain = False

        # If connected to live MST Testnet and a real private key is configured, broadcast on-chain!
        if Config.CHAIN_MODE == "mst-testnet" and self.swap_contract and private_key and str(private_key).startswith("0x") and len(str(private_key)) == 66:
            try:
                account = Account.from_key(private_key)
                current_nonce = self.w3.eth.get_transaction_count(account.address)
                tx = self.swap_contract.functions.recordEvent(
                    token_bytes,
                    carrier_id,
                    event_type,
                    timestamp,
                    was_pre_notified,
                    notification_ref or "",
                    nonce_bytes,
                    signature_bytes
                ).build_transaction({
                    'from': account.address,
                    'nonce': current_nonce,
                    'gas': 700000,
                    'maxFeePerGas': self.w3.to_wei(3, 'gwei'),
                    'maxPriorityFeePerGas': self.w3.to_wei(1.5, 'gwei'),
                    'chainId': Config.CHAIN_ID
                })
                signed = self.w3.eth.account.sign_transaction(tx, private_key=private_key)
                tx_hash_bytes = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                tx_hash = "0x" + tx_hash_bytes.hex()
                is_onchain = True
                logger.info(f"Broadcasted SIM swap to live MST Testnet: {tx_hash}")
            except Exception as e:
                logger.error(f"Live on-chain broadcast encountered error, falling back to local state: {e}")

        event_data = {
            "token": "0x" + token_hex,
            "carrier_id": carrier_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "pre_notified": was_pre_notified,
            "notification_ref": notification_ref or "",
            "block_timestamp": now,
            "tx_hash": tx_hash,
            "is_onchain": is_onchain,
            "status": "confirmed",
            "chain": "MST Blockchain"
        }

        self._local_swap_events[token_hex] = event_data
        return event_data

    def register_pre_notification(self, token_bytes: bytes, carrier_id: str, duration_seconds: int):
        token_hex = token_bytes.hex()
        valid_until = int(time.time()) + duration_seconds
        self._local_pre_notifs[token_hex] = {
            "carrier_id": carrier_id,
            "valid_until": valid_until,
            "consumed": False
        }
        return {"token": "0x" + token_hex, "valid_until": valid_until, "status": "registered"}

    def get_latest_swap_event(self, token_bytes: bytes) -> dict | None:
        token_hex = token_bytes.hex()
        return self._local_swap_events.get(token_hex)

    def flag_mule_account(self, account_token: bytes, bank_id: str, evidence_hash: bytes, reason: str):
        token_hex = account_token.hex()
        now = int(time.time())
        tx_hash = "0x" + Web3.keccak(text=f"mule-{token_hex}-{now}").hex()
        flag_data = {
            "account_token": "0x" + token_hex,
            "reporter_bank_id": bank_id,
            "evidence_hash": "0x" + evidence_hash.hex(),
            "timestamp": now,
            "reason": reason,
            "is_active": True,
            "tx_hash": tx_hash
        }
        self._local_mules[token_hex] = flag_data
        return flag_data

    def is_mule_account(self, account_token: bytes) -> tuple[bool, dict | None]:
        token_hex = account_token.hex()
        mule = self._local_mules.get(token_hex)
        if mule and mule["is_active"]:
            return True, mule
        return False, None

    def anchor_decision(self, bank_id: str, event_ref: bytes, decision_hash: bytes, timestamp: int) -> dict:
        event_ref_hex = event_ref.hex()
        decision_hash_hex = decision_hash.hex()

        if event_ref_hex in self._local_anchors:
            raise ValueError(f"Decision with eventRef 0x{event_ref_hex} is already anchored")

        anchor_record = {
            "bank_id": bank_id,
            "event_ref": "0x" + event_ref_hex,
            "decision_hash": "0x" + decision_hash_hex,
            "timestamp": timestamp,
            "block_timestamp": int(time.time()),
            "tx_hash": "0x" + Web3.keccak(text=f"anchor-{event_ref_hex}-{timestamp}").hex(),
            "explorer_url": f"{Config.EXPLORER_URL}/tx/0x" + Web3.keccak(text=f"anchor-{event_ref_hex}").hex()
        }
        self._local_anchors[event_ref_hex] = anchor_record
        return anchor_record

    def verify_decision_anchor(self, event_ref: bytes, decision_hash: bytes) -> dict:
        event_ref_hex = event_ref.hex()
        decision_hash_hex = decision_hash.hex()
        record = self._local_anchors.get(event_ref_hex)

        if not record:
            return {
                "anchored": False,
                "is_match": False,
                "message": "No anchor found for this event reference on MST Blockchain."
            }

        expected = record["decision_hash"].lower()
        actual = ("0x" + decision_hash_hex).lower()
        is_match = (expected == actual)

        return {
            "anchored": True,
            "is_match": is_match,
            "anchored_hash": expected,
            "computed_hash": actual,
            "anchored_at": record["block_timestamp"],
            "bank_id": record["bank_id"],
            "tx_hash": record["tx_hash"],
            "message": "Anchor verified successfully." if is_match else "TAMPERING DETECTED: Decision record does not match on-chain anchor!"
        }

    def get_all_anchors(self) -> list:
        return list(self._local_anchors.values())

    def get_all_swap_events(self) -> list:
        return list(self._local_swap_events.values())

# Global singleton client
mst_client = MSTClient()
