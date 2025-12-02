import os
import random
import sqlite3
import sys
import time
import requests  # Added for HTTP P2P

sys.path.append(os.getcwd())
# We removed 'import p2p' because we now communicate via HTTP
from blockchain_core import BlockchainNode, Transaction, ActionType

# --- Configuration for Real Network ---
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


def get_identity():
    current_dir = os.getcwd()
    node_name = os.path.basename(current_dir)
    key_path = "private_key.pem"
    if not os.path.exists(key_path):
        return None, None
    with open(key_path, "r") as f:
        private_key = f.read().strip()
    return node_name, private_key


def get_node_port(node_name):
    return PEERS.get(node_name, 5000)


def select_from_menu(items, title, formatter):
    if not items:
        print(f"\n--- {title} ---\n  (No items available)")
        input("Press Enter to go back...")
        return None
    while True:
        print(f"\n--- {title} ---")
        for i, item in enumerate(items, 1):
            print(f"{i}. {formatter(item)}")
        print("B. Back")
        choice = input("\nSelect: ").strip().lower()
        if choice == "b":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")


def main():
    node_name, priv_key = get_identity()
    if not node_name:
        print("Error: Could not find private_key.pem or node identity.")
        return

    # Connection to Local P2P Node
    my_port = get_node_port(node_name)
    base_url = f"http://localhost:{my_port}"

    db_path = "blockchain.db"
    # We initialize Node in Read-Only mode just for querying data
    node = BlockchainNode(node_name, db_path)
    sender_pub = node.get_public_key_by_name(node_name)

    if not sender_pub:
        print(f"Error: Public Key for {node_name} not found in DB.")
        return

    while True:
        print(f"\n{'=' * 40}")
        print(f" {node_name.upper()} WALLET (Port {my_port})")
        print(f"{'=' * 40}")
        print("1. Extract Resource   (E)")
        print("2. Manufacture Goods  (M)")
        print("3. Ship Goods         (S)")
        print("4. Destroy Goods      (D)")
        print("5. Vote for Delegate  (V)")
        print("6. Quit               (Q)")
        print(f"{'-' * 40}")

        choice = input("Select Action: ").upper().strip()

        if choice in ["6", "Q"]:
            print("Exiting...")
            break

        txs = []  # Batch list

        # --- 1. EXTRACT ---
        if choice in ["1", "E"]:
            with sqlite3.connect(db_path) as conn:
                goods = conn.execute(
                    "SELECT good_id, name, unit_of_measure FROM goods"
                ).fetchall()

            print("\n[ Extract New Resources ]")
            sel = select_from_menu(
                goods, "Select Resource Type", lambda x: f"{x[1]} ({x[0]})"
            )
            if sel:
                try:
                    qty = float(input(f"Quantity ({sel[2]}): "))
                    loc = input("Current Location: ")

                    new_ship_id = f"SHIP-{random.randint(10000, 99999)}"
                    txs.append(
                        Transaction(
                            sender_pub,
                            sender_pub,
                            new_ship_id,
                            ActionType.EXTRACTED,
                            loc,
                            sel[0],
                            qty,
                        )
                    )
                    print(f"   -> Queued: Extract {qty} {sel[1]}")
                except ValueError:
                    print("Invalid quantity.")

        # --- 2. MANUFACTURE (Consume Inputs -> Create Output) ---
        elif choice in ["2", "M"]:
            print("\n[ Manufacture Goods ]")

            # Step A: Inputs
            print("--- Step 1: Select Input Materials ---")
            processing_inputs = []

            while True:
                with sqlite3.connect(db_path) as conn:
                    selected_ids = [i["id"] for i in processing_inputs]
                    # Only select active shipments (is_active=1)
                    query = "SELECT shipment_id, g.name, s.quantity, g.unit_of_measure, g.good_id FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=? AND s.is_active=1"
                    if selected_ids:
                        placeholders = ",".join("?" for _ in selected_ids)
                        query += f" AND s.shipment_id NOT IN ({placeholders})"
                        params = (sender_pub, *selected_ids)
                    else:
                        params = (sender_pub,)

                    ships = conn.execute(query, params).fetchall()

                if not ships:
                    if not processing_inputs:
                        print("  (No active inventory available)")
                        break
                    print("  (No more items available)")
                    break

                sel = select_from_menu(
                    ships,
                    "Your Inventory",
                    lambda x: f"{x[0]} - {x[1]} ({x[2]} {x[3]})",
                )
                if not sel:
                    break

                current_qty = sel[2]
                try:
                    use_qty = float(input(f"Quantity to use (Max {current_qty}): "))
                    if use_qty <= 0 or use_qty > current_qty:
                        print(f"Error: You have {current_qty} but entered {use_qty}.")
                        continue

                    processing_inputs.append(
                        {
                            "id": sel[0],
                            "name": sel[1],
                            "total": current_qty,
                            "used": use_qty,
                            "good_id": sel[4],
                            "unit": sel[3],
                        }
                    )
                    print(f"   -> Added {use_qty} of {sel[1]} to inputs.")

                    if input("Add another input? (Y/n): ").lower() == "n":
                        break
                except ValueError:
                    print("Invalid number.")
                    continue

            if not processing_inputs:
                continue

            # Step B: Output & Location
            print("\n--- Step 2: Define Output ---")
            with sqlite3.connect(db_path) as conn:
                goods = conn.execute(
                    "SELECT good_id, name, unit_of_measure FROM goods"
                ).fetchall()

            out_sel = select_from_menu(
                goods, "Select Output Product", lambda x: f"{x[1]} ({x[0]})"
            )
            if not out_sel:
                continue

            try:
                out_qty = float(input(f"Quantity Produced ({out_sel[2]}): "))
                prod_loc = input("Production Location (applied to inputs & output): ")

                input_ids = []
                # 1. Update Inputs
                for item in processing_inputs:
                    input_ids.append(item["id"])
                    remaining = item["total"] - item["used"]

                    if remaining == 0:
                        # Fully consumed -> CONSUMED (New Action Type)
                        txs.append(
                            Transaction(
                                sender_pub,
                                sender_pub,
                                item["id"],
                                ActionType.CONSUMED,
                                "Consumed in Manufacturing",
                                metadata={"product": out_sel[1]},
                            )
                        )
                    else:
                        # Partially consumed -> RECEIVED at new location with new quantity
                        txs.append(
                            Transaction(
                                sender_pub,
                                sender_pub,
                                item["id"],
                                ActionType.RECEIVED,
                                prod_loc,
                                item["good_id"],
                                remaining,
                            )
                        )

                # 2. Create Output -> MANUFACTURED with Metadata
                new_product_id = f"SHIP-{random.randint(10000, 99999)}"
                txs.append(
                    Transaction(
                        sender_pub,
                        sender_pub,
                        new_product_id,
                        ActionType.MANUFACTURED,
                        prod_loc,
                        out_sel[0],
                        out_qty,
                        metadata={"source_materials": input_ids},
                    )
                )

                print(
                    f"\nSummary: Consuming {len(processing_inputs)} inputs -> Creating {out_qty} {out_sel[1]}"
                )

            except ValueError:
                print("Invalid output quantity.")
                continue

        # --- 3. SHIP ---
        elif choice in ["3", "S"]:
            with sqlite3.connect(db_path) as conn:
                ships = conn.execute(
                    "SELECT shipment_id, g.name, s.current_location FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=? AND s.is_active=1",
                    (sender_pub,),
                ).fetchall()

            print("\n[ Ship Goods ]")
            sel = select_from_menu(
                ships, "Your Inventory", lambda x: f"{x[0]} - {x[1]} at {x[2]}"
            )
            if sel:
                with sqlite3.connect(db_path) as conn:
                    partners = conn.execute(
                        "SELECT name, role FROM participants WHERE name != ?",
                        (node_name,),
                    ).fetchall()

                rec = select_from_menu(
                    partners, "Select Receiver", lambda x: f"{x[0]} ({x[1]})"
                )
                if rec:
                    rec_pub = node.get_public_key_by_name(rec[0])
                    loc = input("New Location (e.g., 'In Transit'): ")
                    txs.append(
                        Transaction(
                            sender_pub, rec_pub, sel[0], ActionType.SHIPPED, loc
                        )
                    )

        # --- 4. DESTROY ---
        elif choice in ["4", "D"]:
            with sqlite3.connect(db_path) as conn:
                ships = conn.execute(
                    "SELECT shipment_id, g.name FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=? AND s.is_active=1",
                    (sender_pub,),
                ).fetchall()

            print("\n[ Destroy Goods ]")
            sel = select_from_menu(
                ships, "Select Item to Destroy", lambda x: f"{x[0]} ({x[1]})"
            )
            if sel:
                reason = input("Reason: ")
                txs.append(
                    Transaction(
                        sender_pub,
                        sender_pub,
                        sel[0],
                        ActionType.DESTROYED,
                        "Destroyed",
                        metadata={"reason": reason},
                    )
                )

        # --- 5. VOTE ---
        elif choice in ["5", "V"]:
            with sqlite3.connect(db_path) as conn:
                partners = conn.execute(
                    "SELECT name, votes FROM participants WHERE name != ? ORDER BY votes DESC",
                    (node_name,),
                ).fetchall()

            print("\n[ Vote for Delegate ]")
            rec = select_from_menu(
                partners, "Candidates", lambda x: f"{x[0]} (Current Votes: {x[1]})"
            )
            if rec:
                cand_pub = node.get_public_key_by_name(rec[0])
                txs.append(
                    Transaction(
                        sender_pub,
                        cand_pub,
                        f"VOTE-{int(time.time())}",
                        ActionType.VOTE,
                        "Ballot",
                    )
                )

        # --- BATCH PROCESS (Updated for Network) ---
        if txs:
            print(f"\nProcessing {len(txs)} transaction(s)...")

            for i, tx in enumerate(txs, 1):
                # 1. Local Pre-Check (Optional but good UX)
                is_valid_logic, error_msg = node.validate_smart_contract_rules(tx)
                if not is_valid_logic:
                    print(f"    [!] Tx {i}/{len(txs)} FAILED LOCAL CHECK: {error_msg}")
                    continue

                # 2. Sign
                if tx.sign_transaction(priv_key):
                    # 3. Send to Local P2P Node via HTTP
                    payload = tx.to_dict()
                    payload["signature"] = tx.signature

                    try:
                        resp = requests.post(
                            f"{base_url}/transaction", json=payload, timeout=2
                        )
                        if resp.status_code == 201:
                            print(
                                f"    [+] Tx {i}/{len(txs)} Broadcasted ({tx.action})"
                            )
                        else:
                            print(
                                f"    [!] Tx {i}/{len(txs)} Rejected by Node: {resp.text}"
                            )
                    except requests.exceptions.ConnectionError:
                        print(
                            f"    [X] Error: Could not connect to {base_url}. Is 'p2p.py' running?"
                        )
                else:
                    print(f"    [!] Tx {i}/{len(txs)} Signing Failed.")

            input("\nBatch complete. Press Enter to return to menu...")


if __name__ == "__main__":
    main()
