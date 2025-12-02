import os
import time
import sys
import random
import sqlite3
from blockchain_core import BlockchainNode, Transaction, ActionType, Block
import p2p

NODES_DIR = "nodes"


def get_node_env(name):
    """Loads the node's environment (DB and Private Key)."""
    path = os.path.join(NODES_DIR, name)
    db = os.path.join(path, "blockchain.db")
    pk_path = os.path.join(path, "private_key.pem")

    if not os.path.exists(pk_path):
        raise FileNotFoundError(f"Node {name} not found. Run setup_network.py first.")

    with open(pk_path, "r") as f:
        pk = f.read().strip()
    return BlockchainNode(name, db), pk


def create_and_send_tx(node_name, tx_data, description):
    """Creates, signs, and broadcasts a transaction."""
    print(f"   [ACTION] {node_name}: {description}")
    node, priv_key = get_node_env(node_name)
    sender_pub = node.get_public_key_by_name(node_name)

    tx = None

    # 1. VOTE
    if tx_data["action"] == ActionType.VOTE:
        candidate_pub = node.get_public_key_by_name(tx_data["candidate"])
        tx = Transaction(
            sender_pub,
            candidate_pub,
            f"VOTE-{int(time.time())}",
            ActionType.VOTE,
            "BallotBox",
        )

    # 2. NEW ASSET (EXTRACTED / MANUFACTURED)
    elif tx_data["action"] in [ActionType.EXTRACTED, ActionType.MANUFACTURED]:
        metadata = tx_data.get("metadata", {})
        tx = Transaction(
            sender_pub,
            sender_pub,
            tx_data["ship_id"],
            tx_data["action"],
            tx_data["loc"],
            tx_data["good"],
            tx_data["qty"],
            metadata=metadata,
        )

    # 3. TRANSFER (SHIPPED)
    elif tx_data["action"] == ActionType.SHIPPED:
        rec_pub = node.get_public_key_by_name(tx_data["receiver"])
        tx = Transaction(
            sender_pub, rec_pub, tx_data["ship_id"], ActionType.SHIPPED, tx_data["loc"]
        )

    # 4. STATE UPDATE (RECEIVED)
    elif tx_data["action"] == ActionType.RECEIVED:
        qty = tx_data.get("qty", None)
        good = tx_data.get("good", None)
        tx = Transaction(
            sender_pub,
            sender_pub,
            tx_data["ship_id"],
            ActionType.RECEIVED,
            tx_data["loc"],
            good_id=good,
            quantity=qty,
        )

    # 5. CONSUME / DESTROY / SELL
    elif tx_data["action"] in [
        ActionType.SOLD,
        ActionType.DESTROYED,
        ActionType.CONSUMED,
    ]:
        metadata = tx_data.get("metadata", {})
        tx = Transaction(
            sender_pub,
            sender_pub,
            tx_data["ship_id"],
            tx_data["action"],
            tx_data["loc"],
            metadata=metadata,
        )

    if tx and tx.sign_transaction(priv_key):
        success, msg = node.add_to_mempool(tx)
        if success:
            p2p.broadcast_transaction(node_name, tx)
            return True
        else:
            print(f"      [!] Mempool rejected tx: {msg}")
            return False
    return False


def run_consensus_round():
    """Simulates a DPoS round: elects a delegate, forges a block, and broadcasts."""
    print(f"\n   --- CONSENSUS ROUND (DPoS) ---")
    node, _ = get_node_env("GlobalMining_Corp")
    last = node.get_last_block()
    prev = last.hash if last else "0" * 64

    # 1. Elect Delegate
    val_name = node.select_validator(prev)
    print(f"      > Elected Delegate (Witness): {val_name}")

    # 2. Validator Forges Block
    val_node, _ = get_node_env(val_name)
    pending = val_node.get_mempool_transactions()

    if pending:
        print(
            f"      > {val_name} forging block #{last.index + 1 if last else 1} with {len(pending)} transactions..."
        )
        new_idx = (last.index + 1) if last else 1
        block = Block(new_idx, pending, prev, val_name)

        # 3. Save & Broadcast
        val_node.save_block_to_db(block)
        val_node.clear_mempool(pending)
        p2p.broadcast_block(val_name, block)
    else:
        print("      > Mempool empty. No block produced.")

    time.sleep(0.5)


