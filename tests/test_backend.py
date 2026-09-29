import pytest
from backend.app import create_app
from backend.carrier.carrier_service import carrier_service
from backend.wallet.bridgekey import bridgekey_service
from backend.bank.bank_service import bank_b_service, bank_c_service
from backend.simulator.scenarios import scenario_runner

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["signer"] == "BridgeKey Trusted-Device Signer"
    assert data["chain"] == "MST Blockchain (EVM L1)"

def test_carrier_tokenization():
    phone = "+15551234567"
    token = carrier_service.compute_token(phone)
    assert isinstance(token, bytes)
    assert len(token) == 32  # SHA-256 output length
    
    # Deterministic token check
    token_2 = carrier_service.compute_token(phone)
    assert token == token_2

def test_bridgekey_challenge_and_signing():
    customer_id = "cust_legit"
    challenge = bridgekey_service.create_challenge(
        customer_id=customer_id,
        action="TEST_TRANSFER",
        details={"amount": "$100.00"}
    )
    assert challenge["challenge_id"].startswith("bk_")
    assert challenge["status"] == "pending"

    # Sign using test private key
    test_key = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    sig = bridgekey_service.sign_with_test_wallet(challenge["challenge_id"], test_key)
    assert sig.startswith("0x")

    # Verify signature
    is_valid, msg = bridgekey_service.verify_signature(challenge["challenge_id"], sig)
    assert is_valid is True
    assert "verified successfully" in msg

def test_decision_logger_tamper_detection():
    event_ref = "test_event_123"
    anchor = bank_b_service.decision_logger.log_and_anchor_decision(
        event_ref=event_ref,
        customer_id="cust_victim",
        transaction_type="TEST_TRANSFER",
        risk_evaluation={"risk_score": 75},
        action_taken="STEP_UP"
    )
    assert anchor["decision_hash"].startswith("0x")

    # Valid check
    audit = bank_b_service.decision_logger.verify_record_integrity(event_ref)
    assert audit["is_valid"] is True

    # Tamper
    bank_b_service.decision_logger.simulate_tampering(event_ref, "action_taken", "BYPASS")
    audit_tampered = bank_b_service.decision_logger.verify_record_integrity(event_ref)
    assert audit_tampered["is_valid"] is False

def test_all_simulator_scenarios():
    scenarios = [
        scenario_runner.run_scenario_1_fraud_swap(),
        scenario_runner.run_scenario_2_prenotified_swap(),
        scenario_runner.run_scenario_3_unnotified_legitimate_swap(),
        scenario_runner.run_scenario_4_old_swap(),
        scenario_runner.run_scenario_5_mule_flag_sharing(),
        scenario_runner.run_scenario_6_audit_tampering()
    ]
    for s in scenarios:
        assert s.get("success") is True, f"Scenario {s['scenario']} failed!"

def test_api_carrier_endpoints(client):
    # Test token endpoint
    res = client.get("/api/carrier/token?phone=+15551234567")
    assert res.status_code == 200
    assert "token" in res.get_json()

    # Test pre-notify endpoint
    res = client.post("/api/carrier/pre-notify", json={"phone_number": "+15551234567", "duration_seconds": 3600})
    assert res.status_code == 200
    assert res.get_json()["status"] == "success" or "result" in res.get_json()

    # Test record swap event
    res = client.post("/api/carrier/event", json={"phone_number": "+15551234567", "event_type": "SIM_SWAP"})
    assert res.status_code == 201
    assert res.get_json()["status"] == "success"

def test_api_bank_and_wallet_flow(client):
    # Get customers
    res = client.get("/api/bank/bank-b/customers")
    assert res.status_code == 200
    customers = res.get_json()["customers"]
    assert len(customers) > 0

    # Transfer initiating step-up (un-notified swap score 55 is between 50 and 79 -> triggers BridgeKey step-up)
    res = client.post("/api/bank/bank-b/transfer", json={
        "customer_id": "cust_legit",
        "recipient_account": "ACC-999888",
        "amount_cents": 50000,
        "device_id": "device_bob_pixel",
        "ip_location": "usual_home_location",
        "had_recent_password_reset": False
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["requires_bridgekey"] is True
    transfer_id = data["transfer_id"]
    challenge_id = data["challenge"]["challenge_id"]

    # Test wallet sign
    test_key = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    sign_res = client.post("/api/wallet/test-sign", json={"challenge_id": challenge_id, "private_key": test_key})
    assert sign_res.status_code == 200
    sig = sign_res.get_json()["signature"]

    # Complete step-up
    stepup_res = client.post("/api/bank/bank-b/step-up", json={"transfer_id": transfer_id, "signature": sig})
    assert stepup_res.status_code == 200
    assert stepup_res.get_json()["status"] == "success"

def test_api_simulator_and_summary(client):
    res = client.post("/api/simulator/run-all")
    assert res.status_code == 200
    assert res.get_json()["all_scenarios_passed"] is True

    summary = client.get("/api/summary")
    assert summary.status_code == 200
    assert summary.get_json()["chain_mode"] in ["local", "mst-testnet"]

