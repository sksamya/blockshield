"""
BlockShield - Cross-Carrier, Cross-Bank SIM-Swap Fraud Prevention
Running on MST Blockchain & BridgeKey Signer
"""

from backend.app import app
from backend.config import Config

if __name__ == "__main__":
    print("=" * 60)
    print(" Starting BlockShield Flask Backend Server")
    print(f" Chain: MST Blockchain (RPC: {Config.RPC_URL})")
    print(f" Signer: BridgeKey Biometric Signer")
    print(f" Listening on http://0.0.0.0:{Config.PORT}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
