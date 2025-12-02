import hashlib
import json
import time
import sqlite3
import os
from enum import Enum
from typing import List, Dict, Any
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError


# --- Data Models ---
class ActionType(Enum):
    EXTRACTED = "EXTRACTED"
    MANUFACTURED = "MANUFACTURED"
    SHIPPED = "SHIPPED"
    RECEIVED = "RECEIVED"
    SOLD = "SOLD"
    DESTROYED = "DESTROYED"
    CONSUMED = "CONSUMED"
    VOTE = "VOTE"


class Transaction:
    def __init__(
        self,
        sender_public_key: str,
        receiver_public_key: str,
        shipment_id: str,
        action: ActionType,
        location: str,
        good_id: str = None,
        quantity: float = None,
        metadata: Dict[str, Any] = None,
        timestamp: float = None,
        signature: str = None,
    ):
        self.sender = sender_public_key
        self.receiver = receiver_public_key
        self.shipment_id = shipment_id
        self.action = action.value if isinstance(action, ActionType) else action
        self.location = location
        self.good_id = good_id
        self.quantity = quantity
        self.metadata = metadata if metadata else {}
        self.timestamp = timestamp if timestamp else time.time()
        self.signature = signature
        self.tx_hash = self.calculate_hash()

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "shipment_id": self.shipment_id,
            "action": self.action,
            "good_id": self.good_id,
            "quantity": self.quantity,
            "timestamp": self.timestamp,
            "location": self.location,
            "metadata": self.metadata,
        }

    def calculate_hash(self):
        tx_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def sign_transaction(self, private_key_hex: str):
        try:
            sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.signature = sk.sign(self.calculate_hash().encode()).hex()
            return True
        except Exception as e:
            print(f"Error signing: {e}")
            return False

    def is_valid(self):
        if not self.signature:
            return False
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(self.sender), curve=SECP256k1)
            return vk.verify(
                bytes.fromhex(self.signature), self.calculate_hash().encode()
            )
        except (BadSignatureError, ValueError):
            return False


class Block:
    def __init__(
        self,
        index: int,
        transactions: List[Transaction],
        previous_hash: str,
        validator_address: str,
        timestamp: float = None,
        hash: str = None,
    ):
        self.index = index
        self.timestamp = timestamp if timestamp else time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.validator = validator_address
        self.merkle_root = self.compute_merkle_root()
        self.hash = hash if hash else self.calculate_block_hash()

    def compute_merkle_root(self):
        if not self.transactions:
            return ""
        hashes = [tx.tx_hash for tx in self.transactions]
        while len(hashes) > 1:
            temp = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + (
                    hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
                )
                temp.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = temp
        return hashes[0]

    def calculate_block_hash(self):
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "validator": self.validator,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_json(self):
        return json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": [
                    {**tx.to_dict(), "signature": tx.signature}
                    for tx in self.transactions
                ],
                "previous_hash": self.previous_hash,
                "validator": self.validator,
                "merkle_root": self.merkle_root,
                "hash": self.hash,
            }
        )

    @staticmethod
    def from_json(json_str):
        d = json.loads(json_str)
        txs = [
            Transaction(
                t["sender"],
                t["receiver"],
                t["shipment_id"],
                ActionType(t["action"]),
                t["location"],
                t.get("good_id"),
                t.get("quantity"),
                t["metadata"],
                t["timestamp"],
                t.get("signature"),
            )
            for t in d["transactions"]
        ]
        return Block(
            d["index"],
            txs,
            d["previous_hash"],
            d["validator"],
            d["timestamp"],
            d["hash"],
        )


