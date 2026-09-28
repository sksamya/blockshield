import time
from backend.chain.mst_client import mst_client

class RiskEngine:
    """
    Multi-factor fraud detection & risk evaluation engine.
    Cross-references on-chain swap events from MST Blockchain with bank-level behavioral signals.
    """

    def __init__(self, policy: dict = None):
        self.policy = policy or mst_client.policy

    def evaluate_transaction(
        self,
        customer_id: str,
        phone_token: bytes,
        amount_cents: int,
        destination_account_token: bytes | None,
        is_new_device: bool = False,
        is_unusual_location: bool = False,
        had_recent_password_reset: bool = False
    ) -> dict:
        score = 0
        factors = []
        now = int(time.time())

        # 1. On-chain Swap Registry Check
        swap_event = mst_client.get_latest_swap_event(phone_token)
        swap_detected = False
        is_pre_notified = False
        swap_age_hours = None

        if swap_event:
            swap_timestamp = swap_event["timestamp"]
            age_seconds = now - swap_timestamp
            swap_age_hours = round(age_seconds / 3600, 1)
            is_pre_notified = swap_event.get("pre_notified", False)

            if age_seconds <= self.policy["recent_swap_window"]:
                swap_detected = True
                if is_pre_notified:
                    score += 15
                    factors.append({
                        "factor": "RECENT_SWAP_PRE_NOTIFIED",
                        "weight": 15,
                        "description": f"Pre-notified SIM swap detected {swap_age_hours}h ago (Lower risk policy applied)."
                    })
                else:
                    score += 55
                    factors.append({
                        "factor": "RECENT_UNNOTIFIED_SWAP",
                        "weight": 55,
                        "description": f"CRITICAL: Un-notified SIM swap detected on MST Blockchain {swap_age_hours}h ago."
                    })
            else:
                factors.append({
                    "factor": "HISTORICAL_SWAP_OUTSIDE_WINDOW",
                    "weight": 0,
                    "description": f"Historical swap was {swap_age_hours}h ago (Outside 72h window, no extra risk)."
                })

        # 2. Behavioral Factors
        if is_new_device:
            score += 20
            factors.append({
                "factor": "UNKNOWN_DEVICE",
                "weight": 20,
                "description": "Transaction initiated from an unrecognized device."
            })

        if is_unusual_location:
            score += 15
            factors.append({
                "factor": "UNUSUAL_LOCATION",
                "weight": 15,
                "description": "Access originating from an anomalous IP / geographical location."
            })

        if had_recent_password_reset:
            score += 25
            factors.append({
                "factor": "RECENT_PASSWORD_RESET",
                "weight": 25,
                "description": "Account password was reset within the last 2 hours."
            })

        if amount_cents >= self.policy["high_amount_threshold"]:
            score += 20
            factors.append({
                "factor": "HIGH_VALUE_TRANSFER",
                "weight": 20,
                "description": f"Transfer amount exceeds high-value threshold (${amount_cents / 100:.2f})."
            })

        # 3. Fraud Registry Mule Account Check
        is_destination_mule = False
        mule_details = None
        if destination_account_token:
            is_destination_mule, mule_details = mst_client.is_mule_account(destination_account_token)
            if is_destination_mule:
                score += 45
                factors.append({
                    "factor": "MULE_ACCOUNT_DETECTED",
                    "weight": 45,
                    "description": f"Destination account flagged in MST FraudRegistry by {mule_details.get('reporter_bank_id')}: {mule_details.get('reason')}."
                })

        # Determine Outcome
        score = min(100, score)
        sms_otp_allowed = not (swap_detected and not is_pre_notified)

        if score >= self.policy["block_threshold"]:
            action = "BLOCK"
            reason = "High aggregate fraud risk score exceeding block threshold."
        elif score >= self.policy["step_up_threshold"]:
            action = "STEP_UP_BRIDGEKEY"
            reason = "Elevated risk detected. SMS OTP refused; BridgeKey biometric trusted-device signature required."
        else:
            action = "ALLOW"
            reason = "Risk score within acceptable threshold."

        return {
            "customer_id": customer_id,
            "risk_score": score,
            "action": action,
            "reason": reason,
            "sms_otp_allowed": sms_otp_allowed,
            "requires_bridgekey": action == "STEP_UP_BRIDGEKEY",
            "swap_detected": swap_detected,
            "is_pre_notified": is_pre_notified,
            "swap_age_hours": swap_age_hours,
            "is_destination_mule": is_destination_mule,
            "factors": factors,
            "timestamp": now
        }

risk_engine = RiskEngine()
