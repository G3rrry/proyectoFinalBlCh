import os
import random
import sqlite3
import sys
import time

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


def select_from_menu(items, title, formatter):
    if not items:
        print(f"\n--- {title} ---\n  (No items available)")
        input("Press Enter to go back...")
        return None
    while True:
        print(f"\n--- {title} ---")
        for i, item in enumerate(items, 1):
            print(f"{i}. {formatter(item)}")
        print("b. Back")
        choice = input("\nSelect: ").strip().lower()
        if choice == "b":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            else:
                print("Invalid.")
        except:
            print("Enter a number.")


def main():
    node_name, priv_key = get_identity()
    if not node_name:
        return

    db_path = "blockchain.db"
    node = BlockchainNode(node_name, db_path)
    sender_pub = node.get_public_key_by_name(node_name)

    while True:
        print(f"\n--- {node_name.upper()} WALLET (Mempool Mode) ---")
        print("1. [E]XTRACT / PROCESS")
        print("2. [S]HIP / TRANSFER")
        print("3. [D]ESTROY / CONSUME")
        print("4. [Q]UIT")

        choice = input("Action: ").upper().strip()
        if choice in ["Q", "4"]:
            break

        tx = None
        if choice == "1":
            with sqlite3.connect(db_path) as conn:
                goods = conn.execute(
                    "SELECT good_id, name, unit_of_measure FROM goods"
                ).fetchall()
            sel = select_from_menu(goods, "RESOURCE", lambda x: f"{x[1]} ({x[0]})")
            if not sel:
                continue
            qty = float(input(f"Qty ({sel[2]}): "))
            loc = input("Location: ")
            tx = Transaction(
                sender_pub,
                sender_pub,
                f"SHIP-{random.randint(10000, 99999)}",
                ActionType.EXTRACTED,
                loc,
                sel[0],
                qty,
            )

        elif choice == "2":
            with sqlite3.connect(db_path) as conn:
                ships = conn.execute(
                    "SELECT shipment_id, g.name FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=?",
                    (sender_pub,),
                ).fetchall()
            sel = select_from_menu(ships, "SHIPMENT", lambda x: f"{x[0]} ({x[1]})")
            if not sel:
                continue

            with sqlite3.connect(db_path) as conn:
                partners = conn.execute(
                    "SELECT name, role FROM participants WHERE name != ?", (node_name,)
                ).fetchall()
            rec = select_from_menu(partners, "RECEIVER", lambda x: f"{x[0]} ({x[1]})")
            if not rec:
                continue

            rec_pub = node.get_public_key_by_name(rec[0])
            loc = input("New Location: ")
            tx = Transaction(sender_pub, rec_pub, sel[0], ActionType.SHIPPED, loc)

        elif choice == "3":
            with sqlite3.connect(db_path) as conn:
                ships = conn.execute(
                    "SELECT shipment_id, g.name FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=?",
                    (sender_pub,),
                ).fetchall()
            sel = select_from_menu(ships, "DESTROY", lambda x: f"{x[0]} ({x[1]})")
            if not sel:
                continue
            reason = input("Reason: ")
            tx = Transaction(
                sender_pub,
                sender_pub,
                sel[0],
                ActionType.DESTROYED,
                "Destroyed",
                metadata={"reason": reason},
            )

        if tx:
            if tx.sign_transaction(priv_key):
                # BROADCAST TO MEMPOOL
                print("Transaction signed. Broadcasting to network mempool...")
                # Add to own mempool first
                node.add_to_mempool(tx)
                # Broadcast to others
                p2p.broadcast_transaction(node_name, tx)
                input("Sent to Mempool. Wait for a validator to mine it.")
            else:
                print("Sign failed.")


if __name__ == "__main__":
    main()
