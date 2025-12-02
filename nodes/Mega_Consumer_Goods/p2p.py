import sys
import os
import json
import requests
import argparse
import threading
import time
from flask import Flask, jsonify, request
from blockchain_core import BlockchainNode, Block, Transaction, ActionType

# --- Configuration ---
app = Flask(__name__)
NODE_NAME = os.path.basename(os.getcwd())  # Use folder name as Identity
DB_PATH = "blockchain.db"

# Initialize Node
node = BlockchainNode(NODE_NAME, DB_PATH)

# Known peers - COMPLETE LIST
PEERS = {
    "Truck_Fleet_Alpha": "http://localhost:5001",
    "TechFoundry_Inc": "http://localhost:5002",
    "Pacific_Logistics": "http://localhost:5003",
    "OPEC_Supplier": "http://localhost:5004",
    "Mega_Consumer_Goods": "http://localhost:5005",
    "GlobalMining_Corp": "http://localhost:5006",
    "FreightTrain_Express": "http://localhost:5007",
    "Drone_Delivery_X": "http://localhost:5008",
    "Corner_Store": "http://localhost:5009",
    "CleanWater_Services": "http://localhost:5010",
    "CargoShip_EverGiven": "http://localhost:5011",
}

# Determine My Port
MY_PORT = 5000  # Default fallback
if NODE_NAME in PEERS:
    MY_PORT = int(PEERS[NODE_NAME].split(":")[-1])


# --- Auto-Miner Thread ---
def auto_mine_loop():
    """Checks periodically if this node is the validator and mines if needed."""
    print(f"[*] Auto-Miner started for {NODE_NAME}")

    while True:
        time.sleep(5)  # Wait 5 seconds between checks (Block Time)

        try:
            # 1. Get Current Network State
            last_block = node.get_last_block()
            if not last_block:
                continue

            prev_hash = last_block.hash
            height = last_block.index

            # 2. Am I the Validator?
            expected_validator = node.select_validator(prev_hash)

            if expected_validator == NODE_NAME:
                # 3. Check Mempool
                mempool = node.get_mempool_transactions()
                if mempool:
                    print(f"\n   [⛏] It is my turn! Mining {len(mempool)} txs...")

                    # 4. Filter Valid Transactions
                    valid_txs = []
                    for tx in mempool:
                        is_valid_logic, _ = node.validate_smart_contract_rules(tx)
                        if is_valid_logic and tx.is_valid():
                            valid_txs.append(tx)

                    if valid_txs:
                        # 5. Mine Block
                        new_index = height + 1
                        new_block = Block(new_index, valid_txs, prev_hash, NODE_NAME)

                        # 6. Save Locally
                        success, msg = node.receive_block(new_block)
                        if success:
                            print(
                                f"   [+] Mined Block #{new_index} ({new_block.hash[:8]}). Broadcasting..."
                            )
                            # 7. Broadcast to Peers
                            broadcast_block(new_block)
                        else:
                            print(f"   [!] Self-validation failed: {msg}")
        except Exception as e:
            print(f"   [!] Miner Error: {e}")


# --- API Endpoints ---


@app.route("/info", methods=["GET"])
def get_info():
    last_block = node.get_last_block()
    return jsonify(
        {
            "node_name": NODE_NAME,
            "height": last_block.index if last_block else 0,
            "last_hash": last_block.hash if last_block else "0" * 64,
        }
    )


@app.route("/chain", methods=["GET"])
def get_chain():
    chain_data = []
    last = node.get_last_block()
    height = last.index if last else 0
    for i in range(1, height + 1):
        blk = node.get_block_by_index(i)
        if blk:
            chain_data.append(json.loads(blk.to_json()))
    return jsonify(chain_data)


