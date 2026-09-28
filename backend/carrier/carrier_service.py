import hmac
import hashlib
import time
import secrets
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from backend.config import Config
from backend.chain.mst_client import mst_client

class CarrierService:
    """
    Carrier A Core Simulator & Signing Gateway.
    Protects user PII by tokenizing phone numbers with HMAC-SHA256.
    """

    def __init__(self, carrier_id: str = "carrier-a", secret_key: str = None, signing_key: str = None):
        self.carrier_id = carrier_id
        self.secret_key = (secret_key or Config.CARRIER_A_TOKEN_KEY).encode("utf-8")
        self.signing_key = signing_key or Config.CARRIER_A_SIGNING_KEY
        self.account = Account.from_key(self.signing_key)
        self.address = self.account.address

    def compute_token(self, phone_number: str) -> bytes:
        """
        Computes HMAC-SHA256(carrier_key, E.164 phone_number).
        Protects user PII while allowing consortium banks with the shared key to perform lookups.
        """
        clean_number = phone_number.strip().replace(" ", "").replace("-", "")
        return hmac.new(self.secret_key, clean_number.encode("utf-8"), hashlib.sha256).digest()

    def get_token_hex(self, phone_number: str) -> str:
        return "0x" + self.compute_token(phone_number).hex()

    def register_pre_notification(self, phone_number: str, duration_seconds: int = 86400) -> dict:
        """
        Registers an authorized customer pre-notification before a legitimate SIM swap.
        """
        token = self.compute_token(phone_number)
        result = mst_client.register_pre_notification(token, self.carrier_id, duration_seconds)
        return {
            "status": "success",
            "carrier_id": self.carrier_id,
            "token": self.get_token_hex(phone_number),
            "phone_masked": self._mask_phone(phone_number),
            "duration_seconds": duration_seconds,
            "result": result
        }

    def record_sim_event(
        self,
        phone_number: str,
        event_type: str = "SIM_SWAP",
        pre_notified: bool = False,
        notification_ref: str = None
    ) -> dict:
        """
        Processes a SIM lifecycle event: tokenizes number, signs payload, and broadcasts to MST Blockchain.
        """
        token = self.compute_token(phone_number)
        timestamp = int(time.time())
        nonce = secrets.token_bytes(32)

        # Create signable payload hash
        # message: token + carrierId + eventType + timestamp + preNotified + nonce
        message_bytes = (
            token +
            self.carrier_id.encode("utf-8") +
            event_type.encode("utf-8") +
            timestamp.to_bytes(32, "big") +
            (1 if pre_notified else 0).to_bytes(1, "big") +
            nonce
        )
        msg_hash = Web3.keccak(message_bytes)
        signable_msg = encode_defunct(primitive=msg_hash)
        signed = self.account.sign_message(signable_msg)

        # Broadcast to MST Blockchain
        chain_result = mst_client.record_swap_event(
            token_bytes=token,
            carrier_id=self.carrier_id,
            event_type=event_type,
            timestamp=timestamp,
            pre_notified=pre_notified,
            notification_ref=notification_ref or "",
            nonce_bytes=nonce,
            signature_bytes=signed.signature,
            private_key=self.signing_key
        )

        return {
            "status": "success",
            "event_type": event_type,
            "carrier_id": self.carrier_id,
            "phone_masked": self._mask_phone(phone_number),
            "token": "0x" + token.hex(),
            "timestamp": timestamp,
            "pre_notified": chain_result.get("pre_notified", pre_notified),
            "tx_hash": chain_result["tx_hash"],
            "block_timestamp": chain_result["block_timestamp"]
        }

    def _mask_phone(self, phone: str) -> str:
        clean = phone.strip()
        if len(clean) > 4:
            return clean[:3] + "******" + clean[-2:]
        return "***"

carrier_service = CarrierService()
