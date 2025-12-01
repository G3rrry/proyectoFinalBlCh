import sqlite3
import time
import os
import sys

sys.path.append(os.getcwd())

from initialize import BlockchainNode


def view_local_ledger():
    current_dir = os.getcwd()
    node_name = os.path.basename(current_dir)
    db_file = "blockchain.db"

    if not os.path.exists(db_file):
        print(f"Error: No blockchain database found in {current_dir}")
        return

    node = BlockchainNode(node_name, db_file)

    print("\n" + "=" * 80)
    print(f"[{node_name.upper()}] LOCAL LEDGER VIEW")
    print("=" * 80)

    # 1. CHAIN VIEW
    print("\n" + "-" * 30 + " BLOCKCHAIN " + "-" * 31)
    chain = node.load_chain()

    if not chain:
        print("(Blockchain is empty)")
    else:
        for block in chain:
            print(f"\n[ BLOCK #{block.index} ]")
            print(f"Timestamp   : {time.ctime(block.timestamp)}")
            print(f"Validator   : {block.validator}")
            print(f"Block Hash  : {block.hash}")
            print(f"Prev Hash   : {block.previous_hash}")

            for tx in block.transactions:
                s = node.get_name_by_public_key(tx.sender)
                r = node.get_name_by_public_key(tx.receiver)

                g_name = tx.good_id
                if tx.good_id:
                    with sqlite3.connect(node.db_file) as conn:
                        res = conn.execute(
                            "SELECT name FROM goods WHERE good_id = ?", (tx.good_id,)
                        ).fetchone()
                        if res:
                            g_name = res[0]

                if tx.action in ["EXTRACTED", "PROCESSED"]:
                    print(
                        f"   > {tx.action:<10}: {s} created {tx.shipment_id} ({tx.quantity} {g_name})"
                    )
                else:
                    print(
                        f"   > {tx.action:<10}: {tx.shipment_id} moved {s} -> {r} @ {tx.location}"
                    )

            print("-" * 80)

    # 2. WORLD STATE
    print("\n" + "-" * 30 + " LOCAL WORLD STATE (Ownership) " + "-" * 17)
    print(f"{'ID':<12} | {'Good':<18} | {'Qty':<15} | {'Owner':<20} | {'Location':<15}")
    print("-" * 88)

    conn = sqlite3.connect(node.db_file)
    cursor = conn.cursor()
    query = """
        SELECT s.shipment_id, g.name, g.unit_of_measure, s.quantity, s.current_owner_pk, s.current_location
        FROM shipments s
        JOIN goods g ON s.good_id = g.good_id
    """
    rows = cursor.execute(query).fetchall()
    conn.close()

    if not rows:
        print("(No active shipments known to this node)")
    else:
        for row in rows:
            sh_id, g_name, unit, qty, owner_pk, loc = row
            owner_name = node.get_name_by_public_key(owner_pk)
            qty_str = f"{qty} {unit}"
            print(
                f"{sh_id:<12} | {g_name[:18]:<18} | {qty_str:<15} | {owner_name[:20]:<20} | {loc:<15}"
            )

    print("\n")


if __name__ == "__main__":
    view_local_ledger()
