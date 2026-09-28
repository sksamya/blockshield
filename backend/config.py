import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CHAIN_MODE = os.getenv("CHAIN_MODE", "local")
    RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
    CHAIN_ID = int(os.getenv("CHAIN_ID", "1337"))
    EXPLORER_URL = os.getenv("EXPLORER_URL", "https://testnet.mstscan.com")
    CONFIRMATIONS = int(os.getenv("CONFIRMATIONS", "1"))

    # Contract Addresses
    SWAP_REGISTRY_ADDRESS = os.getenv("SWAP_REGISTRY_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
    FRAUD_REGISTRY_ADDRESS = os.getenv("FRAUD_REGISTRY_ADDRESS", "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")
    POLICY_CONTRACT_ADDRESS = os.getenv("POLICY_CONTRACT_ADDRESS", "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0")
    DECISION_LOG_ADDRESS = os.getenv("DECISION_LOG_ADDRESS", "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9")

    # Keys
    CONSORTIUM_OWNER_KEY = os.getenv(
        "CONSORTIUM_OWNER_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    CARRIER_A_SIGNING_KEY = os.getenv(
        "CARRIER_A_SIGNING_KEY",
        "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    )
    CARRIER_A_TOKEN_KEY = os.getenv("CARRIER_A_TOKEN_KEY", "carrier-a-consortium-secret-key-2026")

    BANK_B_SIGNER_KEY = os.getenv(
        "BANK_B_SIGNER_KEY",
        "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
    )
    BANK_C_SIGNER_KEY = os.getenv(
        "BANK_C_SIGNER_KEY",
        "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"
    )

    SIGNER_MODE = os.getenv("SIGNER_MODE", "bridgekey")
    STORAGE_MODE = os.getenv("STORAGE_MODE", "memory")
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "blockshield.db")

    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
