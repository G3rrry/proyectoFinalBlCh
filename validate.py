import os
import sys
import requests
import time
import json  # <--- THIS WAS MISSING
from blockchain_core import BlockchainNode, Block

# Configuration
NODE_NAME = os.path.basename(os.getcwd())

# Map of Node Names to Ports (Must match p2p.py)
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

MY_PORT = PEERS.get(NODE_NAME, 5000)
BASE_URL = f"http://localhost:{MY_PORT}"


def main():
    print(f"\n--- {NODE_NAME.upper()} VALIDATOR DASHBOARD ---")

    # 1. Get Info from Local Node Server
    try:
        resp = requests.get(f"{BASE_URL}/info", timeout=2)
        info = resp.json()
    except requests.exceptions.ConnectionError:
        print(f"[!] Error: Node server is not running at {BASE_URL}")
        print(f"    Please ensure 'p2p.py' is running for this node.")
        return

    print(f"Current Height: {info['height']}")

    # 2. Check Logic (Read-Only DB Access)
    node = BlockchainNode(NODE_NAME, "blockchain.db")
    last_block = node.get_last_block()
    prev_hash = last_block.hash if last_block else "0" * 64

    # Check if it's our turn
    expected_validator = node.select_validator(prev_hash)
    print(f"Expected Validator: {expected_validator}")

    if expected_validator != NODE_NAME:
        print("\n[!] You are NOT the current validator.")
        print(f"    Waiting for {expected_validator}...")
        return

    print("\n[+] You ARE the elected validator!")

    # 3. Mine
    mempool = node.get_mempool_transactions()
    if not mempool:
        print("    Mempool is empty. Nothing to mine.")
        return

    print(f"    Found {len(mempool)} transactions.")
    valid_txs = []
    for tx in mempool:
        is_valid, msg = node.validate_smart_contract_rules(tx)
        if is_valid and tx.is_valid():
            valid_txs.append(tx)
        else:
            print(f"    Skipping invalid tx: {tx.tx_hash[:8]} ({msg})")

    if not valid_txs:
        print("    No valid transactions to package.")
        return

    new_index = (last_block.index + 1) if last_block else 1
    new_block = Block(new_index, valid_txs, prev_hash, NODE_NAME)

    print(f"\n[+] Minting Block #{new_index}...")

    # 4. Submit Block to Local Server
    try:
        # This line failed before because json wasn't imported
        block_payload = json.loads(new_block.to_json())

        r = requests.post(f"{BASE_URL}/block", json=block_payload)
        if r.status_code == 201:
            print(f"Success! Block #{new_index} mined and broadcasted.")
        else:
            print(f"Error submitting block: {r.text}")
    except Exception as e:
        print(f"    Communication error: {e}")


if __name__ == "__main__":
    main()
