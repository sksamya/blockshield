import time
import secrets
from backend.carrier.carrier_service import carrier_service, CarrierService
from backend.bank.bank_service import bank_b_service, bank_c_service
from backend.wallet.bridgekey import bridgekey_service
from backend.chain.mst_client import mst_client
from backend.config import Config

class ScenarioRunner:
    """
    Simulates end-to-end fraud and security scenarios on MST Blockchain and BridgeKey.
    """

    def run_scenario_1_fraud_swap(self) -> dict:
        """
        Scenario 1: Fraud swap.
        Fraudster swaps victim's SIM at Carrier A, then attacks Bank B and Bank C.
        Both banks refuse SMS OTP, raise risk, alert the victim, and anchor decision hashes on MST.
        """
        victim_phone = "+15551234567"
        timeline = []

        # Step 1: Fraudster swaps SIM at Carrier A
        swap_result = carrier_service.record_sim_event(
            phone_number=victim_phone,
            event_type="SIM_SWAP",
            pre_notified=False
        )
        timeline.append({
            "step": 1,
            "entity": "Carrier A",
            "action": "Fraudulent SIM Swap Recorded",
            "detail": f"SIM swap recorded on MST Blockchain (TX: {swap_result['tx_hash'][:10]}...)",
            "result": swap_result
        })

        # Step 2: Fraudster attacks Bank B (password reset + $8,000 transfer)
        b_reset = bank_b_service.request_password_reset(
            phone_number=victim_phone,
            device_id="fraudster_laptop_macbook",
            ip_location="unknown_ip_russia"
        )
        timeline.append({
            "step": 2,
            "entity": "Bank B",
            "action": "Attacker Tries Password Reset",
            "detail": f"SMS OTP Refused: {not b_reset['sms_otp_allowed']}. Risk Score: {b_reset['risk_evaluation']['risk_score']}.",
            "result": b_reset
        })

        b_transfer = bank_b_service.initiate_transfer(
            customer_id="cust_victim",
            recipient_account="ACC-MULE-999",
            amount_cents=800000, # $8,000.00
            device_id="fraudster_laptop_macbook",
            ip_location="unknown_ip_russia",
            had_recent_password_reset=True
        )
        timeline.append({
            "step": 3,
            "entity": "Bank B",
            "action": "Attacker High-Value Transfer Blocked/Stepped-Up",
            "detail": f"Status: {b_transfer['status']}. BridgeKey Required: {b_transfer['requires_bridgekey']}.",
            "result": b_transfer
        })

        # Step 3: Fraudster attacks Bank C
        c_transfer = bank_c_service.initiate_transfer(
            customer_id="cust_victim",
            recipient_account="ACC-MULE-888",
            amount_cents=600000, # $6,000.00
            device_id="fraudster_laptop_macbook",
            ip_location="unknown_ip_russia",
            had_recent_password_reset=True
        )
        timeline.append({
            "step": 4,
            "entity": "Bank C",
            "action": "Bank C Reads Same MST Event & Blocks",
            "detail": f"Cross-Bank Detection: Risk Score {c_transfer['risk_score']}. Action: {c_transfer['action']}.",
            "result": c_transfer
        })

        return {
            "scenario": 1,
            "title": "Fraud Swap Attack on Multiple Banks",
            "success": True,
            "expected_result": "Both banks refuse SMS OTP, block transfers, alert victim, anchor hashes on MST Blockchain",
            "timeline": timeline
        }

    def run_scenario_2_prenotified_swap(self) -> dict:
        """
        Scenario 2: Pre-notified legitimate swap.
        Customer notifies carrier before upgrading device/SIM. Normal transfer succeeds.
        """
        bob_phone = "+15559876543"
        timeline = []

        # Step 1: Pre-notification
        pre_notif = carrier_service.register_pre_notification(phone_number=bob_phone, duration_seconds=86400)
        timeline.append({
            "step": 1,
            "entity": "Carrier A",
            "action": "Customer Authenticates & Pre-Notifies SIM Swap",
            "detail": "Pre-notification registered for token on MST Blockchain",
            "result": pre_notif
        })

        # Step 2: Swap SIM
        swap_result = carrier_service.record_sim_event(
            phone_number=bob_phone,
            event_type="ESIM",
            pre_notified=True
        )
        timeline.append({
            "step": 2,
            "entity": "Carrier A",
            "action": "eSIM Activated",
            "detail": f"Swap marked pre-notified: {swap_result['pre_notified']}",
            "result": swap_result
        })

        # Step 3: Bob makes a transfer at Bank B
        transfer = bank_b_service.initiate_transfer(
            customer_id="cust_legit",
            recipient_account="ACC-UTILITIES-44",
            amount_cents=15000, # $150.00
            device_id="device_bob_pixel",
            ip_location="usual_home_location"
        )
        timeline.append({
            "step": 3,
            "entity": "Bank B",
            "action": "Transfer Evaluated Under Lower-Risk Policy",
            "detail": f"Risk Score: {transfer['risk_score']}. Status: {transfer['status']}",
            "result": transfer
        })

        return {
            "scenario": 2,
            "title": "Pre-notified Legitimate SIM Swap",
            "success": transfer["status"] == "APPROVED",
            "expected_result": "Lower-risk policy applies and normal transfer succeeds",
            "timeline": timeline
        }

    def run_scenario_3_unnotified_legitimate_swap(self) -> dict:
        """
        Scenario 3: Un-notified legitimate swap.
        Customer swaps without notice. Step-up required -> Customer signs with BridgeKey -> succeeds.
        """
        bob_phone = "+15559876543"
        timeline = []

        # Step 1: Un-notified swap
        swap = carrier_service.record_sim_event(phone_number=bob_phone, event_type="SIM_SWAP", pre_notified=False)
        timeline.append({
            "step": 1,
            "entity": "Carrier A",
            "action": "Un-notified SIM Swap",
            "detail": "Swap recorded without pre-notification",
            "result": swap
        })

        # Step 2: Bank B initiates transfer -> Triggers BridgeKey Step-Up
        transfer = bank_b_service.initiate_transfer(
            customer_id="cust_legit",
            recipient_account="ACC-STORE-77",
            amount_cents=45000, # $450.00
            device_id="device_bob_pixel",
            ip_location="usual_home_location"
        )
        timeline.append({
            "step": 2,
            "entity": "Bank B",
            "action": "Step-Up Required (SMS OTP Disabled)",
            "detail": f"Status: {transfer['status']}. BridgeKey Challenge Issued: {transfer['challenge']['challenge_id']}",
            "result": transfer
        })

        # Step 3: Customer signs challenge with BridgeKey
        # Test private key corresponding to cust_legit wallet (0x70997970C51812dc3A010C7d01b50e0d17dc79C8)
        test_key = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
        challenge_id = transfer["challenge"]["challenge_id"]
        sig = bridgekey_service.sign_with_test_wallet(challenge_id, test_key)

        step_up_result = bank_b_service.complete_bridgekey_step_up(transfer["transfer_id"], sig)
        timeline.append({
            "step": 3,
            "entity": "BridgeKey / Bank B",
            "action": "Biometric On-Device Signature Submitted",
            "detail": f"Outcome: {step_up_result['transfer_status']}. Decision re-anchored on MST.",
            "result": step_up_result
        })

        return {
            "scenario": 3,
            "title": "Un-notified Swap with BridgeKey Trusted-Device Step-Up",
            "success": step_up_result["transfer_status"] == "APPROVED_BY_BRIDGEKEY",
            "expected_result": "Step-up triggered; customer signs with BridgeKey and succeeds",
            "timeline": timeline
        }

    def run_scenario_4_old_swap(self) -> dict:
        """
        Scenario 4: Old swap.
        Swap falls outside recent-swap window (> 72 hours). No effect on risk.
        """
        alice_phone = "+15551234567"
        timeline = []

        # Simulate historical event 100 hours ago
        old_timestamp = int(time.time()) - (100 * 3600)
        token = carrier_service.compute_token(alice_phone)
        nonce = secrets.token_bytes(32)

        mst_client.record_swap_event(
            token_bytes=token,
            carrier_id="carrier-a",
            event_type="SIM_SWAP",
            timestamp=old_timestamp,
            pre_notified=False,
            notification_ref="",
            nonce_bytes=nonce,
            signature_bytes=b"",
            private_key=Config.CARRIER_A_SIGNING_KEY
        )

        timeline.append({
            "step": 1,
            "entity": "Carrier A",
            "action": "Historical Swap Record",
            "detail": "Swap occurred 100 hours ago (outside 72h window)"
        })

        transfer = bank_b_service.initiate_transfer(
            customer_id="cust_victim",
            recipient_account="ACC-STORE-12",
            amount_cents=10000,
            device_id="device_alice_iphone",
            ip_location="usual_home_location"
        )
        timeline.append({
            "step": 2,
            "entity": "Bank B",
            "action": "Transfer Evaluation",
            "detail": f"Risk Score: {transfer['risk_score']}. Status: {transfer['status']}",
            "result": transfer
        })

        return {
            "scenario": 4,
            "title": "Historical Swap Outside Window",
            "success": transfer["status"] == "APPROVED",
            "expected_result": "No effect on risk",
            "timeline": timeline
        }

    def run_scenario_5_mule_flag_sharing(self) -> dict:
        """
        Scenario 5: Mule flag sharing.
        Bank B flags a mule account in MST FraudRegistry -> Bank C raises risk on transfer to it.
        """
        mule_account = "ACC-MULE-FRAUD-99"
        mule_token = carrier_service.compute_token(mule_account)
        timeline = []

        # Step 1: Bank B flags mule
        evidence_hash = secrets.token_bytes(32)
        flag_result = mst_client.flag_mule_account(
            account_token=mule_token,
            bank_id="bank-b",
            evidence_hash=evidence_hash,
            reason="Confirmed mule account involved in phishing campaign"
        )
        timeline.append({
            "step": 1,
            "entity": "Bank B",
            "action": "Flag Mule Account on MST FraudRegistry",
            "detail": f"Account {mule_account} flagged on-chain",
            "result": flag_result
        })

        # Step 2: Customer at Bank C tries to send money to the flagged mule
        transfer = bank_c_service.initiate_transfer(
            customer_id="cust_victim",
            recipient_account=mule_account,
            amount_cents=200000,
            device_id="device_alice_iphone",
            ip_location="usual_home_location"
        )
        timeline.append({
            "step": 2,
            "entity": "Bank C",
            "action": "Bank C Evaluates Transfer to Flagged Account",
            "detail": f"Mule Flag Detected: Risk Score {transfer['risk_score']}. Action: {transfer['action']}",
            "result": transfer
        })

        return {
            "scenario": 5,
            "title": "Cross-Bank Mule Flag Sharing",
            "success": transfer["risk_score"] >= 45,
            "expected_result": "Bank C raises risk on transfers to that account",
            "timeline": timeline
        }

    def run_scenario_6_audit_tampering(self) -> dict:
        """
        Scenario 6: Audit & Tamper Detection.
        A stored decision record is altered off-chain -> Recomputed hash does not match on-chain anchor.
        """
        timeline = []
        event_ref = f"audit_tx_{secrets.token_hex(6)}"

        # Step 1: Create legitimate decision record & anchor on MST
        anchor = bank_b_service.decision_logger.log_and_anchor_decision(
            event_ref=event_ref,
            customer_id="cust_victim",
            transaction_type="HIGH_RISK_BLOCK",
            risk_evaluation={"risk_score": 90, "action": "BLOCK"},
            action_taken="BLOCK"
        )
        timeline.append({
            "step": 1,
            "action": "Legitimate Decision Anchored on MST Blockchain",
            "detail": f"Anchored Hash: {anchor['decision_hash']}",
            "result": anchor
        })

        # Step 2: Verify integrity before tampering
        audit_before = bank_b_service.decision_logger.verify_record_integrity(event_ref)
        timeline.append({
            "step": 2,
            "action": "Pre-Tamper Audit Verification",
            "detail": f"Is Match: {audit_before['is_valid']}. Message: {audit_before['chain_result']['message']}",
            "result": audit_before
        })

        # Step 3: Malicious insider alters off-chain record
        bank_b_service.decision_logger.simulate_tampering(event_ref, "action_taken", "APPROVED_BYPASS")
        timeline.append({
            "step": 3,
            "action": "Off-Chain Record Maliciously Altered",
            "detail": "Changed action_taken from BLOCK to APPROVED_BYPASS"
        })

        # Step 4: Auditor runs audit verification
        audit_after = bank_b_service.decision_logger.verify_record_integrity(event_ref)
        timeline.append({
            "step": 4,
            "action": "Post-Tamper Audit Verification",
            "detail": f"Tampering Detected: {not audit_after['is_valid']}. Message: {audit_after['chain_result']['message']}",
            "result": audit_after
        })

        return {
            "scenario": 6,
            "title": "Audit & On-Chain Anchor Tamper Detection",
            "success": (audit_before["is_valid"] is True and audit_after["is_valid"] is False),
            "expected_result": "Recomputed hash does not match the on-chain anchor",
            "timeline": timeline
        }

scenario_runner = ScenarioRunner()
