import time
import secrets
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

class BridgeKeyService:
    """
    BridgeKey Biometric Wallet Integration & Signer Verification.
    BridgeKey is a non-custodial wallet on MST Blockchain with biometric unlock.
    """

    def __init__(self):
        # In-memory storage for active challenges: challenge_id -> challenge_dict
        self._active_challenges = {}
        # Registered customer wallet address bindings: account_id -> wallet_address
        self._enrolled_wallets = {
            "cust_101": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "cust_102": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
            "cust_victim": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
            "cust_legit": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        }

    def enroll_wallet(self, customer_id: str, wallet_address: str):
        """Binds a customer bank account with their BridgeKey wallet address upon KYC."""
        checksummed = Web3.to_checksum_address(wallet_address)
        self._enrolled_wallets[customer_id] = checksummed
        return {"customer_id": customer_id, "wallet_address": checksummed, "status": "enrolled"}

    def get_enrolled_wallet(self, customer_id: str) -> str | None:
        return self._enrolled_wallets.get(customer_id)

    def create_challenge(self, customer_id: str, action: str, details: dict) -> dict:
        """
        Creates an on-device authentication challenge for BridgeKey.
        Includes a cryptographic nonce, timestamp, and human-readable context.
        """
        enrolled_wallet = self.get_enrolled_wallet(customer_id)
        if not enrolled_wallet:
            raise ValueError(f"No enrolled BridgeKey wallet found for customer {customer_id}")

        challenge_id = "bk_" + secrets.token_hex(16)
        nonce = secrets.token_hex(16)
        timestamp = int(time.time())

        # Construct deterministic message for signing
        message_text = (
            f"BlockShield Security Challenge\n"
            f"Action: {action}\n"
            f"Customer: {customer_id}\n"
            f"Details: {details}\n"
            f"Nonce: {nonce}\n"
            f"Timestamp: {timestamp}\n"
            f"Chain: MST Blockchain"
        )

        challenge = {
            "challenge_id": challenge_id,
            "customer_id": customer_id,
            "wallet_address": enrolled_wallet,
            "action": action,
            "details": details,
            "nonce": nonce,
            "timestamp": timestamp,
            "expires_at": timestamp + 300, # 5 minutes
            "message_text": message_text,
            "status": "pending"
        }

        self._active_challenges[challenge_id] = challenge
        return challenge

    def verify_signature(self, challenge_id: str, signature_hex: str) -> tuple[bool, str]:
        """
        Verifies an EIP-191 signature produced by the BridgeKey device.
        """
        challenge = self._active_challenges.get(challenge_id)
        if not challenge:
            return False, "Challenge not found or expired"

        if int(time.time()) > challenge["expires_at"]:
            challenge["status"] = "expired"
            return False, "Challenge has expired"

        expected_wallet = challenge["wallet_address"]
        message_text = challenge["message_text"]

        try:
            signable_message = encode_defunct(text=message_text)
            recovered_address = Account.recover_message(signable_message, signature=signature_hex)
            
            if Web3.to_checksum_address(recovered_address) == Web3.to_checksum_address(expected_wallet):
                challenge["status"] = "verified"
                challenge["verified_at"] = int(time.time())
                return True, "Signature verified successfully"
            else:
                return False, f"Signature mismatch: recovered {recovered_address}, expected {expected_wallet}"
        except Exception as e:
            return False, f"Signature verification failed: {str(e)}"

    def sign_with_test_wallet(self, challenge_id: str, private_key: str) -> str:
        """
        Helper method for CI and automated simulation testing:
        Produces a valid EIP-191 signature using a test private key.
        """
        challenge = self._active_challenges.get(challenge_id)
        if not challenge:
            raise ValueError("Challenge not found")

        message_text = challenge["message_text"]
        signable_message = encode_defunct(text=message_text)
        account = Account.from_key(private_key)
        signed = account.sign_message(signable_message)
        sig_hex = signed.signature.hex()
        return "0x" + sig_hex if not sig_hex.startswith("0x") else sig_hex

bridgekey_service = BridgeKeyService()
