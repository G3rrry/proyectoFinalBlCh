import os
import time
import sys
import random
from initialize import BlockchainNode, Transaction, Block, ActionType
import p2p

# Directories
NODES_DIR = "nodes"


def get_node_environment(node_name):
    """
    Simulates 'logging in' to a specific node.
    Returns the Node object (connected to local DB) and the Private Key.
    """
    node_path = os.path.join(NODES_DIR, node_name)
    db_path = os.path.join(node_path, "blockchain.db")
    key_path = os.path.join(node_path, "private_key.pem")

    if not os.path.exists(node_path):
        raise FileNotFoundError(
            f"Node {node_name} does not exist. Run setup_network.py first."
        )

    # Load Private Key
    with open(key_path, "r") as f:
        private_key = f.read().strip()

    # Instantiate Node
    node = BlockchainNode(node_name, db_path)
    return node, private_key


def print_header(title):
    print("\n" + "=" * 80)
    print(f"{title:^80}")
    print("=" * 80)


def simulate_block_mining(node_name, transactions, block_title):
    """
    Helper to bundle transactions into a block, sign them, save locally, and broadcast.
    """
    print(f"\n--- {node_name} is processing: {block_title} ---")

    node, priv_key = get_node_environment(node_name)

    # 1. Sign Transactions
    valid_txs = []
    for tx in transactions:
        if tx.sign_transaction(priv_key):
            print(
                f"  [SIGNED] TX: {tx.action} {tx.shipment_id} ({tx.good_id or 'Transfer'})"
            )
            valid_txs.append(tx)
        else:
            print(f"  [ERROR] Failed to sign transaction for {tx.shipment_id}")

    if not valid_txs:
        return

    # 2. Prepare Block Metadata
    last_block = node.get_last_block()
    if last_block:
        new_index = last_block.index + 1
        prev_hash = last_block.hash
    else:
        new_index = 1
        prev_hash = "0" * 64

    # 3. Create Block
    new_block = Block(new_index, valid_txs, prev_hash, node_name)

    # 4. Mine Locally (Save to own DB)
    node.save_block_to_db(new_block)
    print(f"  [MINED] Block #{new_index} committed to {node_name}'s local ledger.")

    # 5. Broadcast to Network
    p2p.broadcast_block(node_name, new_block)
    time.sleep(1)  # Pause for visual clarity between blocks


def run_simulation():
    if not os.path.exists(NODES_DIR):
        print("Error: Network not found. Please run 'setup_network.py' first.")
        return

    print_header("STARTING DECENTRALIZED SUPPLY CHAIN SIMULATION")
    print("Scenario: Raw Materials -> Logistics -> Manufacturing -> Retail -> Sale")

    # --- SHARED DATA ---
    # We need to track Shipment IDs across different scopes/blocks
    ship_lithium = "SHIP-SIM-LI-01"
    ship_titanium = "SHIP-SIM-TI-01"
    ship_phones = "SHIP-SIM-PHONE-99"

    # =========================================================================
    # BLOCK 1: EXTRACTION (GlobalMining_Corp)
    # =========================================================================
    miner_name = "GlobalMining_Corp"
    miner_node, _ = get_node_environment(miner_name)
    miner_pub = miner_node.get_public_key_by_name(miner_name)

    tx1 = Transaction(
        miner_pub,
        miner_pub,
        ship_lithium,
        ActionType.EXTRACTED,
        "Nevada Mine",
        "G-LI",
        500.0,
    )
    tx2 = Transaction(
        miner_pub,
        miner_pub,
        ship_titanium,
        ActionType.EXTRACTED,
        "Nevada Mine",
        "G-TI",
        200.0,
    )

    simulate_block_mining(miner_name, [tx1, tx2], "Raw Material Extraction")

    # =========================================================================
    # BLOCK 2: HANDOVER TO LOGISTICS (GlobalMining -> Pacific_Logistics)
    # =========================================================================
    logistics_name = "Pacific_Logistics"
    logistics_node, _ = get_node_environment(logistics_name)
    logistics_pub = logistics_node.get_public_key_by_name(logistics_name)

    # Note: Sender is still GlobalMining, initiating the transfer
    tx3 = Transaction(
        miner_pub, logistics_pub, ship_lithium, ActionType.SHIPPED, "Loading Dock A"
    )
    tx4 = Transaction(
        miner_pub, logistics_pub, ship_titanium, ActionType.SHIPPED, "Loading Dock A"
    )

    simulate_block_mining(miner_name, [tx3, tx4], "Handover to Logistics")

    # =========================================================================
    # BLOCK 3: TRANSPORT & DELIVERY (Pacific_Logistics -> TechFoundry_Inc)
    # =========================================================================
    factory_name = "TechFoundry_Inc"
    factory_node, _ = get_node_environment(factory_name)
    factory_pub = factory_node.get_public_key_by_name(factory_name)

    # Now Pacific_Logistics is the owner and sender
    tx5 = Transaction(
        logistics_pub,
        factory_pub,
        ship_lithium,
        ActionType.RECEIVED,
        "TechFoundry Warehouse",
    )
    tx6 = Transaction(
        logistics_pub,
        factory_pub,
        ship_titanium,
        ActionType.RECEIVED,
        "TechFoundry Warehouse",
    )

    simulate_block_mining(logistics_name, [tx5, tx6], "Delivery to Manufacturer")

    # =========================================================================
    # BLOCK 4: MANUFACTURING (TechFoundry_Inc)
    # =========================================================================
    # TechFoundry consumes raw materials (implicitly) and creates a new product

    tx7 = Transaction(
        factory_pub,
        factory_pub,
        ship_phones,
        ActionType.PROCESSED,
        "Assembly Line 1",
        "G-PHONE",
        1000.0,
    )

    simulate_block_mining(factory_name, [tx7], "Manufacturing Smartphones")

    # =========================================================================
    # BLOCK 5: WHOLESALE DISTRIBUTION (TechFoundry -> Mega_Consumer_Goods)
    # =========================================================================
    retailer_name = "Mega_Consumer_Goods"
    retailer_node, _ = get_node_environment(retailer_name)
    retailer_pub = retailer_node.get_public_key_by_name(retailer_name)

    tx8 = Transaction(
        factory_pub, retailer_pub, ship_phones, ActionType.SHIPPED, "Air Freight"
    )

    simulate_block_mining(factory_name, [tx8], "Shipping to Retailer")

    # =========================================================================
    # BLOCK 6: RETAIL STOCKING & SALE (Mega_Consumer_Goods)
    # =========================================================================
    # 1. Receive
    tx9 = Transaction(
        retailer_pub,
        retailer_pub,
        ship_phones,
        ActionType.RECEIVED,
        "MegaStore Central",
    )

    # 2. Sell to End User (Simulated by selling to a 'Customer' name, or self-burn)
    # We will sell a portion (simulated by splitting, or just marking the batch as SOLD)
    customer_name = "Corner_Store"  # Selling to a smaller store
    customer_node, _ = get_node_environment(customer_name)
    customer_pub = customer_node.get_public_key_by_name(customer_name)

    tx10 = Transaction(
        retailer_pub, customer_pub, ship_phones, ActionType.SOLD, "Checkout Counter"
    )

    simulate_block_mining(retailer_name, [tx9, tx10], "Retail Receipt & Sale")

    print_header("SIMULATION COMPLETE")
    print("Verification: Run 'python view_blockchain.py' inside any node folder.")
    print("Example: cd nodes/Mega_Consumer_Goods && python view_blockchain.py")


if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        print("\nSimulation aborted.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