def verify_counts():
    """Connects to a node's DB to count the final state."""
    print("\n" + "=" * 60)
    print("FINAL STATE VERIFICATION")
    print("=" * 60)

    # We can check any node's DB since they should be synced
    db_path = os.path.join(NODES_DIR, "Corner_Store", "blockchain.db")
    conn = sqlite3.connect(db_path)

    # Count by Last Action
    rows = conn.execute("""
        SELECT last_action, COUNT(*) 
        FROM shipments 
        WHERE is_active = 1 
        GROUP BY last_action
    """).fetchall()

    print(f"{'STATUS':<20} | {'COUNT':<10}")
    print("-" * 35)

    counts = {action: count for action, count in rows}
    total_active = sum(counts.values())

    for action, count in counts.items():
        print(f"{action:<20} | {count:<10}")

    print("-" * 35)
    print(f"{'TOTAL ACTIVE':<20} | {total_active:<10}")
    conn.close()


# --- MAIN SCENARIO ---


def run_simulation():
    if not os.path.exists(NODES_DIR):
        print("Error: Node directories not found. Please run 'setup_network.py' first.")
        return

    print("\n" + "=" * 60)
    print("BLOCKCHAIN SUPPLY CHAIN SIMULATION")
    print("Goal: Generate MANUFACTURED and RECEIVED items for counting.")
    print("=" * 60)

    # --- PHASE 1: SETUP & ELECTION ---
    print("\n=== PHASE 1: INITIALIZATION ===")
    # Ensure delegates are active
    create_and_send_tx(
        "Corner_Store",
        {"action": ActionType.VOTE, "candidate": "TechFoundry_Inc"},
        "Voting for TechFoundry",
    )
    create_and_send_tx(
        "Truck_Fleet_Alpha",
        {"action": ActionType.VOTE, "candidate": "Pacific_Logistics"},
        "Voting for Pacific_Logistics",
    )
    run_consensus_round()

    # --- PHASE 2: CREATE 'RECEIVED' ITEMS ---
    # We will Create -> Ship -> Receive multiple items so they end up as RECEIVED
    print("\n=== PHASE 2: GENERATING 'RECEIVED' STOCK ===")

    # Batch 1: Retail Goods (Wheat)
    ship_id_1 = "SHIP-5001"
    create_and_send_tx(
        "GlobalMining_Corp",
        {
            "action": ActionType.EXTRACTED,
            "ship_id": ship_id_1,
            "loc": "Farm",
            "good": "G-WHT",
            "qty": 1000,
        },
        "Extracting Wheat",
    )

    # Batch 2: Retail Goods (Water)
    ship_id_2 = "SHIP-5002"
    create_and_send_tx(
        "CleanWater_Services",
        {
            "action": ActionType.EXTRACTED,
            "ship_id": ship_id_2,
            "loc": "Plant",
            "good": "G-H2O",
            "qty": 5000,
        },
        "Extracting Water",
    )

    run_consensus_round()

    # Ship to Store
    create_and_send_tx(
        "GlobalMining_Corp",
        {
            "action": ActionType.SHIPPED,
            "ship_id": ship_id_1,
            "loc": "Train",
            "receiver": "Corner_Store",
        },
        "Shipping Wheat",
    )

    create_and_send_tx(
        "CleanWater_Services",
        {
            "action": ActionType.SHIPPED,
            "ship_id": ship_id_2,
            "loc": "Pipe",
            "receiver": "Corner_Store",
        },
        "Shipping Water",
    )

    run_consensus_round()

    # Store Receives (These 2 items will stay as RECEIVED)
    create_and_send_tx(
        "Corner_Store",
        {"action": ActionType.RECEIVED, "ship_id": ship_id_1, "loc": "Store Shelf"},
        "Store Receives Wheat",
    )

    create_and_send_tx(
        "Corner_Store",
        {"action": ActionType.RECEIVED, "ship_id": ship_id_2, "loc": "Store Fridge"},
        "Store Receives Water",
    )

    run_consensus_round()

    # --- PHASE 3: CREATE 'MANUFACTURED' ITEMS ---
    # We will Extract -> Consume -> Manufacture items that stay at the factory (MANUFACTURED)
    print("\n=== PHASE 3: GENERATING 'MANUFACTURED' STOCK ===")

    # 1. Get Raw Materials
    raw_id_1 = "SHIP-5003"
    raw_id_2 = "SHIP-5004"

    create_and_send_tx(
        "GlobalMining_Corp",
        {
            "action": ActionType.EXTRACTED,
            "ship_id": raw_id_1,
            "loc": "Mine",
            "good": "G-LI",
            "qty": 500,
        },
        "Extracting Lithium",
    )

    create_and_send_tx(
        "OPEC_Supplier",
        {
            "action": ActionType.EXTRACTED,
            "ship_id": raw_id_2,
            "loc": "Rig",
            "good": "G-OIL",
            "qty": 500,
        },
        "Extracting Oil",
    )

    run_consensus_round()

    # 2. Ship to Manufacturer
    create_and_send_tx(
        "GlobalMining_Corp",
        {
            "action": ActionType.SHIPPED,
            "ship_id": raw_id_1,
            "loc": "Truck",
            "receiver": "TechFoundry_Inc",
        },
        "Shipping Lithium",
    )

    create_and_send_tx(
        "OPEC_Supplier",
        {
            "action": ActionType.SHIPPED,
            "ship_id": raw_id_2,
            "loc": "Tanker",
            "receiver": "TechFoundry_Inc",
        },
        "Shipping Oil",
    )

    run_consensus_round()

    # 3. Manufacturer Receives (Internal step)
    create_and_send_tx(
        "TechFoundry_Inc",
        {"action": ActionType.RECEIVED, "ship_id": raw_id_1, "loc": "Factory"},
        "Receiving Lithium",
    )

    create_and_send_tx(
        "TechFoundry_Inc",
        {"action": ActionType.RECEIVED, "ship_id": raw_id_2, "loc": "Factory"},
        "Receiving Oil",
    )

    run_consensus_round()

    # 4. Manufacture (Consumes Raw, Creates New)
    # Consume inputs
    create_and_send_tx(
        "TechFoundry_Inc",
        {
            "action": ActionType.CONSUMED,
            "ship_id": raw_id_1,
            "loc": "Furnace",
            "metadata": {"product": "Microchips"},
        },
        "Consuming Lithium",
    )

    create_and_send_tx(
        "TechFoundry_Inc",
        {
            "action": ActionType.CONSUMED,
            "ship_id": raw_id_2,
            "loc": "Furnace",
            "metadata": {"product": "Microchips"},
        },
        "Consuming Oil",
    )

    # Create Product (This will stay as MANUFACTURED)
    manuf_id_1 = "SHIP-5005"
    create_and_send_tx(
        "TechFoundry_Inc",
        {
            "action": ActionType.MANUFACTURED,
            "ship_id": manuf_id_1,
            "loc": "Assembly Line",
            "good": "G-CHIP",
            "qty": 1000,
            "metadata": {"source_materials": [raw_id_1, raw_id_2]},
        },
        "Manufacturing Microchips",
    )

    # Create another Product directly (Simulating immediate production)
    manuf_id_2 = "SHIP-5006"
    create_and_send_tx(
        "TechFoundry_Inc",
        {
            "action": ActionType.MANUFACTURED,
            "ship_id": manuf_id_2,
            "loc": "Lab",
            "good": "G-PHONE",
            "qty": 200,
        },
        "Manufacturing Smartphones",
    )

    run_consensus_round()

    # --- PHASE 4: FINAL VERIFICATION ---
    verify_counts()


if __name__ == "__main__":
    run_simulation()
