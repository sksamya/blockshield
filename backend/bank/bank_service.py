import time
import secrets
from backend.carrier.carrier_service import carrier_service
from backend.bank.risk_engine import RiskEngine
from backend.bank.decision_logger import DecisionLogger
from backend.wallet.bridgekey import bridgekey_service

class BankService:
    """
    Bank Service Instance (Deployed for Bank B and Bank C).
    Implements Auth Gateway, Risk Scoring, BridgeKey Signer Challenges, Decision Anchoring, and Victim Alerts.
    """

    def __init__(self, bank_id: str = "bank-b", bank_name: str = "Bank B"):
        self.bank_id = bank_id
        self.bank_name = bank_name
        self.risk_engine = RiskEngine()
        self.decision_logger = DecisionLogger(bank_id=bank_id)

        # Mock customer accounts
        self.customers = {
            "cust_victim": {
                "id": "cust_victim",
                "name": "Alice Johnson",
                "phone": "+15551234567",
                "email": "alice@example.com",
                "account_number": "ACC-987654",
                "balance_cents": 2500000, # $25,000.00
                "enrolled_device": "device_alice_iphone",
                "wallet_address": "0xe62307B28F3130Db729C05D47b701160FD8b13b5",
                "password_hash": "mock_hash_123",
                "last_password_reset": 0
            },
            "cust_legit": {
                "id": "cust_legit",
                "name": "Bob Smith",
                "phone": "+15559876543",
                "email": "bob@example.com",
                "account_number": "ACC-123456",
                "balance_cents": 1000000, # $10,000.00
                "enrolled_device": "device_bob_pixel",
                "wallet_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                "password_hash": "mock_hash_456",
                "last_password_reset": 0
            }
        }

        # Stored transaction & transfer attempts: tx_id -> dict
        self.transfers = {}
        # Outbound victim alerts / email notifications log
        self.sent_alerts = []

    def get_customer(self, customer_id: str) -> dict | None:
        return self.customers.get(customer_id)

    def request_password_reset(
        self,
        phone_number: str,
        device_id: str = "unknown_device",
        ip_location: str = "unrecognized_location"
    ) -> dict:
        """
        Processes a password reset attempt.
        Evaluates on-chain swap events; refuses SMS OTP if a recent SIM swap occurred.
        """
        # Find customer by phone
        customer = next((c for c in self.customers.values() if c["phone"] == phone_number), None)
        if not customer:
            return {"status": "failed", "error": "Customer not found"}

        phone_token = carrier_service.compute_token(phone_number)
        event_ref = f"reset_{secrets.token_hex(8)}"

        risk = self.risk_engine.evaluate_transaction(
            customer_id=customer["id"],
            phone_token=phone_token,
            amount_cents=0,
            destination_account_token=None,
            is_new_device=(device_id != customer["enrolled_device"]),
            is_unusual_location=True,
            had_recent_password_reset=False
        )

        # Anchor decision on MST Blockchain
        anchor = self.decision_logger.log_and_anchor_decision(
            event_ref=event_ref,
            customer_id=customer["id"],
            transaction_type="PASSWORD_RESET_REQUEST",
            risk_evaluation=risk,
            action_taken=risk["action"],
            additional_metadata={"device_id": device_id, "ip_location": ip_location}
        )

        if not risk["sms_otp_allowed"]:
            self._dispatch_victim_alert(
                customer=customer,
                subject=f"CRITICAL SECURITY ALERT from {self.bank_name}",
                body=f"A password reset was attempted after a SIM swap was detected on your carrier. SMS OTP has been disabled."
            )

        return {
            "bank_id": self.bank_id,
            "customer_id": customer["id"],
            "event_ref": event_ref,
            "risk_evaluation": risk,
            "sms_otp_allowed": risk["sms_otp_allowed"],
            "requires_bridgekey": risk["requires_bridgekey"],
            "decision_anchor": anchor
        }

    def initiate_transfer(
        self,
        customer_id: str,
        recipient_account: str,
        amount_cents: int,
        device_id: str,
        ip_location: str,
        had_recent_password_reset: bool = False
    ) -> dict:
        """
        Initiates a funds transfer.
        Runs full risk evaluation, checks MST swap and fraud registries, and anchors the outcome.
        """
        customer = self.customers.get(customer_id)
        if not customer:
            return {"status": "failed", "error": "Customer account not found"}

        transfer_id = f"tx_{secrets.token_hex(8)}"
        phone_token = carrier_service.compute_token(customer["phone"])
        recipient_token = carrier_service.compute_token(recipient_account)

        risk = self.risk_engine.evaluate_transaction(
            customer_id=customer_id,
            phone_token=phone_token,
            amount_cents=amount_cents,
            destination_account_token=recipient_token,
            is_new_device=(device_id != customer["enrolled_device"]),
            is_unusual_location=(ip_location != "usual_home_location"),
            had_recent_password_reset=had_recent_password_reset
        )

        transfer_record = {
            "transfer_id": transfer_id,
            "bank_id": self.bank_id,
            "customer_id": customer_id,
            "recipient_account": recipient_account,
            "amount_cents": amount_cents,
            "amount_formatted": f"${amount_cents / 100:.2f}",
            "device_id": device_id,
            "ip_location": ip_location,
            "risk_evaluation": risk,
            "status": "PENDING_VERIFICATION" if risk["requires_bridgekey"] else ("BLOCKED" if risk["action"] == "BLOCK" else "APPROVED"),
            "timestamp": int(time.time())
        }

        # Anchor decision on MST Blockchain
        anchor = self.decision_logger.log_and_anchor_decision(
            event_ref=transfer_id,
            customer_id=customer_id,
            transaction_type="FUNDS_TRANSFER",
            risk_evaluation=risk,
            action_taken=transfer_record["status"],
            additional_metadata={"amount_cents": amount_cents, "recipient": recipient_account}
        )

        transfer_record["decision_anchor"] = anchor
        self.transfers[transfer_id] = transfer_record

        # Handle Step-Up or Block
        challenge_info = None
        if risk["requires_bridgekey"]:
            challenge_info = bridgekey_service.create_challenge(
                customer_id=customer_id,
                action="AUTHORIZE_TRANSFER",
                details={
                    "transfer_id": transfer_id,
                    "bank_id": self.bank_id,
                    "amount": f"${amount_cents / 100:.2f}",
                    "recipient": recipient_account
                }
            )
            transfer_record["challenge_id"] = challenge_info["challenge_id"]

        if risk["action"] in ["BLOCK", "STEP_UP_BRIDGEKEY"]:
            self._dispatch_victim_alert(
                customer=customer,
                subject=f"Suspicious Transaction Alert ({self.bank_name})",
                body=f"A transfer of ${amount_cents / 100:.2f} was flagged. Risk score: {risk['risk_score']}. Action: {risk['action']}."
            )

        return {
            "transfer_id": transfer_id,
            "bank_id": self.bank_id,
            "status": transfer_record["status"],
            "risk_score": risk["risk_score"],
            "action": risk["action"],
            "requires_bridgekey": risk["requires_bridgekey"],
            "challenge": challenge_info,
            "decision_anchor": anchor,
            "factors": risk["factors"],
            # Fields required by the frontend
            "wallet_address": customer.get("wallet_address", ""),
            "customer_display_id": customer.get("name", customer_id),
            "risk_reason": risk.get("reason", ""),
            "has_mule_flag": risk.get("is_destination_mule", False),
            "anchor_hash": anchor.get("decision_hash", "")
        }

    def complete_bridgekey_step_up(self, transfer_id: str, signature_hex: str) -> dict:
        """
        Validates BridgeKey biometric signature and finalizes the transfer.
        """
        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return {"status": "failed", "error": "Transfer record not found"}

        challenge_id = transfer.get("challenge_id")
        if not challenge_id:
            return {"status": "failed", "error": "No BridgeKey challenge attached to this transfer"}

        is_valid, msg = bridgekey_service.verify_signature(challenge_id, signature_hex)

        if is_valid:
            transfer["status"] = "APPROVED_BY_BRIDGEKEY"
            transfer["completed_at"] = int(time.time())
            
            # Re-anchor the step-up success decision
            anchor = self.decision_logger.log_and_anchor_decision(
                event_ref=f"{transfer_id}_stepup_complete",
                customer_id=transfer["customer_id"],
                transaction_type="BRIDGEKEY_STEP_UP_COMPLETED",
                risk_evaluation={"status": "verified"},
                action_taken="APPROVED_BY_BRIDGEKEY",
                additional_metadata={"transfer_id": transfer_id, "signature": signature_hex}
            )
            transfer["step_up_anchor"] = anchor

            return {
                "status": "success",
                "transfer_id": transfer_id,
                "transfer_status": "APPROVED_BY_BRIDGEKEY",
                "message": "Biometric verification successful. Transfer executed.",
                "anchor": anchor
            }
        else:
            transfer["status"] = "BLOCKED_FAILED_SIGNATURE"
            return {
                "status": "failed",
                "transfer_id": transfer_id,
                "transfer_status": "BLOCKED_FAILED_SIGNATURE",
                "error": msg
            }

    def _dispatch_victim_alert(self, customer: dict, subject: str, body: str):
        alert = {
            "alert_id": f"alt_{secrets.token_hex(6)}",
            "bank_id": self.bank_id,
            "recipient_email": customer["email"],
            "recipient_phone": customer["phone"],
            "subject": subject,
            "body": body,
            "timestamp": int(time.time())
        }
        self.sent_alerts.append(alert)
        return alert

# Factory instances for Bank B and Bank C
bank_b_service = BankService(bank_id="bank-b", bank_name="Bank B")
bank_c_service = BankService(bank_id="bank-c", bank_name="Bank C")
