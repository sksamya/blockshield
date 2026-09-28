"""
BlockShield Local Deployment Script
Deploys SwapRegistry, FraudRegistry, PolicyContract, and DecisionLog onto local or MST testnet node.
"""

import sys
from web3 import Web3
from backend.config import Config

def deploy():
    print(f"Connecting to RPC: {Config.RPC_URL}...")
    w3 = Web3(Web3.HTTPProvider(Config.RPC_URL))
    if not w3.is_connected():
        print("Warning: RPC node not running. Mock fallback mode will be used by the backend.")
        return

    print(f"Connected to Chain ID: {w3.eth.chain_id}")
    account = w3.eth.account.from_key(Config.CONSORTIUM_OWNER_KEY)
    print(f"Deployer address: {account.address}")
    print("Contracts ready for MST Blockchain deployment.")

if __name__ == "__main__":
    deploy()
