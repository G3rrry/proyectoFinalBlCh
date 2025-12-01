import hashlib
import json
import time
import sqlite3
import os
import shutil
import random
from enum import Enum
from typing import List, Dict, Any
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError

# --- Configuration ---
DB_FILE = "transactions_DB.db"
KEYS_FOLDER = "initial_participants"

# --- Data Models ---


class ActionType(Enum):
    EXTRACTED = "EXTRACTED"
    PROCESSED = "PROCESSED"
    SHIPPED = "SHIPPED"
    RECEIVED = "RECEIVED"
    SOLD = "SOLD"


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
            message = self.calculate_hash().encode()
            signature = sk.sign(message)
            self.signature = signature.hex()
            return True
        except Exception as e:
            print(f"Error signing: {e}")
            return False

    def is_valid(self):
        if not self.signature:
            return False
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(self.sender), curve=SECP256k1)
            message = self.calculate_hash().encode()
            return vk.verify(bytes.fromhex(self.signature), message)
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


# --- Blockchain Node Logic ---


class BlockchainNode:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 1. LEDGER
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, block_hash TEXT UNIQUE, previous_hash TEXT, validator TEXT, timestamp REAL, data TEXT)"
        )

        # 2. PARTICIPANTS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                name TEXT UNIQUE, 
                public_key TEXT PRIMARY KEY, 
                role TEXT,
                reputation INTEGER DEFAULT 0
            )
        """)

        # 3. GOODS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goods (
                good_id TEXT PRIMARY KEY, 
                name TEXT,
                unit_of_measure TEXT
            )
        """)

        # 4. SHIPMENTS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                shipment_id TEXT PRIMARY KEY, 
                good_id TEXT,
                quantity REAL,
                current_owner_pk TEXT, 
                current_location TEXT, 
                last_action TEXT, 
                last_updated_timestamp REAL,
                FOREIGN KEY(good_id) REFERENCES goods(good_id),
                FOREIGN KEY(current_owner_pk) REFERENCES participants(public_key)
            )
        """)
        conn.commit()
        conn.close()

    def get_dpos_validator(self, block_index: int):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM participants ORDER BY reputation DESC LIMIT 3")
        delegates = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not delegates:
            return "Genesis_Validator"
        return delegates[block_index % len(delegates)]

    def save_block(self, block: Block):
        block.validator = self.get_dpos_validator(block.index)
        block.hash = block.calculate_block_hash()

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
                if tx.action in ["EXTRACTED", "PROCESSED"] and tx.quantity:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO shipments (shipment_id, good_id, quantity, current_owner_pk, current_location, last_action, last_updated_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
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
                    cursor.execute(
                        """
                        UPDATE shipments 
                        SET current_owner_pk = ?, current_location = ?, last_action = ?, last_updated_timestamp = ?
                        WHERE shipment_id = ?
                    """,
                        (
                            tx.receiver,
                            tx.location,
                            tx.action,
                            tx.timestamp,
                            tx.shipment_id,
                        ),
                    )

            conn.commit()
            print(f"Block {block.index} saved. Validator: {block.validator}")
        except sqlite3.IntegrityError as e:
            print(f"Integrity Error: {e}")
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
            txs = []
            for t in d["transactions"]:
                new_tx = Transaction(
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
                txs.append(new_tx)
            chain.append(
                Block(
                    d["index"], txs, d["previous_hash"], d["validator"], d["timestamp"]
                )
            )
        conn.close()
        return chain

    def get_public_key_by_name(self, name):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute(
            "SELECT public_key FROM participants WHERE name = ?", (name,)
        ).fetchone()
        conn.close()
        return res[0] if res else None

    def get_name_by_public_key(self, pk):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute(
            "SELECT name FROM participants WHERE public_key = ?", (pk,)
        ).fetchone()
        conn.close()
        return res[0] if res else "Unknown"

    def get_good_info(self, good_id):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute(
            "SELECT name, unit_of_measure FROM goods WHERE good_id = ?", (good_id,)
        ).fetchone()
        conn.close()
        return res

    def get_shipment(self, shipment_id):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute(
            "SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,)
        ).fetchone()
        conn.close()
        return res

    def get_world_state(self):
        conn = sqlite3.connect(self.db_file)
        res = conn.execute("SELECT * FROM shipments").fetchall()
        conn.close()
        return res


# --- Initialization Helper ---


def populate_initial_data():
    if os.path.exists(KEYS_FOLDER):
        shutil.rmtree(KEYS_FOLDER)
    os.makedirs(KEYS_FOLDER)

    node = BlockchainNode()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. GOODS DEFINITION
    goods_data = [
        ("G-LI", "Lithium Ore", "Tonnes"),
        ("G-TI", "Titanium Alloy", "Kg"),
        ("G-OIL", "Crude Oil", "Barrels"),
        ("G-H2O", "Industrial Water", "Liters"),
        ("G-WHT", "Wheat", "Tonnes"),
        ("G-CHIP", "Silicon Microchips", "Units"),
        ("G-PHONE", "Smartphone V15", "Units"),
        ("G-MED", "Vaccines", "Vials"),
    ]
    print("--- DEFINING GOODS ---")
    for gid, name, unit in goods_data:
        cursor.execute(
            "INSERT OR IGNORE INTO goods (good_id, name, unit_of_measure) VALUES (?, ?, ?)",
            (gid, name, unit),
        )
        print(f"   Defined: {name} ({unit})")

    # 2. PARTICIPANTS
    participants = [
        ("GlobalMining_Corp", 100, "Extractor"),
        ("Pacific_Logistics", 95, "Logistics"),
        ("TechFoundry_Inc", 90, "Manufacturer"),
        ("CargoShip_EverGiven", 10, "Transporter"),
        ("FreightTrain_Express", 10, "Transporter"),
        ("Truck_Fleet_Alpha", 5, "Transporter"),
        ("Drone_Delivery_X", 5, "Transporter"),
        ("OPEC_Supplier", 50, "Extractor"),
        ("CleanWater_Services", 40, "Utility"),
        ("Mega_Consumer_Goods", 60, "Retailer"),
        ("Corner_Store", 5, "Retailer"),
    ]

    print("\n--- GENERATING PARTICIPANTS & KEYS ---")
    for name, rep, role in participants:
        sk = SigningKey.generate(curve=SECP256k1)
        vk = sk.verifying_key
        private_hex = sk.to_string().hex()
        public_hex = vk.to_string().hex()

        filename = os.path.join(KEYS_FOLDER, f"{name}.pem")
        with open(filename, "w") as f:
            f.write(private_hex)

        cursor.execute(
            "INSERT OR IGNORE INTO participants (name, public_key, role, reputation) VALUES (?, ?, ?, ?)",
            (name, public_hex, role, rep),
        )
        print(f"   Created: {name} [{role}]")

    # --- CRITICAL FIX: COMMIT BEFORE QUERYING ---
    # We must commit here so that get_good_info() (which uses a new connection)
    # can see the goods we just inserted.
    conn.commit()
    # --------------------------------------------

    # 3. INITIAL SHIPMENTS
    print("\n--- CREATING GENESIS SHIPMENTS ---")

    genesis_shipments = [
        ("SHIP-1001", "G-LI", 500.0, "GlobalMining_Corp", "Nevada Mine"),
        ("SHIP-1002", "G-OIL", 1000.0, "OPEC_Supplier", "Offshore Platform"),
        ("SHIP-1003", "G-H2O", 50000.0, "CleanWater_Services", "Reservoir A"),
    ]

    for sh_id, g_id, qty, owner_name, loc in genesis_shipments:
        owner_pk = node.get_public_key_by_name(owner_name)
        cursor.execute(
            """
            INSERT OR IGNORE INTO shipments 
            (shipment_id, good_id, quantity, current_owner_pk, current_location, last_action, last_updated_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (sh_id, g_id, qty, owner_pk, loc, "EXTRACTED", time.time()),
        )

        # Now this will work because we committed the goods above
        g_name = node.get_good_info(g_id)[0]
        print(f"   Genesis: {qty} of {g_name} owned by {owner_name}")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    populate_initial_data()
    print("\nInitialization Complete.")
