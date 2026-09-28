import os
from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.routes.carrier_routes import carrier_bp
from backend.routes.bank_routes import bank_bp
from backend.routes.wallet_routes import wallet_bp
from backend.routes.consortium_routes import consortium_bp
from backend.routes.simulator_routes import simulator_bp

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable Cross-Origin Resource Sharing for React frontend

    # Register API blueprints
    app.register_blueprint(carrier_bp)
    app.register_blueprint(bank_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(consortium_bp)
    app.register_blueprint(simulator_bp)

    @app.route("/health", methods=["GET"])
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "BlockShield Core Backend",
            "chain": "MST Blockchain (EVM L1)",
            "signer": "BridgeKey Trusted-Device Signer",
            "framework": "Flask"
        }), 200

    @app.route("/api/summary", methods=["GET"])
    def system_summary():
        from backend.chain.mst_client import mst_client
        from backend.bank.bank_service import bank_b_service, bank_c_service
        return jsonify({
            "chain_mode": Config.CHAIN_MODE,
            "contracts": {
                "SwapRegistry": Config.SWAP_REGISTRY_ADDRESS,
                "FraudRegistry": Config.FRAUD_REGISTRY_ADDRESS,
                "PolicyContract": Config.POLICY_CONTRACT_ADDRESS,
                "DecisionLog": Config.DECISION_LOG_ADDRESS
            },
            "stats": {
                "total_swap_events": len(mst_client._local_swap_events),
                "total_anchors": len(mst_client._local_anchors),
                "bank_b_transfers": len(bank_b_service.transfers),
                "bank_c_transfers": len(bank_c_service.transfers),
                "bank_b_alerts": len(bank_b_service.sent_alerts),
                "bank_c_alerts": len(bank_c_service.sent_alerts)
            }
        }), 200

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
