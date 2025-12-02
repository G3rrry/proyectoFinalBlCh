import os
import time
import requests
import json
import random
from ecdsa import SigningKey, SECP256k1
from blockchain_core import Transaction, ActionType

# --- Network Configuration ---
PEERS = {
    "Truck_Fleet_Alpha": 5001,
    "TechFoundry_Inc": 5002,
    "Pacific_Logistics": 5003,
    "OPEC_Supplier": 5004,
    "Mega_Consumer_Goods": 5005,
    "GlobalMining_Corp": 5006,
    "FreightTrain_Express": 5007,
    "Drone_Delivery_X": 5008,
    "Corner_Store": 5009,
    "CleanWater_Services": 5010,
    "CargoShip_EverGiven": 5011,
}


def get_keys(node_name):
    """Loads private key from disk and derives public key."""
    key_path = os.path.join("nodes", node_name, "private_key.pem")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Key for {node_name} not found.")

    with open(key_path, "r") as f:
        priv_hex = f.read().strip()

    sk = SigningKey.from_string(bytes.fromhex(priv_hex), curve=SECP256k1)
    vk = sk.verifying_key
    return priv_hex, vk.to_string().hex()


def execute_step(step_num, sender_name, tx_data, title, narrative):
    print(f"\n{'=' * 80}")
    print(f"STEP {step_num}/10: {title.upper()}")
    print(f"{'-' * 80}")
    print(f"STORY: {narrative}")

    # 1. Prepare Credentials
    port = PEERS[sender_name]
    priv_key, pub_key = get_keys(sender_name)

    # 2. Identify Receiver Public Key (if applicable)
    receiver_pub = pub_key  # Default to self (for Extract/Manufacture/Receive)
    if "receiver_name" in tx_data:
        _, receiver_pub = get_keys(tx_data.pop("receiver_name"))

    # 3. Create Transaction Object
    tx = Transaction(
        sender_public_key=pub_key,
        receiver_public_key=receiver_pub,
        shipment_id=tx_data["shipment_id"],
        action=tx_data["action"],
        location=tx_data["location"],
        good_id=tx_data.get("good_id"),
        quantity=tx_data.get("quantity"),
        metadata=tx_data.get("metadata"),
    )

    # 4. Sign
    tx.sign_transaction(priv_key)

    # 5. Broadcast via HTTP
    payload = tx.to_dict()
    payload["signature"] = tx.signature

    print(f"\nACTION: Sending Transaction to Node '{sender_name}' (Port {port})...")
    try:
        url = f"http://localhost:{port}/transaction"
        resp = requests.post(url, json=payload, timeout=2)
        if resp.status_code == 201:
            print(f"SUCCESS: Transaction Accepted by Network.")
            print(f"Tx Hash: {tx.tx_hash[:16]}...")
            print(f"Payload: {tx.action} -> {tx.shipment_id}")
        else:
            print(f"FAILURE: Node Rejected Tx: {resp.text}")
            return
    except Exception as e:
        print(f"ERROR: Connection Failed: {e}")
        return

    # 6. Wait for Auto-Mining
    print("\nCONSENSUS: Waiting 6 seconds for block mining and propagation...")
    for i in range(6, 0, -1):
        print(f"   {i}...", end="\r")
        time.sleep(1)
    print("   Done! Block should be mined.\n")


