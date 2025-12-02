import os
import time
import sys
from initialize import BlockchainNode, Transaction, ActionType
import p2p

NODES_DIR = "nodes"


def get_node_env(name):
    path = os.path.join(NODES_DIR, name)
    db = os.path.join(path, "blockchain.db")
    with open(os.path.join(path, "private_key.pem"), "r") as f:
        pk = f.read().strip()
    return BlockchainNode(name, db), pk


def step_1_user_creates_tx(node_name, tx_data, description):
    print(f"\n--- 1. USER ACTION: {description} ({node_name}) ---")
    node, priv_key = get_node_env(node_name)
    sender_pub = node.get_public_key_by_name(node_name)

    # Construct TX
    tx = None
    if tx_data["action"] == ActionType.EXTRACTED:
        tx = Transaction(
            sender_pub,
            sender_pub,
            tx_data["ship_id"],
            ActionType.EXTRACTED,
            tx_data["loc"],
            tx_data["good"],
            tx_data["qty"],
        )
    elif tx_data["action"] == ActionType.SHIPPED:
        rec_pub = node.get_public_key_by_name(tx_data["receiver"])
        tx = Transaction(
            sender_pub, rec_pub, tx_data["ship_id"], ActionType.SHIPPED, tx_data["loc"]
        )
    elif tx_data["action"] == ActionType.RECEIVED:
        tx = Transaction(
            sender_pub,
            sender_pub,
            tx_data["ship_id"],
            ActionType.RECEIVED,
            tx_data["loc"],
        )
    elif tx_data["action"] == ActionType.DESTROYED:
        tx = Transaction(
            sender_pub,
            sender_pub,
            tx_data["ship_id"],
            ActionType.DESTROYED,
            "Destroyed",
            metadata={"reason": "Simulation End"},
        )

    # Sign and Broadcast
    if tx and tx.sign_transaction(priv_key):
        node.add_to_mempool(tx)
        p2p.broadcast_transaction(node_name, tx)
        print(f"   > Transaction {tx.tx_hash[:8]} sent to Mempool.")
    else:
        print("   > Error signing.")


def step_2_validator_works():
    print(f"\n--- 2. CONSENSUS: Validator processes Mempool ---")
    # We check any node to see who the network expects as validator
    node, _ = get_node_env("GlobalMining_Corp")
    last = node.get_last_block()
    prev = last.hash if last else "0" * 64

    val_name = node.select_validator(prev)
    print(f"   > Network consensus elected: {val_name}")

    # Switch to the elected validator
    val_node, _ = get_node_env(val_name)
    pending = val_node.get_mempool_transactions()

    if pending:
        print(f"   > {val_name} found {len(pending)} txs in mempool.")
        new_idx = (last.index + 1) if last else 1
        from initialize import Block

        block = Block(new_idx, pending, prev, val_name)

        val_node.save_block_to_db(block)
        val_node.clear_mempool(pending)
        p2p.broadcast_block(val_name, block)
    else:
        print("   > Mempool empty.")
    time.sleep(1)


def run_simulation():
    if not os.path.exists(NODES_DIR):
        return print("Run setup first.")

    ship_id = "SHIP-STRICT-01"

    # 1. Extraction
    step_1_user_creates_tx(
        "GlobalMining_Corp",
        {
            "action": ActionType.EXTRACTED,
            "ship_id": ship_id,
            "loc": "Mine",
            "good": "G-LI",
            "qty": 100,
        },
        "Mining Lithium",
    )
    step_2_validator_works()

    # 2. Shipping
    step_1_user_creates_tx(
        "GlobalMining_Corp",
        {
            "action": ActionType.SHIPPED,
            "ship_id": ship_id,
            "loc": "Truck",
            "receiver": "Pacific_Logistics",
        },
        "Handover to Logistics",
    )
    step_2_validator_works()

    # 3. Logistics Receives
    step_1_user_creates_tx(
        "Pacific_Logistics",
        {"action": ActionType.RECEIVED, "ship_id": ship_id, "loc": "Warehouse"},
        "Logistics Receives",
    )

    # 4. Goods Damaged (Destroyed)
    step_1_user_creates_tx(
        "Pacific_Logistics",
        {"action": ActionType.DESTROYED, "ship_id": ship_id, "loc": "Incinerator"},
        "Goods Damaged",
    )

    step_2_validator_works()


if __name__ == "__main__":
    run_simulation()
