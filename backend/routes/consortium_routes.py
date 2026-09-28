import secrets
from flask import Blueprint, request, jsonify
from backend.chain.mst_client import mst_client
from backend.carrier.carrier_service import carrier_service
from backend.bank.bank_service import bank_b_service, bank_c_service

consortium_bp = Blueprint("consortium", __name__, url_prefix="/api/consortium")

@consortium_bp.route("/mule", methods=["POST"])
def flag_mule():
    data = request.get_json() or {}
    account_number = data.get("account_number")
    bank_id = data.get("bank_id", "bank-b")
    reason = data.get("reason", "Suspected mule account")

    if not account_number:
        return jsonify({"error": "account_number is required"}), 400

    account_token = carrier_service.compute_token(account_number)
    evidence_hash = secrets.token_bytes(32)

    flag_result = mst_client.flag_mule_account(
        account_token=account_token,
        bank_id=bank_id,
        evidence_hash=evidence_hash,
        reason=reason
    )
    return jsonify(flag_result), 201

@consortium_bp.route("/mule/<account_number>", methods=["GET"])
def check_mule(account_number):
    account_token = carrier_service.compute_token(account_number)
    is_mule, details = mst_client.is_mule_account(account_token)
    return jsonify({"account_number": account_number, "is_mule": is_mule, "details": details})

@consortium_bp.route("/anchors", methods=["GET"])
def list_anchors():
    anchors = mst_client.get_all_anchors()
    return jsonify({"total": len(anchors), "anchors": anchors})

@consortium_bp.route("/audit/<bank_id>/<event_ref>", methods=["GET"])
def audit_record(bank_id, event_ref):
    bank = bank_b_service if bank_id.lower() in ["bank-b", "b"] else bank_c_service
    res = bank.decision_logger.verify_record_integrity(event_ref)
    return jsonify(res), (200 if res.get("is_valid") else 409)
