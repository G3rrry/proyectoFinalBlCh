import os
import random
import sqlite3
from initialize import BlockchainNode, Transaction, Block, ActionType


def load_private_key(filename):
    paths_to_check = [filename, os.path.join("initial_participants", filename)]
    for path in paths_to_check:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    return None


def get_transaction_input(node: BlockchainNode):
    print("\n--- NEW SUPPLY CHAIN TRANSACTION ---")

    # 1. SENDER
    sender_name = input("Who is initiating this? (Sender Name): ").strip()
    sender_pub = node.get_public_key_by_name(sender_name)
    if not sender_pub:
        print("Unknown participant.")
        return None

    key_file = input(f"Private Key File for {sender_name}: ").strip()
    priv_key = load_private_key(key_file)
    if not priv_key:
        print("Key file not found.")
        return None

    # 2. ACTION SELECTION
    print("\n--- SELECT ACTION ---")
    print("1. [E]XTRACT / PROCESS (Creates a NEW Shipment)")
    print("2. [S]HIP / TRANSFER   (Moves an EXISTING Shipment)")
    choice = input("Choice (1/2): ").strip()

    if choice == "1":
        action = ActionType.EXTRACTED
        print("\nAvailable Goods:")
        conn = sqlite3.connect(node.db_file)
        goods = conn.execute(
            "SELECT good_id, name, unit_of_measure FROM goods"
        ).fetchall()
        conn.close()
        for g in goods:
            print(f" - ID: {g[0]} | {g[1]} ({g[2]})")

        good_id = input("Enter Good ID from list: ").strip()
        quantity = float(input("Enter Quantity: ").strip())

        shipment_id = f"SHIP-{random.randint(2000, 9999)}"
        print(f"Generating New Shipment ID: {shipment_id}")

        receiver_name = (
            input(f"Who currently holds this? (Default: {sender_name}): ").strip()
            or sender_name
        )

    else:
        action = ActionType.SHIPPED
        shipment_id = input("Enter Shipment ID to move (e.g., SHIP-1001): ").strip()

        ship_data = node.get_shipment(shipment_id)
        if not ship_data:
            print("Shipment ID not found.")
            return None

        current_owner_pk = ship_data[3]
        if current_owner_pk != sender_pub:
            print("SECURITY ALERT: You do not own this shipment!")
            return None

        receiver_name = input("Receiver Name (e.g., CargoShip_EverGiven): ").strip()
        good_id = None
        quantity = None

    # 3. RECEIVER VALIDATION
    receiver_pub = node.get_public_key_by_name(receiver_name)
    if not receiver_pub:
        print(f"Receiver '{receiver_name}' not found.")
        return None

    location = input("Current Location: ").strip()

    tx = Transaction(
        sender_pub, receiver_pub, shipment_id, action, location, good_id, quantity
    )

    print("Signing...")
    if tx.sign_transaction(priv_key):
        return tx
    else:
        print("Signing failed.")
        return None


if __name__ == "__main__":
    node = BlockchainNode()
    chain = node.load_chain()

    if chain:
        new_index = chain[-1].index + 1
        prev_hash = chain[-1].hash
    else:
        new_index = 1
        prev_hash = "0" * 64

    pool = []
    while True:
        tx = get_transaction_input(node)
        if tx and tx.is_valid():
            pool.append(tx)
            print("Added to Pool.")

        if input("\nAdd another? (y/n): ").lower() != "y":
            break

    if pool:
        new_block = Block(new_index, pool, prev_hash, "Pending")
        node.save_block(new_block)
