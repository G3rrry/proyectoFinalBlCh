import os
import time
from initialize import BlockchainNode, Transaction, Block, ActionType


def load_key(name):
    """Helper to load private key from the initial_participants folder."""
    path = os.path.join("initial_participants", f"{name}.pem")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Key for {name} not found. Did you run initialize.py?")
    with open(path, "r") as f:
        return f.read().strip()


def run_simulation():
    node = BlockchainNode()
    print("--- STARTING SUPPLY CHAIN SIMULATION (10 TRANSACTIONS) ---\n")

    # Load existing chain state to determine next index
    chain = node.load_chain()
    next_index = chain[-1].index + 1 if chain else 1
    prev_hash = chain[-1].hash if chain else "0" * 64

    # --- BATCH 1: RAW MATERIALS LOGISTICS ---
    # Scenario: GlobalMining extracts Titanium, puts it on a Train, which delivers to TechFoundry.
    print(f"Preparing Block {next_index} (Raw Materials)...")

    txs_batch_1 = []

    # 1. Extraction (New Shipment)
    # GlobalMining -> GlobalMining
    sender = "GlobalMining_Corp"
    receiver = "GlobalMining_Corp"
    shipment_id = "SHIP-SIM-01"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx1 = Transaction(
        s_pub, r_pub, shipment_id, ActionType.EXTRACTED, "Nevada Mine", "G-TI", 1000.0
    )
    tx1.sign_transaction(priv_key)
    txs_batch_1.append(tx1)
    print(f"  [1/10] EXTRACTED: 1000kg Titanium created by {sender}")

    # 2. Shipping (Move to Transport)
    # GlobalMining -> FreightTrain_Express
    sender = "GlobalMining_Corp"
    receiver = "FreightTrain_Express"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx2 = Transaction(s_pub, r_pub, shipment_id, ActionType.SHIPPED, "Loading Dock A")
    tx2.sign_transaction(priv_key)
    txs_batch_1.append(tx2)
    print(f"  [2/10] SHIPPED: Titanium loaded onto {receiver}")

    # 3. Delivery (Move to Factory)
    # FreightTrain_Express -> TechFoundry_Inc
    sender = "FreightTrain_Express"
    receiver = "TechFoundry_Inc"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx3 = Transaction(
        s_pub, r_pub, shipment_id, ActionType.RECEIVED, "TechFoundry Warehouse"
    )
    tx3.sign_transaction(priv_key)
    txs_batch_1.append(tx3)
    print(f"  [3/10] RECEIVED: Titanium arrived at {receiver}")

    # MINT BLOCK 1
    block1 = Block(next_index, txs_batch_1, prev_hash, "Pending_Validator")
    node.save_block(block1)
    prev_hash = block1.hash
    next_index += 1
    print("  >> Block MINTED successfully.\n")

    # --- BATCH 2: MANUFACTURING & DISTRIBUTION ---
    # Scenario: TechFoundry turns Titanium into Laptops, ships via Drone to Retailer.
    print(f"Preparing Block {next_index} (Manufacturing)...")
    txs_batch_2 = []

    # 4. Processing (New Product Created)
    # TechFoundry -> TechFoundry (New Shipment ID for the Laptops)
    sender = "TechFoundry_Inc"
    receiver = "TechFoundry_Inc"
    shipment_id_goods = "SHIP-SIM-02"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx4 = Transaction(
        s_pub,
        r_pub,
        shipment_id_goods,
        ActionType.PROCESSED,
        "Assembly Line 4",
        "G-CHIP",
        5000.0,
    )
    tx4.sign_transaction(priv_key)
    txs_batch_2.append(tx4)
    print(f"  [4/10] PROCESSED: 5000 Microchips created by {sender}")

    # 5. Handover to Logistics
    # TechFoundry -> Drone_Delivery_X
    sender = "TechFoundry_Inc"
    receiver = "Drone_Delivery_X"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx5 = Transaction(
        s_pub, r_pub, shipment_id_goods, ActionType.SHIPPED, "Airspace Sector 9"
    )
    tx5.sign_transaction(priv_key)
    txs_batch_2.append(tx5)
    print(f"  [5/10] SHIPPED: Chips loaded onto {receiver}")

    # 6. Delivery to Retailer
    # Drone_Delivery_X -> Mega_Consumer_Goods
    sender = "Drone_Delivery_X"
    receiver = "Mega_Consumer_Goods"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx6 = Transaction(
        s_pub, r_pub, shipment_id_goods, ActionType.RECEIVED, "MegaStore Central Depot"
    )
    tx6.sign_transaction(priv_key)
    txs_batch_2.append(tx6)
    print(f"  [6/10] RECEIVED: Chips delivered to {receiver}")

    # MINT BLOCK 2
    block2 = Block(next_index, txs_batch_2, prev_hash, "Pending_Validator")
    node.save_block(block2)
    prev_hash = block2.hash
    next_index += 1
    print("  >> Block MINTED successfully.\n")

    # --- BATCH 3: RETAIL & UTILITIES ---
    # Scenario: Retailer sells to local store. Separately, Water is extracted and moved.
    print(f"Preparing Block {next_index} (Retail & Utility)...")
    txs_batch_3 = []

    # 7. Sale
    # Mega_Consumer_Goods -> Corner_Store
    sender = "Mega_Consumer_Goods"
    receiver = "Corner_Store"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx7 = Transaction(
        s_pub, r_pub, shipment_id_goods, ActionType.SOLD, "City Center Branch"
    )
    tx7.sign_transaction(priv_key)
    txs_batch_3.append(tx7)
    print(f"  [7/10] SOLD: Chips sold to {receiver}")

    # 8. Utility Extraction
    # CleanWater -> CleanWater
    sender = "CleanWater_Services"
    receiver = "CleanWater_Services"
    shipment_id_water = "SHIP-SIM-03"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx8 = Transaction(
        s_pub,
        r_pub,
        shipment_id_water,
        ActionType.EXTRACTED,
        "Dam Reserve",
        "G-H2O",
        10000.0,
    )
    tx8.sign_transaction(priv_key)
    txs_batch_3.append(tx8)
    print(f"  [8/10] EXTRACTED: 10,000L Water by {sender}")

    # 9. Transport
    # CleanWater -> Truck_Fleet_Alpha
    sender = "CleanWater_Services"
    receiver = "Truck_Fleet_Alpha"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx9 = Transaction(
        s_pub, r_pub, shipment_id_water, ActionType.SHIPPED, "Highway 101"
    )
    tx9.sign_transaction(priv_key)
    txs_batch_3.append(tx9)
    print(f"  [9/10] SHIPPED: Water loaded onto {receiver}")

    # 10. Final Delivery
    # Truck_Fleet_Alpha -> Corner_Store
    sender = "Truck_Fleet_Alpha"
    receiver = "Corner_Store"

    s_pub = node.get_public_key_by_name(sender)
    r_pub = node.get_public_key_by_name(receiver)
    priv_key = load_key(sender)

    tx10 = Transaction(
        s_pub, r_pub, shipment_id_water, ActionType.RECEIVED, "Corner Store Backroom"
    )
    tx10.sign_transaction(priv_key)
    txs_batch_3.append(tx10)
    print(f"  [10/10] RECEIVED: Water delivered to {receiver}")

    # MINT BLOCK 3
    block3 = Block(next_index, txs_batch_3, prev_hash, "Pending_Validator")
    node.save_block(block3)
    print("  >> Block MINTED successfully.\n")

    print("--- SIMULATION COMPLETE ---")
    print("Run 'view_blockchain.py' to see the final ledger and world state.")


if __name__ == "__main__":
    try:
        run_simulation()
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
