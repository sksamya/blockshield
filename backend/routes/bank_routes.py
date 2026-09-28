from flask import Blueprint, request, jsonify
from backend.bank.bank_service import bank_b_service, bank_c_service

bank_bp = Blueprint("bank", __name__, url_prefix="/api/bank")

def _get_bank(bank_id: str):
    if bank_id.lower() in ["bank-b", "b"]:
        return bank_b_service
    elif bank_id.lower() in ["bank-c", "c"]:
        return bank_c_service
    return None

@bank_bp.route("/<bank_id>/customers", methods=["GET"])
def get_customers(bank_id):
    bank = _get_bank(bank_id)
    if not bank:
        return jsonify({"error": f"Invalid bank_id: {bank_id}"}), 404
    return jsonify({"bank_id": bank.bank_id, "customers": list(bank.customers.values())})

@bank_bp.route("/<bank_id>/password-reset", methods=["POST"])
def password_reset(bank_id):
    bank = _get_bank(bank_id)
    if not bank:
        return jsonify({"error": f"Invalid bank_id: {bank_id}"}), 404

    data = request.get_json() or {}
    phone = data.get("phone_number")
    device_id = data.get("device_id", "unknown_device")
    ip_loc = data.get("ip_location", "unknown_location")

    if not phone:
        return jsonify({"error": "phone_number required"}), 400

    result = bank.request_password_reset(phone_number=phone, device_id=device_id, ip_location=ip_loc)
    return jsonify(result), (200 if result.get("status") != "failed" else 400)

@bank_bp.route("/<bank_id>/transfer", methods=["POST"])
def initiate_transfer(bank_id):
    bank = _get_bank(bank_id)
    if not bank:
        return jsonify({"error": f"Invalid bank_id: {bank_id}"}), 404

    data = request.get_json() or {}
    customer_id = data.get("customer_id")
    recipient = data.get("recipient_account")
    amount_cents = int(data.get("amount_cents", 0))
    device_id = data.get("device_id", "default_device")
    ip_location = data.get("ip_location", "usual_home_location")
    had_reset = data.get("had_recent_password_reset", False)

    if not customer_id or not recipient:
        return jsonify({"error": "customer_id and recipient_account are required"}), 400

    result = bank.initiate_transfer(
        customer_id=customer_id,
        recipient_account=recipient,
        amount_cents=amount_cents,
        device_id=device_id,
        ip_location=ip_location,
        had_recent_password_reset=had_reset
    )
    return jsonify(result), 200

@bank_bp.route("/<bank_id>/step-up", methods=["POST"])
def complete_step_up(bank_id):
    bank = _get_bank(bank_id)
    if not bank:
        return jsonify({"error": f"Invalid bank_id: {bank_id}"}), 404

    data = request.get_json() or {}
    transfer_id = data.get("transfer_id")
    signature = data.get("signature")

    if not transfer_id or not signature:
        return jsonify({"error": "transfer_id and signature are required"}), 400

    result = bank.complete_bridgekey_step_up(transfer_id=transfer_id, signature_hex=signature)
    return jsonify(result), (200 if result.get("status") == "success" else 400)

@bank_bp.route("/<bank_id>/transfers", methods=["GET"])
def list_transfers(bank_id):
    bank = _get_bank(bank_id)
    if not bank:
        return jsonify({"error": f"Invalid bank_id: {bank_id}"}), 404
    return jsonify({"bank_id": bank.bank_id, "transfers": list(bank.transfers.values())})

@bank_bp.route("/<bank_id>/alerts", methods=["GET"])
def list_alerts(bank_id):
    bank = _get_bank(bank_id)
    if not bank:
        return jsonify({"error": f"Invalid bank_id: {bank_id}"}), 404
    return jsonify({"bank_id": bank.bank_id, "alerts": bank.sent_alerts})
