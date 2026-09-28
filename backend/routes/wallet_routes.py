from flask import Blueprint, request, jsonify
from backend.wallet.bridgekey import bridgekey_service

wallet_bp = Blueprint("wallet", __name__, url_prefix="/api/wallet")

@wallet_bp.route("/enroll", methods=["POST"])
def enroll_wallet():
    data = request.get_json() or {}
    cust_id = data.get("customer_id")
    wallet_addr = data.get("wallet_address")

    if not cust_id or not wallet_addr:
        return jsonify({"error": "customer_id and wallet_address are required"}), 400

    try:
        res = bridgekey_service.enroll_wallet(cust_id, wallet_addr)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@wallet_bp.route("/challenge/<challenge_id>", methods=["GET"])
def get_challenge(challenge_id):
    challenge = bridgekey_service._active_challenges.get(challenge_id)
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404
    return jsonify(challenge), 200

@wallet_bp.route("/verify", methods=["POST"])
def verify_signature():
    data = request.get_json() or {}
    challenge_id = data.get("challenge_id")
    signature = data.get("signature")

    if not challenge_id or not signature:
        return jsonify({"error": "challenge_id and signature are required"}), 400

    is_valid, msg = bridgekey_service.verify_signature(challenge_id, signature)
    return jsonify({"is_valid": is_valid, "message": msg}), (200 if is_valid else 400)

@wallet_bp.route("/test-sign", methods=["POST"])
def test_sign():
    data = request.get_json() or {}
    challenge_id = data.get("challenge_id")
    private_key = data.get("private_key")

    if not challenge_id or not private_key:
        return jsonify({"error": "challenge_id and private_key are required"}), 400

    try:
        sig = bridgekey_service.sign_with_test_wallet(challenge_id, private_key)
        return jsonify({"challenge_id": challenge_id, "signature": sig}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
