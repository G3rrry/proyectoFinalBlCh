import os
import random
import sqlite3
import sys
import time

# Ensure local modules can be imported
sys.path.append(os.getcwd())

from initialize import BlockchainNode, Transaction, Block, ActionType
import p2p


def get_identity():
    current_dir = os.getcwd()
    node_name = os.path.basename(current_dir)
    key_path = "private_key.pem"

    if not os.path.exists(key_path):
        return None, None

    with open(key_path, "r") as f:
        private_key = f.read().strip()

    return node_name, private_key


def list_my_shipments(node, my_pub_key):
    """Fetch and display shipments owned by this node."""
    conn = sqlite3.connect("blockchain.db")
    cursor = conn.cursor()
    query = """
        SELECT s.shipment_id, g.name, s.quantity, g.unit_of_measure, s.current_location 
        FROM shipments s 
        JOIN goods g ON s.good_id = g.good_id 
        WHERE s.current_owner_pk = ?
    """
    rows = cursor.execute(query, (my_pub_key,)).fetchall()
    conn.close()
    return rows


def list_receivers(node, my_name):
    """Fetch and display other participants."""
    conn = sqlite3.connect("blockchain.db")
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT name, role FROM participants WHERE name != ?", (my_name,)
    ).fetchall()
    conn.close()
    return rows


def main():
    node_name, priv_key = get_identity()

    if not node_name:
        print("ERROR: Could not detect Node identity.")
        print(
            "Run this script FROM INSIDE a node directory (e.g., nodes/GlobalMining_Corp/)"
        )
        return

    node = BlockchainNode(node_name, "blockchain.db")
    sender_pub = node.get_public_key_by_name(node_name)

    while True:
        print(f"\n" + "=" * 40)
        print(f"--- {node_name.upper()} TERMINAL ---")
        print("=" * 40)
        print("1. [E]XTRACT / PROCESS (Create New Shipment)")
        print("2. [S]HIP / TRANSFER   (Move Existing Shipment)")
        print("3. [Q]UIT")

        choice = input("\nSelect Action: ").strip().upper()

        if choice in ["Q", "QUIT", "3"]:
            print("Exiting...")
            break

        tx = None

        # --- OPTION 1: EXTRACT ---
        if choice in ["1", "E"]:
            print("\n--- NEW SHIPMENT CREATION ---")

            with sqlite3.connect("blockchain.db") as conn:
                goods = conn.execute(
                    "SELECT good_id, name, unit_of_measure FROM goods"
                ).fetchall()

            print(f"{'ID':<10} | {'Name':<20} | {'Unit':<10}")
            print("-" * 45)
            for g in goods:
                print(f"{g[0]:<10} | {g[1]:<20} | {g[2]:<10}")

            while True:
                good_id = input("\nEnter Good ID (or 'b' to back): ").strip()
                if good_id.lower() == "b":
                    break

                # Validate Good ID
                if not any(g[0] == good_id for g in goods):
                    print("Invalid Good ID. Please try again.")
                    continue

                try:
                    qty = float(input("Quantity: ").strip())
                    if qty <= 0:
                        raise ValueError
                except ValueError:
                    print("Quantity must be a positive number.")
                    continue

                loc = input("Location (e.g., Warehouse A): ").strip()
                if not loc:
                    print("Location is required.")
                    continue

                ship_id = f"SHIP-{random.randint(10000, 99999)}"
                tx = Transaction(
                    sender_pub,
                    sender_pub,
                    ship_id,
                    ActionType.EXTRACTED,
                    loc,
                    good_id,
                    qty,
                )
                break

        # --- OPTION 2: SHIP ---
        elif choice in ["2", "S"]:
            print("\n--- TRANSFER SHIPMENT ---")

            my_shipments = list_my_shipments(node, sender_pub)

            if not my_shipments:
                print(">> You have no shipments available to move.")
                print(">> Try Extracting/Processing (Option 1) first.")
                input("Press Enter to continue...")
                continue

            print(
                f"{'Shipment ID':<15} | {'Content':<20} | {'Qty':<15} | {'Location':<20}"
            )
            print("-" * 75)
            for s in my_shipments:
                qty_str = f"{s[2]} {s[3]}"
                print(f"{s[0]:<15} | {s[1]:<20} | {qty_str:<15} | {s[4]:<20}")

            while True:
                ship_id = input(
                    "\nEnter Shipment ID to move (or 'b' to back): "
                ).strip()
                if ship_id.lower() == "b":
                    break

                # Verify ownership and existence
                target_shipment = next(
                    (s for s in my_shipments if s[0] == ship_id), None
                )
                if not target_shipment:
                    print("Invalid ID or you do not own this shipment. Try again.")
                    continue

                # Select Receiver
                receivers = list_receivers(node, node_name)
                print("\nAvailable Partners:")
                for r in receivers:
                    print(f" - {r[0]} ({r[1]})")

                rec_name = input("Receiver Name: ").strip()
                rec_pub = node.get_public_key_by_name(rec_name)

                if not rec_pub:
                    print(f"Participant '{rec_name}' not found. Check spelling.")
                    continue

                loc = input("New Location: ").strip()
                if not loc:
                    print("Location is required.")
                    continue

                tx = Transaction(sender_pub, rec_pub, ship_id, ActionType.SHIPPED, loc)
                break

        else:
            print("Invalid selection.")
            continue

        # --- EXECUTION PHASE ---
        if tx:
            print(f"\nProcessing Transaction: {tx.action} {tx.shipment_id}...")
            if tx.sign_transaction(priv_key):
                print("Signature Verified.")

                last_block = node.get_last_block()
                prev_hash = last_block.hash if last_block else "0" * 64
                new_index = (last_block.index + 1) if last_block else 1

                block = Block(new_index, [tx], prev_hash, node_name)

                # Save locally
                node.save_block_to_db(block)
                print("Block mined and committed to LOCAL ledger.")

                # Broadcast
                print("Broadcasting to network...")
                p2p.broadcast_block(node_name, block)

                input("\nSuccess! Press Enter to return to menu...")
            else:
                print("Error: Signing failed. Check your private keys.")
                time.sleep(2)


if __name__ == "__main__":
    main()
