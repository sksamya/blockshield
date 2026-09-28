import json
import time
import secrets
from web3 import Web3
from backend.chain.mst_client import mst_client

class DecisionLogger:
    """
    Manages off-chain decision logs and anchors their keccak256 hashes onto MST Blockchain.
    Ensures verifiable, tamper-evident audit trails across consortium banks.
    """

    def __init__(self, bank_id: str = "bank-b"):
        self.bank_id = bank_id
        # In-memory storage of off-chain decision records: event_ref -> canonical_dict
        self._records = {}

    def to_canonical_json(self, data: dict) -> str:
        """Serializes dictionary to canonical JSON with sorted keys."""
        return json.dumps(data, sort_keys=True, separators=(',', ':'))

    def compute_decision_hash(self, canonical_json_str: str) -> bytes:
        """Computes keccak256 hash of the canonical JSON string."""
        return Web3.keccak(text=canonical_json_str)

    def log_and_anchor_decision(
        self,
        event_ref: str,
        customer_id: str,
        transaction_type: str,
        risk_evaluation: dict,
        action_taken: str,
        additional_metadata: dict = None
    ) -> dict:
        """
        Creates canonical decision record, hashes it, saves off-chain, and anchors on MST Blockchain.
        """
        timestamp = int(time.time())
        event_ref_bytes = Web3.keccak(text=event_ref)

        record = {
            "version": "1.0",
            "bank_id": self.bank_id,
            "event_ref": event_ref,
            "event_ref_hash": "0x" + event_ref_bytes.hex(),
            "customer_id": customer_id,
            "transaction_type": transaction_type,
            "timestamp": timestamp,
            "risk_evaluation": risk_evaluation,
            "action_taken": action_taken,
            "metadata": additional_metadata or {}
        }

        canonical_json_str = self.to_canonical_json(record)
        decision_hash = self.compute_decision_hash(canonical_json_str)

        # Store off-chain record
        self._records[event_ref] = {
            "raw_record": record,
            "canonical_json": canonical_json_str,
            "decision_hash": "0x" + decision_hash.hex(),
            "anchored": False
        }

        # Anchor on MST Blockchain
        anchor_result = mst_client.anchor_decision(
            bank_id=self.bank_id,
            event_ref=event_ref_bytes,
            decision_hash=decision_hash,
            timestamp=timestamp
        )

        self._records[event_ref]["anchored"] = True
        self._records[event_ref]["anchor_result"] = anchor_result

        return {
            "event_ref": event_ref,
            "bank_id": self.bank_id,
            "decision_hash": "0x" + decision_hash.hex(),
            "tx_hash": anchor_result["tx_hash"],
            "block_timestamp": anchor_result["block_timestamp"],
            "explorer_url": anchor_result["explorer_url"]
        }

    def get_record(self, event_ref: str) -> dict | None:
        return self._records.get(event_ref)

    def get_all_records(self) -> list:
        return list(self._records.values())

    def verify_record_integrity(self, event_ref: str) -> dict:
        """
        Audits a stored decision record by recomputing its keccak256 hash and verifying
        against the immutable on-chain anchor on MST Blockchain.
        """
        stored = self._records.get(event_ref)
        if not stored:
            return {"verified": False, "error": f"Record with event_ref {event_ref} not found locally."}

        # Recompute hash from current stored record
        recomputed_json = self.to_canonical_json(stored["raw_record"])
        recomputed_hash = self.compute_decision_hash(recomputed_json)
        event_ref_bytes = Web3.keccak(text=event_ref)

        chain_verification = mst_client.verify_decision_anchor(
            event_ref=event_ref_bytes,
            decision_hash=recomputed_hash
        )

        return {
            "event_ref": event_ref,
            "bank_id": self.bank_id,
            "is_valid": chain_verification["is_match"],
            "recomputed_hash": "0x" + recomputed_hash.hex(),
            "chain_result": chain_verification
        }

    def simulate_tampering(self, event_ref: str, field_to_alter: str, new_value: any) -> dict:
        """Helper to simulate malicious off-chain tampering for demo scenario 6."""
        stored = self._records.get(event_ref)
        if not stored:
            raise ValueError(f"Record {event_ref} not found")

        stored["raw_record"][field_to_alter] = new_value
        return {"status": "tampered", "field": field_to_alter, "new_value": new_value}