def main():
    print("\n" + "#" * 80)
    print("GLOBAL SUPPLY CHAIN SIMULATION: FROM MINE TO MARKET")
    print("#" * 80)

    # Identifiers
    raw_material_id = f"SHIP-LITH-{random.randint(1000, 9999)}"
    finished_good_id = f"SHIP-BATT-{random.randint(1000, 9999)}"

    # --- 1. EXTRACT ---
    execute_step(
        1,
        "GlobalMining_Corp",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.EXTRACTED,
            "location": "Nevada Lithium Basin",
            "good_id": "G-LI",
            "quantity": 500.0,
        },
        "Extraction of Raw Materials",
        "GlobalMining Corp initiates operations in Nevada, extracting 500 Tonnes of raw Lithium ore.",
    )

    # --- 2. SHIP TO MANUFACTURER ---
    execute_step(
        2,
        "GlobalMining_Corp",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.SHIPPED,
            "location": "In Transit (Rail Network B)",
            "receiver_name": "TechFoundry_Inc",
        },
        "Shipment to Factory",
        "The raw ore is loaded onto freight trains bound for TechFoundry's specialized processing plant.",
    )

    # --- 3. RECEIVE AT FACTORY ---
    execute_step(
        3,
        "TechFoundry_Inc",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.RECEIVED,
            "location": "Silicon Valley Processing Hub",
        },
        "Factory Intake",
        "TechFoundry verifies the shipment upon arrival at their loading dock, signing for custody on the blockchain.",
    )

    # --- 4. CONSUME INPUT ---
    execute_step(
        4,
        "TechFoundry_Inc",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.CONSUMED,
            "location": "Smelting Sector 4",
            "metadata": {"process": "Purification", "waste_ratio": "0.05"},
        },
        "Processing Raw Materials",
        "The Lithium Ore is fed into the smelting furnace. It is 'Consumed' from inventory to create the final product.",
    )

    # --- 5. MANUFACTURE OUTPUT ---
    execute_step(
        5,
        "TechFoundry_Inc",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.MANUFACTURED,
            "location": "Assembly Line A",
            "good_id": "G-CHIP",  # Proxy for High Tech Good
            "quantity": 2000.0,
            "metadata": {"source_batch": raw_material_id, "quality_check": "PASS"},
        },
        "Manufacturing Finished Goods",
        "Refined Lithium is used to manufacture 2,000 High-Capacity Battery Cells (G-CHIP). A digital twin is created.",
    )

    # --- 6. SHIP TO LOGISTICS ---
    execute_step(
        6,
        "TechFoundry_Inc",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.SHIPPED,
            "location": "Outbound Freight",
            "receiver_name": "Pacific_Logistics",
        },
        "Handover to Logistics",
        "The finished batteries are palletized and handed over to Pacific Logistics for international distribution.",
    )

    # --- 7. RECEIVE AT PORT ---
    execute_step(
        7,
        "Pacific_Logistics",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.RECEIVED,
            "location": "Port of Los Angeles",
            "metadata": {"customs_status": "CLEARED"},
        },
        "Logistics Hub Check-in",
        "Pacific Logistics scans the crates at the Port of LA. Customs clearance is recorded in the metadata.",
    )

    # --- 8. TRANSFER TO LAST MILE ---
    execute_step(
        8,
        "Pacific_Logistics",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.SHIPPED,
            "location": "Loading Bay 12",
            "receiver_name": "Truck_Fleet_Alpha",
        },
        "Transfer to Truck Fleet",
        "Cargo is moved from the warehouse to Truck Fleet Alpha for last-mile delivery to the retailer.",
    )

    # --- 9. TRUCK TRANSIT ---
    execute_step(
        9,
        "Truck_Fleet_Alpha",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.RECEIVED,
            "location": "Interstate 405 South",
            "metadata": {"driver": "ID-442", "temp_c": "22.5"},
        },
        "Transit Confirmation",
        "Truck Fleet Alpha confirms pickup. IoT sensors record the temperature during transit.",
    )

    # --- 10. FINAL DELIVERY ---
    execute_step(
        10,
        "Truck_Fleet_Alpha",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.SHIPPED,
            "location": "Retail Loading Dock",
            "receiver_name": "Mega_Consumer_Goods",
        },
        "Final Delivery to Retailer",
        "The truck arrives at Mega Consumer Goods. Ownership is transferred to the retailer, completing the cycle.",
    )

    print("\n" + "=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)
    print("To verify the Ledger state, you can run:")
    print("  python view_blockchain.py")
    print("  from inside any node.")
    print("\nYou should see:")
    print(f"  1. A 'CONSUMED' transaction for {raw_material_id}")
    print(f"  2. A 'MANUFACTURED' transaction for {finished_good_id}")
    print(f"  3. Multiple 'SHIPPED/RECEIVED' events tracking the path.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
