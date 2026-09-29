"""
Test End-to-End Phone-Number-to-Wallet Binding and SIM-Swap Broadcast-to-Detection Flow
Demo Data:
  - CUST-1001: Phone +15551234567, Wallet 0x19515982e62f9fc03f4e43498ce18028a4cb650e (bank-b)
  - CUST-1002: Phone +15557654321, Wallet 0xa61efceef6debe10a029af2bf7e37220b6dae22f (bank-b)
"""

import sys
import json
from web3 import Web3
from backend.app import app
from backend.carrier.carrier_service import carrier_service
from backend.bank.bank_service import bank_b_service
from backend.wallet.bridgekey import bridgekey_service
from backend.chain.mst_client import mst_client

def run_tests():
    print("=" * 70)
    print("RUNNING END-TO-END SIM-SWAP BROADCAST-TO-DETECTION & WALLET BINDING TEST")
    print("=" * 70)

    # 1. Verify Phone-to-Wallet Bindings in Bank B and BridgeKey
    print("\n[Step 1] Verifying Customer Phone-to-Wallet Bindings in Bank B...")
    c1 = bank_b_service.get_customer("CUST-1001")
    c2 = bank_b_service.get_customer("CUST-1002")

    assert c1 is not None, "CUST-1001 must exist in Bank B"
    assert c2 is not None, "CUST-1002 must exist in Bank B"

    assert c1["phone"] == "+15551234567", f"Expected +15551234567, got {c1['phone']}"
    assert c1["wallet_address"].lower() == "0x19515982e62f9fc03f4e43498ce18028a4cb650e".lower()

    assert c2["phone"] == "+15557654321", f"Expected +15557654321, got {c2['phone']}"
    assert c2["wallet_address"].lower() == "0xa61efceef6debe10a029af2bf7e37220b6dae22f".lower()

    w1 = bridgekey_service.get_enrolled_wallet("CUST-1001")
    w2 = bridgekey_service.get_enrolled_wallet("CUST-1002")
    assert w1.lower() == c1["wallet_address"].lower(), "BridgeKey enrolled wallet must match Bank B customer record"
    assert w2.lower() == c2["wallet_address"].lower(), "BridgeKey enrolled wallet must match Bank B customer record"
    print("  [OK] CUST-1001: Phone +15551234567 -> Wallet 0x19515982e62f9fc03f4e43498ce18028a4cb650e")
    print("  [OK] CUST-1002: Phone +15557654321 -> Wallet 0xa61efceef6debe10a029af2bf7e37220b6dae22f")

    # 2. Before Swap: Bank B Checks Status for CUST-1001
    print("\n[Step 2] Bank B Checks Status before any SIM swap...")
    token_1001 = carrier_service.compute_token(c1["phone"])
    # Clear local swap events for this test if any
    mst_client._local_swap_events.pop(token_1001.hex(), None)

    pre_check = bank_b_service.detect_sim_swap("CUST-1001")
    assert pre_check["swap_detected"] is False, "Before swap, swap_detected must be False"
    assert pre_check["sms_otp_allowed"] is True, "Before swap, SMS OTP must be allowed"
    print(f"  [OK] Pre-swap state: swap_detected={pre_check['swap_detected']}, sms_otp_allowed={pre_check['sms_otp_allowed']}")

    # 3. Carrier A Broadcasts SIM_SWAP for CUST-1001 Phone (+15551234567)
    print("\n[Step 3] Carrier A Broadcasts SIM_SWAP event for +15551234567 to MST Blockchain...")
    swap_res = carrier_service.record_sim_event(
        phone_number=c1["phone"],
        event_type="SIM_SWAP",
        pre_notified=False
    )
    assert swap_res["status"] == "success", "SIM swap broadcast must succeed"
    assert "0x" in swap_res["tx_hash"], "A transaction hash must be recorded"
    print(f"  [OK] Swap recorded on MST Blockchain: token={swap_res['token'][:16]}..., tx={swap_res['tx_hash'][:16]}...")

    # 4. Bank B Detects the SIM Swap in Real-Time
    print("\n[Step 4] Bank B Queries MST Blockchain to Detect the SIM Swap...")
    detection = bank_b_service.detect_sim_swap("CUST-1001")
    assert detection["swap_detected"] is True, "Bank B MUST detect the SIM swap!"
    assert detection["sms_otp_allowed"] is False, "Bank B MUST refuse SMS OTP!"
    assert detection["requires_bridgekey"] is True, "Bank B MUST require BridgeKey biometric signer!"
    assert detection["wallet_address"].lower() == c1["wallet_address"].lower()
    print("  [OK] Bank B successfully detected the SIM swap on MST Blockchain!")
    print(f"       Action: {detection['action']}")
    print(f"       SMS OTP Allowed: {detection['sms_otp_allowed']}")
    print(f"       BridgeKey Biometric Required: {detection['requires_bridgekey']}")
    print(f"       Bound Device Signer Wallet: {detection['wallet_address']}")

    # 5. Bank B Evaluates Transfer Attempt -> Enforces BridgeKey Step-Up
    print("\n[Step 5] Bank B Evaluates Transfer Attempt for CUST-1001...")
    tx = bank_b_service.initiate_transfer(
        customer_id="CUST-1001",
        recipient_account="ACC-MERCHANT-88",
        amount_cents=10000,
        device_id="unknown_laptop",
        ip_location="usual_home_location",
        had_recent_password_reset=False
    )
    assert tx["status"] == "PENDING_VERIFICATION", f"Transfer must require verification, got {tx['status']}"
    assert tx["requires_bridgekey"] is True, "Transfer must require BridgeKey"
    assert tx["wallet_address"].lower() == c1["wallet_address"].lower(), "Challenge must target CUST-1001 wallet"
    print(f"  [OK] Transfer intercepted: Status={tx['status']}, Risk Score={tx['risk_score']}")
    print(f"       Challenge ID: {tx['challenge']['challenge_id']}")
    print(f"       Target Wallet: {tx['challenge']['wallet_address']}")

    # 6. Test via HTTP API Client
    print("\n[Step 6] Testing HTTP API Endpoints via Flask Client...")
    with app.test_client() as client:
        # GET detect-swap endpoint
        res = client.get("/api/bank/bank-b/detect-swap/CUST-1001")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["swap_detected"] is True
        assert data["sms_otp_allowed"] is False
        assert data["wallet_address"].lower() == c1["wallet_address"].lower()
        print("  [OK] GET /api/bank/bank-b/detect-swap/CUST-1001 -> swap_detected=True, sms_otp_allowed=False")

        # Simulator Demo-flow endpoint
        sim_res = client.post("/api/simulator/demo-flow")
        assert sim_res.status_code == 200
        sim_data = json.loads(sim_res.data)
        assert sim_data["success"] is True
        print("  [OK] POST /api/simulator/demo-flow -> success=True")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED! END-TO-END FLOW VERIFIED SUCCESSFULLY.")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
