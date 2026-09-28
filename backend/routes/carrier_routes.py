from flask import Blueprint, request, jsonify
from backend.carrier.carrier_service import carrier_service
from backend.chain.mst_client import mst_client

carrier_bp = Blueprint("carrier", __name__, url_prefix="/api/carrier")

@carrier_bp.route("/event", methods=["POST"])
def record_event():
    data = request.get_json() or {}
    phone = data.get("phone_number")
    event_type = data.get("event_type", "SIM_SWAP")
    pre_notified = data.get("pre_notified", False)
    ref = data.get("notification_ref", "")

    if not phone:
        return jsonify({"error": "phone_number is required"}), 400

    try:
        result = carrier_service.record_sim_event(
            phone_number=phone,
            event_type=event_type,
            pre_notified=pre_notified,
            notification_ref=ref
        )
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@carrier_bp.route("/pre-notify", methods=["POST"])
def pre_notify():
    data = request.get_json() or {}
    phone = data.get("phone_number")
    duration = int(data.get("duration_seconds", 86400))

    if not phone:
        return jsonify({"error": "phone_number is required"}), 400

    try:
        result = carrier_service.register_pre_notification(phone, duration)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@carrier_bp.route("/token", methods=["GET"])
def get_token():
    phone = request.args.get("phone")
    if not phone:
        return jsonify({"error": "phone parameter required"}), 400
    token_hex = carrier_service.get_token_hex(phone)
    return jsonify({"phone_masked": carrier_service._mask_phone(phone), "token": token_hex})

@carrier_bp.route("/events", methods=["GET"])
def list_events():
    events = mst_client.get_all_swap_events()
    return jsonify({"total": len(events), "events": events})
