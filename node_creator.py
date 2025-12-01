import os
import shutil
import sqlite3
import time
import sys
from ecdsa import SigningKey, SECP256k1
from initialize import BlockchainNode

# Constants
NODES_DIR = "nodes"
FILES_TO_INSTALL = [
    "initialize.py",
    "p2p.py",
    "add_transaction.py",
    "view_blockchain.py",
]


def sync_chain_from_peer(node_name, db_path):
    """
    Connects to the first available peer and downloads the blockchain.
    Replays blocks locally to build the World State (Shipments table).
    """
    peers = [
        d
        for d in os.listdir(NODES_DIR)
        if os.path.isdir(os.path.join(NODES_DIR, d)) and d != node_name
    ]

    if not peers:
        print("No peers found to sync with. Starting with Genesis state.")
        return

    peer_name = peers[0]
    peer_db = os.path.join(NODES_DIR, peer_name, "blockchain.db")
    print(f"Found peer '{peer_name}'. Starting Full Sync...")

    # 1. Fetch Blocks from Peer
    try:
        src_conn = sqlite3.connect(peer_db)
        # Fetch block data (JSON) in order
        cursor = src_conn.execute("SELECT data FROM blocks ORDER BY block_index ASC")
        block_rows = cursor.fetchall()
        src_conn.close()
    except Exception as e:
        print(f"Error reading peer database: {e}")
        return

    if not block_rows:
        print("Peer blockchain is empty.")
        return

    # 2. Replay Blocks on Local Node
    # We use a temporary node instance to access the `save_block_to_db` logic
    # which automatically updates the 'shipments' table (World State).
    node = BlockchainNode(node_name, db_path)

    # Clear any existing state (like Genesis created during init) to prevent conflicts
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM blocks")
    conn.execute("DELETE FROM shipments")
    conn.commit()
    conn.close()

    print(f"Downloading and verifying {len(block_rows)} blocks...")

    for row in block_rows:
        block_json = row[0]
        block = node.json_to_block(block_json)
        # This saves the block AND updates the shipment ownership/location
        node.save_block_to_db(block)
        sys.stdout.write(".")
        sys.stdout.flush()

    print("\nSync Complete. Local World State matches the Network.")


def create_new_node():
    print("\n--- CREATE NEW DECENTRALIZED NODE ---")

    if not os.path.exists(NODES_DIR):
        print(
            f"Error: '{NODES_DIR}' directory not found. Please run 'setup_network.py' first."
        )
        return

    while True:
        name = input("Enter unique participant name (e.g., MyTransportCo): ").strip()
        if not name:
            print("Name cannot be empty.")
            continue
        if " " in name:
            print("Name cannot contain spaces. Use underscores.")
            continue

        node_path = os.path.join(NODES_DIR, name)
        if os.path.exists(node_path):
            print(f"Error: Node '{name}' already exists. Try another name.")
            continue
        break

    # 1. Generate Identity
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.verifying_key
    private_key_hex = sk.to_string().hex()
    public_key_hex = vk.to_string().hex()

    print(f"\nGenerating Identity for {name}...")

    # 2. Create Node Directory
    os.makedirs(node_path)

    # 3. Install Software
    print("Installing node software...")
    for filename in FILES_TO_INSTALL:
        if os.path.exists(filename):
            shutil.copy(filename, os.path.join(node_path, filename))
        else:
            print(f"Warning: Source file {filename} missing.")

    # 4. Save Key
    with open(os.path.join(node_path, "private_key.pem"), "w") as f:
        f.write(private_key_hex)

    # 5. Initialize Database (Structure Only)
    db_path = os.path.join(node_path, "blockchain.db")
    node = BlockchainNode(name, db_path)

    # 6. SYNC BLOCKCHAIN STATE
    # Instead of creating a new Genesis state, we download history from peers.
    sync_chain_from_peer(name, db_path)

    # 7. ADD SELF & STANDARD GOODS (If Sync didn't cover it)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Ensure standard goods exist (in case peer was empty)
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
    for g in goods_data:
        c.execute("INSERT OR IGNORE INTO goods VALUES (?,?,?)", g)

    # Add Self to Address Book
    c.execute(
        "INSERT OR IGNORE INTO participants VALUES (?,?,?,?)",
        (name, public_key_hex, "User_Created", 10),
    )
    conn.commit()
    conn.close()

    # 8. BROADCAST IDENTITY (Sync Address Books)
    print("Broadcasting identity to network peers...")
    peers = [
        d for d in os.listdir(NODES_DIR) if os.path.isdir(os.path.join(NODES_DIR, d))
    ]

    for peer in peers:
        if peer == name:
            continue

        peer_db = os.path.join(NODES_DIR, peer, "blockchain.db")
        if not os.path.exists(peer_db):
            continue

        try:
            # Connect to PEER DB
            p_conn = sqlite3.connect(peer_db)
            p_cursor = p_conn.cursor()

            # Get Peer Info
            peer_info = p_cursor.execute(
                "SELECT name, public_key, role, reputation FROM participants WHERE name = ?",
                (peer,),
            ).fetchone()

            # Insert NEW USER into PEER DB
            p_cursor.execute(
                "INSERT OR IGNORE INTO participants VALUES (?,?,?,?)",
                (name, public_key_hex, "User_Created", 10),
            )
            p_conn.commit()
            p_conn.close()

            # Insert PEER INFO into NEW USER DB
            if peer_info:
                my_conn = sqlite3.connect(db_path)
                my_conn.execute(
                    "INSERT OR IGNORE INTO participants VALUES (?,?,?,?)", peer_info
                )
                my_conn.commit()
                my_conn.close()

        except Exception as e:
            print(f"Warning: Could not sync with {peer}: {e}")

    print(f"\nSUCCESS: Node '{name}' created in 'nodes/{name}/' and fully synced.")


if __name__ == "__main__":
    create_new_node()
