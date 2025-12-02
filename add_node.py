import os
import shutil
import sqlite3
import sys
from ecdsa import SigningKey, SECP256k1
from blockchain_core import BlockchainNode

NODES_DIR = "nodes"
FILES_TO_INSTALL = [
    "blockchain_core.py",
    "p2p.py",
    "add_transaction.py",
    "view_blockchain.py",
    "validate.py",
]


def get_existing_nodes():
    if not os.path.exists(NODES_DIR):
        return []
    return [
        d for d in os.listdir(NODES_DIR) if os.path.isdir(os.path.join(NODES_DIR, d))
    ]


def add_node(name, role="Observer", reputation=10):
    if os.path.exists(os.path.join(NODES_DIR, name)):
        print(f"Error: Node '{name}' already exists.")
        return

    print(f"--- CREATING NEW NODE: {name} ---")

    # 1. Generate Identity
    sk = SigningKey.generate(curve=SECP256k1)
    sk_hex = sk.to_string().hex()
    pk = sk.verifying_key.to_string().hex()
    print(f"   > Generated Identity (Public Key: {pk[:10]}...)")

    # 2. Create Directory & Install Files
    node_path = os.path.join(NODES_DIR, name)
    os.makedirs(node_path)

    for filename in FILES_TO_INSTALL:
        if os.path.exists(filename):
            shutil.copy(filename, os.path.join(node_path, filename))
        else:
            print(f"   > Warning: Source file {filename} not found.")

    with open(os.path.join(node_path, "private_key.pem"), "w") as f:
        f.write(sk_hex)

    # 3. Initialize Database
    db_path = os.path.join(node_path, "blockchain.db")
    BlockchainNode(name, db_path)  # Creates empty tables

    # 4. Bootstrap / Sync with Network
    existing_nodes = get_existing_nodes()
    # Filter out self (just in case directory was created before list check)
    neighbors = [n for n in existing_nodes if n != name]

    conn_new = sqlite3.connect(db_path)

    # Register self in own DB
    conn_new.execute(
        "INSERT INTO participants (name, public_key, role, reputation, votes) VALUES (?,?,?,?,?)",
        (name, pk, role, reputation, 0),
    )

    if neighbors:
        # Pick a neighbor to sync state from
        seed_node = neighbors[0]
        print(f"   > Syncing state from {seed_node}...")

        seed_db = os.path.join(NODES_DIR, seed_node, "blockchain.db")

        # Attach seed DB to copy data efficiently
        conn_new.execute(f"ATTACH DATABASE '{seed_db}' AS seed")

        # Copy Participants (Address Book)
        conn_new.execute(
            "INSERT OR IGNORE INTO participants SELECT * FROM seed.participants"
        )

        # Copy Goods definitions
        conn_new.execute("INSERT OR IGNORE INTO goods SELECT * FROM seed.goods")

        # Copy Shipments (World State)
        conn_new.execute("INSERT OR IGNORE INTO shipments SELECT * FROM seed.shipments")

        # Copy Blockchain History
        conn_new.execute("INSERT OR IGNORE INTO blocks SELECT * FROM seed.blocks")

        # Copy Mempool
        conn_new.execute("INSERT OR IGNORE INTO mempool SELECT * FROM seed.mempool")

        conn_new.commit()
        conn_new.execute("DETACH DATABASE seed")

        # 5. Broadcast Existence (Update other nodes' participant lists)
        print("   > Announcing to network (updating peer address books)...")
        for neighbor in neighbors:
            n_db_path = os.path.join(NODES_DIR, neighbor, "blockchain.db")
            try:
                with sqlite3.connect(n_db_path) as conn_n:
                    conn_n.execute(
                        "INSERT OR IGNORE INTO participants (name, public_key, role, reputation, votes) VALUES (?,?,?,?,?)",
                        (name, pk, role, reputation, 0),
                    )
                    conn_n.commit()
            except Exception as e:
                print(f"     ! Failed to update {neighbor}: {e}")

    else:
        print("   > No existing nodes found. This is the first node (Genesis).")
        # Initialize default goods if it's the very first node manually created
        goods_data = [
            ("G-LI", "Lithium Ore", "Tonnes"),
            ("G-CHIP", "Silicon Microchips", "Units"),
            ("G-PHONE", "Smartphone V15", "Units"),
            ("G-WHT", "Wheat", "Tonnes"),
        ]
        for g in goods_data:
            conn_new.execute("INSERT OR IGNORE INTO goods VALUES (?,?,?)", g)

    conn_new.commit()
    conn_new.close()

    print(f"\nNode '{name}' successfully added to the network.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n--- Add New Node ---")
        name = input("Enter Node Name (e.g., Retail_Z): ").strip()
        if not name:
            print("Name required.")
            sys.exit(1)
        role = input("Enter Role (default: Observer): ").strip() or "Observer"
    else:
        name = sys.argv[1]
        role = sys.argv[2] if len(sys.argv) > 2 else "Observer"

    add_node(name, role)