# --- Blockchain Node Logic ---
class BlockchainNode:
    def __init__(self, node_name="Unknown", db_path="blockchain.db"):
        self.node_name = node_name
        self.db_file = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, block_hash TEXT UNIQUE, previous_hash TEXT, validator TEXT, timestamp REAL, data TEXT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS participants (name TEXT UNIQUE, public_key TEXT PRIMARY KEY, role TEXT, reputation INTEGER DEFAULT 10, votes INTEGER DEFAULT 0)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS goods (good_id TEXT PRIMARY KEY, name TEXT, unit_of_measure TEXT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS shipments (shipment_id TEXT PRIMARY KEY, good_id TEXT, quantity REAL, current_owner_pk TEXT, current_location TEXT, last_action TEXT, last_updated_timestamp REAL, is_active INTEGER DEFAULT 1)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS mempool (tx_hash TEXT PRIMARY KEY, data TEXT, timestamp REAL)"
        )
        conn.commit()
        conn.close()

    def select_validator(self, previous_block_hash, seed_offset=0):
        with sqlite3.connect(self.db_file) as conn:
            delegates = conn.execute(
                "SELECT name FROM participants ORDER BY votes DESC, name ASC LIMIT 3"
            ).fetchall()

        if not delegates:
            with sqlite3.connect(self.db_file) as conn:
                fallback = conn.execute(
                    "SELECT name FROM participants LIMIT 1"
                ).fetchone()
            return fallback[0] if fallback else "Unknown"

        seed_str = f"{previous_block_hash}{seed_offset}"
        seed_int = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
        winner_index = seed_int % len(delegates)
        return delegates[winner_index][0]

    def validate_smart_contract_rules(
        self, tx: Transaction, temp_state: Dict[str, Any] = None
    ):
        if tx.action == "VOTE":
            with sqlite3.connect(self.db_file) as conn:
                exists = conn.execute(
                    "SELECT 1 FROM participants WHERE public_key=?", (tx.receiver,)
                ).fetchone()
            return (True, "Valid Vote") if exists else (False, "Candidate unknown")

        shipment_data = None
        found_in_temp = False

        if temp_state and tx.shipment_id in temp_state:
            shipment_data = temp_state[tx.shipment_id]
            found_in_temp = True

        if not found_in_temp:
            with sqlite3.connect(self.db_file) as conn:
                shipment_data = conn.execute(
                    "SELECT current_owner_pk, last_action, is_active FROM shipments WHERE shipment_id = ?",
                    (tx.shipment_id,),
                ).fetchone()

        if tx.action in ["EXTRACTED", "MANUFACTURED"]:
            if shipment_data:
                _, _, is_active = shipment_data
                if is_active == 1:
                    return False, f"Shipment {tx.shipment_id} already active."
            return True, f"Valid {tx.action} (New Asset)"

        if not shipment_data:
            return False, f"Shipment {tx.shipment_id} does not exist."

        current_owner, last_action, is_active = shipment_data

        if is_active == 0:
            return False, f"Shipment {tx.shipment_id} is inactive."
        if tx.sender != current_owner:
            return False, f"Sender is not the current owner."

        return True, "Smart Contract Validated"

    def receive_block(self, block: Block):
        is_valid, reason = self.validate_block(block)
        if is_valid:
            self.save_block_to_db(block)
            self.clear_mempool(block.transactions)
            return True, "Accepted"
        return False, f"Rejected ({reason})"

    def validate_block(self, block: Block):
        last_block = self.get_last_block()
        if block.index == 1:
            if last_block:
                return False, "Genesis exists"
            if block.previous_hash != "0" * 64:
                return False, "Bad Genesis"
            return True, "Valid Genesis"
        if not last_block:
            return False, "Gap detected"
        if block.index != last_block.index + 1:
            return False, "Invalid Index"
        if block.previous_hash != last_block.hash:
            return False, "Broken Chain"
        if block.hash != block.calculate_block_hash():
            return False, "Invalid Hash"
        return True, "Valid"

    def save_block_to_db(self, block: Block):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO blocks (block_index, block_hash, previous_hash, validator, timestamp, data) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    block.index,
                    block.hash,
                    block.previous_hash,
                    block.validator,
                    block.timestamp,
                    block.to_json(),
                ),
            )

            for tx in block.transactions:
                if tx.action == "VOTE":
                    cursor.execute(
                        "UPDATE participants SET votes = votes + 1 WHERE public_key = ?",
                        (tx.receiver,),
                    )
                elif tx.action in ["DESTROYED", "CONSUMED"]:
                    cursor.execute(
                        "UPDATE shipments SET is_active = 0, last_action = ?, last_updated_timestamp = ? WHERE shipment_id = ?",
                        (tx.action, tx.timestamp, tx.shipment_id),
                    )
                elif tx.action in ["EXTRACTED", "MANUFACTURED"]:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO shipments (shipment_id, good_id, quantity, current_owner_pk, current_location, last_action, last_updated_timestamp, is_active) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                        (
                            tx.shipment_id,
                            tx.good_id,
                            tx.quantity,
                            tx.receiver,
                            tx.location,
                            tx.action,
                            tx.timestamp,
                        ),
                    )
                else:
                    q_sql = ", quantity = ?" if tx.quantity is not None else ""
                    params = [tx.receiver, tx.location, tx.action, tx.timestamp]
                    if tx.quantity is not None:
                        params.append(tx.quantity)
                    params.append(tx.shipment_id)
                    cursor.execute(
                        f"UPDATE shipments SET current_owner_pk = ?, current_location = ?, last_action = ?, last_updated_timestamp = ?, is_active = 1 {q_sql} WHERE shipment_id = ?",
                        params,
                    )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def add_to_mempool(self, tx: Transaction):
        if not tx.is_valid():
            return False, "Invalid Signature"
        conn = sqlite3.connect(self.db_file)
        try:
            # CHECK FOR DUPLICATE FIRST to support gossiping
            cursor = conn.execute(
                "SELECT 1 FROM mempool WHERE tx_hash = ?", (tx.tx_hash,)
            )
            if cursor.fetchone():
                return False, "Duplicate"

            tx_data = tx.to_dict()
            tx_data["signature"] = tx.signature
            conn.execute(
                "INSERT INTO mempool VALUES (?, ?, ?)",
                (tx.tx_hash, json.dumps(tx_data), time.time()),
            )
            conn.commit()
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
        return True, "Added"

    def get_mempool_transactions(self):
        conn = sqlite3.connect(self.db_file)
        rows = conn.execute(
            "SELECT data FROM mempool ORDER BY timestamp ASC"
        ).fetchall()
        conn.close()
        txs = []
        for row in rows:
            t = json.loads(row[0])
            tx = Transaction(
                t["sender"],
                t["receiver"],
                t["shipment_id"],
                ActionType(t["action"]),
                t["location"],
                t.get("good_id"),
                t.get("quantity"),
                t["metadata"],
                t["timestamp"],
                t.get("signature"),
            )
            txs.append(tx)
        return txs

    def clear_mempool(self, processed_txs: List[Transaction]):
        conn = sqlite3.connect(self.db_file)
        for tx in processed_txs:
            conn.execute("DELETE FROM mempool WHERE tx_hash = ?", (tx.tx_hash,))
        conn.commit()
        conn.close()

    def get_last_block(self):
        conn = sqlite3.connect(self.db_file)
        row = conn.execute(
            "SELECT data FROM blocks ORDER BY block_index DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return Block.from_json(row[0]) if row else None

    def get_block_by_index(self, index):
        conn = sqlite3.connect(self.db_file)
        row = conn.execute(
            "SELECT data FROM blocks WHERE block_index = ?", (index,)
        ).fetchone()
        conn.close()
        return Block.from_json(row[0]) if row else None

    def load_chain(self):
        conn = sqlite3.connect(self.db_file)
        rows = conn.execute(
            "SELECT data FROM blocks ORDER BY block_index ASC"
        ).fetchall()
        conn.close()
        return [Block.from_json(row[0]) for row in rows]

    def get_public_key_by_name(self, name):
        with sqlite3.connect(self.db_file) as conn:
            res = conn.execute(
                "SELECT public_key FROM participants WHERE name = ?", (name,)
            ).fetchone()
        return res[0] if res else None

    def get_name_by_public_key(self, pk):
        with sqlite3.connect(self.db_file) as conn:
            res = conn.execute(
                "SELECT name FROM participants WHERE public_key = ?", (pk,)
            ).fetchone()
        return res[0] if res else "Unknown"
