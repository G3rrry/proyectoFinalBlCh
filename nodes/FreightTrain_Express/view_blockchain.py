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
    print(f"[{node_name.upper()}] LEDGER (PoS)")
    print("=" * 80)

    chain = node.load_chain()
    if not chain:
        print("(Empty)")
    else:
        for block in chain:
            print(f"\n[ BLOCK #{block.index} ]")
            print(f"Time      : {time.ctime(block.timestamp)}")
            print(f"Validator : {block.validator} (PoS Winner)")
            print(f"Hash      : {block.hash}")

            for tx in block.transactions:
                s = node.get_name_by_public_key(tx.sender)
                if tx.action == "DESTROYED":
                    print(
                        f"   > {tx.action:<10}: {tx.shipment_id} removed. Reason: {tx.metadata.get('reason')}"
                    )
                elif tx.action in ["EXTRACTED", "PROCESSED"]:
                    print(
                        f"   > {tx.action:<10}: {s} created {tx.shipment_id} ({tx.quantity} {tx.good_id})"
                    )
                else:
                    r = node.get_name_by_public_key(tx.receiver)
                    print(f"   > {tx.action:<10}: {tx.shipment_id} moved {s} -> {r}")
            print("-" * 80)

    print("\n" + "-" * 30 + " ACTIVE INVENTORY " + "-" * 30)
    print(f"{'ID':<15} | {'Good':<15} | {'Owner':<20} | {'Location':<15}")
    print("-" * 75)

    conn = sqlite3.connect(node.db_file)
    rows = conn.execute(
        "SELECT s.shipment_id, g.name, s.current_owner_pk, s.current_location FROM shipments s JOIN goods g ON s.good_id = g.good_id"
    ).fetchall()
    conn.close()

    if not rows:
        print("(No active shipments)")
    else:
        for row in rows:
            sh, g, own_pk, loc = row
            own = node.get_name_by_public_key(own_pk)
            print(f"{sh:<15} | {g[:15]:<15} | {own[:20]:<20} | {loc:<15}")
    print("\n")


if __name__ == "__main__":
    view_local_ledger()
