import hashlib
import json
import time
import sqlite3
from enum import Enum
from typing import List, Dict, Any

# --- Data Models ---


class ActionType(Enum):
    MANUFACTURED = "MANUFACTURED"
    SHIPPED = "SHIPPED"
    RECEIVED = "RECEIVED"
    SOLD = "SOLD"


class Transaction:
    def __init__(
        self,
        sender_public_key: str,
        receiver_public_key: str,
        product_id: str,
        action: ActionType,
        location: str,
        metadata: Dict[str, Any] = None,
        timestamp: float = None,
    ):
        self.sender = sender_public_key
        self.receiver = receiver_public_key
        self.product_id = product_id
        self.action = action.value if isinstance(action, ActionType) else action
        self.timestamp = timestamp if timestamp else time.time()
        self.location = location
        self.metadata = metadata if metadata else {}
        self.tx_hash = self.calculate_hash()

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "product_id": self.product_id,
            "action": self.action,
            "timestamp": self.timestamp,
            "location": self.location,
            "metadata": self.metadata,
        }

    def calculate_hash(self):
        tx_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()


class Block:
    def __init__(
        self,
        index: int,
        transactions: List[Transaction],
        previous_hash: str,
        validator_address: str,
        timestamp: float = None,
    ):
        self.index = index
        self.timestamp = timestamp if timestamp else time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.validator = validator_address
        self.merkle_root = self.compute_merkle_root()
        self.hash = self.calculate_block_hash()

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
                "transactions": [tx.to_dict() for tx in self.transactions],
                "previous_hash": self.previous_hash,
                "validator": self.validator,
                "merkle_root": self.merkle_root,
                "hash": self.hash,
            }
        )


# --- Blockchain Node Logic ---


class BlockchainNode:
    def __init__(self, db_file="transactions_DB.db"):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        # Ledger
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, block_hash TEXT UNIQUE, previous_hash TEXT, validator TEXT, timestamp REAL, data TEXT)"
        )
        # World State Entities
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS participants (public_key TEXT PRIMARY KEY, role TEXT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS products (product_id TEXT PRIMARY KEY, details TEXT)"
        )
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ownership_state (
                product_id TEXT PRIMARY KEY, current_owner TEXT, current_location TEXT, 
                last_action TEXT, last_updated_timestamp REAL,
                FOREIGN KEY(product_id) REFERENCES products(product_id),
                FOREIGN KEY(current_owner) REFERENCES participants(public_key)
            )
        """)
        conn.commit()
        conn.close()

    def save_block(self, block: Block):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            # Save to Ledger
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

            # Update World State (Supreme Logic: Auto-creates entities if missing)
            for tx in block.transactions:
                cursor.execute(
                    "INSERT OR IGNORE INTO participants (public_key, role) VALUES (?, ?)",
                    (tx.sender, "Actor"),
                )
                cursor.execute(
                    "INSERT OR IGNORE INTO participants (public_key, role) VALUES (?, ?)",
                    (tx.receiver, "Actor"),
                )
                cursor.execute(
                    "INSERT OR IGNORE INTO products (product_id, details) VALUES (?, ?)",
                    (tx.product_id, "Standard Item"),
                )
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO ownership_state (product_id, current_owner, current_location, last_action, last_updated_timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (tx.product_id, tx.receiver, tx.location, tx.action, tx.timestamp),
                )

            conn.commit()
            print(f"✅ Block {block.index} saved successfully.")
        except sqlite3.IntegrityError as e:
            print(f"⚠️ Integrity Error: {e}")
        finally:
            conn.close()

    def load_chain(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM blocks ORDER BY block_index ASC")
        rows = cursor.fetchall()
        chain = []
        for row in rows:
            d = json.loads(row[0])
            txs = [
                Transaction(
                    t["sender"],
                    t["receiver"],
                    t["product_id"],
                    ActionType(t["action"]),
                    t["location"],
                    t["metadata"],
                    t["timestamp"],
                )
                for t in d["transactions"]
            ]
            chain.append(
                Block(
                    d["index"], txs, d["previous_hash"], d["validator"], d["timestamp"]
                )
            )
        conn.close()
        return chain

    # --- Validation Helpers for Strict Mode ---
    def participant_exists(self, key):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute(
            "SELECT 1 FROM participants WHERE public_key = ?", (key,)
        ).fetchone()
        conn.close()
        return res is not None

    def product_exists(self, pid):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute(
            "SELECT 1 FROM products WHERE product_id = ?", (pid,)
        ).fetchone()
        conn.close()
        return res is not None

    def get_world_state(self):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute("SELECT * FROM ownership_state").fetchall()
        conn.close()
        return res


if __name__ == "__main__":
    node = BlockchainNode()
    print("✅ Database initialized at 'transactions_DB.db'")