@app.route("/transaction", methods=["POST"])
def receive_transaction():
    data = request.get_json()
    try:
        tx = Transaction(
            data["sender"],
            data["receiver"],
            data["shipment_id"],
            ActionType(data["action"]),
            data["location"],
            data.get("good_id"),
            data.get("quantity"),
            data.get("metadata"),
            data.get("timestamp"),
            data.get("signature"),
        )

        # Try to add to local mempool
        success, msg = node.add_to_mempool(tx)

        if success:
            print(f"[*] Received Tx {tx.tx_hash[:8]} (New) - Relaying to network...")
            # GOSSIP: Relay to others
            threading.Thread(target=broadcast_transaction, args=(tx,)).start()
            return jsonify({"message": "Transaction added and relayed"}), 201

        elif msg == "Duplicate":
            return jsonify({"message": "Transaction already known"}), 200

        return jsonify({"message": f"Invalid Tx: {msg}"}), 400
    except Exception as e:
        return jsonify({"message": str(e)}), 400


@app.route("/block", methods=["POST"])
def receive_block():
    data = request.get_json()
    try:
        block = Block.from_json(json.dumps(data))
        print(f"[*] Received Block #{block.index} from {block.validator}")

        # 1. Attempt to add to local chain
        success, msg = node.receive_block(block)

        if success:
            print(f"    [+] Block Accepted. New Height: {block.index}")

            # 2. GOSSIP: If it's valid and new, broadcast it!
            threading.Thread(target=broadcast_block, args=(block,)).start()

            return jsonify({"message": "Block accepted"}), 201
        else:
            print(f"    [-] Block Rejected: {msg}")
            # If rejected because of a gap, trigger sync
            if "Gap detected" in msg or "Invalid Index" in msg:
                threading.Thread(target=synchronize_chain).start()
            return jsonify({"message": f"Block rejected: {msg}"}), 409
    except Exception as e:
        print(f"Error processing block: {e}")
        return jsonify({"message": str(e)}), 400


# --- P2P Actions ---


def broadcast_transaction(tx):
    tx_data = tx.to_dict()
    tx_data["signature"] = tx.signature
    for name, url in PEERS.items():
        if name == NODE_NAME:
            continue
        try:
            requests.post(f"{url}/transaction", json=tx_data, timeout=1)
        except:
            pass


def broadcast_block(block):
    block_json = json.loads(block.to_json())
    for name, url in PEERS.items():
        if name == NODE_NAME:
            continue
        try:
            requests.post(f"{url}/block", json=block_json, timeout=1)
        except Exception as e:
            print(f"    [!] Failed to reach {name}")


def synchronize_chain():
    print("[*] Starting Synchronization...")
    best_height = 0
    best_peer = None

    # 1. Find peer with longest chain
    for name, url in PEERS.items():
        if name == NODE_NAME:
            continue
        try:
            resp = requests.get(f"{url}/info", timeout=1)
            if resp.status_code == 200:
                info = resp.json()
                if info["height"] > best_height:
                    best_height = info["height"]
                    best_peer = url
        except:
            pass

    my_height = node.get_last_block().index if node.get_last_block() else 0

    if best_height > my_height:
        print(f"[*] Found longer chain ({best_height}) at {best_peer}. Downloading...")
        try:
            resp = requests.get(f"{best_peer}/chain")
            if resp.status_code == 200:
                chain_dump = resp.json()
                for blk_data in chain_dump:
                    blk = Block.from_json(json.dumps(blk_data))
                    if blk.index > my_height:
                        success, msg = node.receive_block(blk)
                        if success:
                            print(f"    Synced Block #{blk.index}")
                        else:
                            print(f"    Sync Error at #{blk.index}: {msg}")
                            break
        except Exception as e:
            print(f"Sync failed: {e}")
    else:
        print("[*] Chain is up to date.")


# --- Bootstrapping ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="Port to run on")
    args = parser.parse_args()

    if args.port:
        MY_PORT = args.port

    # Initial Sync
    threading.Thread(target=synchronize_chain).start()

    # Start Auto-Miner Thread
    threading.Thread(target=auto_mine_loop, daemon=True).start()

    print(f"\n=== NODE {NODE_NAME} RUNNING ON PORT {MY_PORT} ===")
    app.run(host="0.0.0.0", port=MY_PORT)
