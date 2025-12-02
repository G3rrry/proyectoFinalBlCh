import sqlite3
import time
import os
import sys

sys.path.append(os.getcwd())
from blockchain_core import BlockchainNode


def view_local_ledger():
    current_dir = os.getcwd()
    node_name = os.path.basename(current_dir)
    db_file = "blockchain.db"

    if not os.path.exists(db_file):
        print(f"Error: No blockchain database found in {current_dir}")
        return

    node = BlockchainNode(node_name, db_file)

    print("\n" + "=" * 100)
    print(f"[{node_name.upper()}] IMMUTABLE LEDGER (DPoS)")
    print("=" * 100)

    chain = node.load_chain()
    if not chain:
        print("(Empty Chain)")
    else:
        for block in chain:
            print(f"\n[ BLOCK #{block.index} ]")
            print(f"Timestamp     : {time.ctime(block.timestamp)}")
            print(f"Validator     : {block.validator}")
            print(f"Hash          : {block.hash}")
            print(f"Previous Hash : {block.previous_hash}")
            print(f"Merkle Root   : {block.merkle_root}")
            print(f"Transactions  : {len(block.transactions)}")
            print("-" * 50)

            if not block.transactions:
                print("   (No transactions)")

            for tx in block.transactions:
                s = node.get_name_by_public_key(tx.sender)

                if tx.action == "VOTE":
                    c = node.get_name_by_public_key(tx.receiver)
                    print(f"   > [VOTE]      {s} voted for candidate {c}")

                elif tx.action == "DESTROYED":
                    reason = tx.metadata.get("reason", "Unknown")
                    print(f"   > [DESTROYED] {tx.shipment_id} removed by {s}")
                    print(f"                 Reason: {reason}")

                elif tx.action == "CONSUMED":
                    product = tx.metadata.get("product", "Goods")
                    print(f"   > [CONSUMED]  {tx.shipment_id} used by {s}")
                    print(f"                 Input for: {product}")

                elif tx.action in ["EXTRACTED", "MANUFACTURED"]:
                    verb = "created" if tx.action == "EXTRACTED" else "manufactured"
                    print(f"   > [CREATED]   {s} {verb} {tx.shipment_id}")
                    print(
                        f"                 {tx.quantity} {tx.good_id} at {tx.location}"
                    )
                    if (
                        tx.action == "MANUFACTURED"
                        and "source_materials" in tx.metadata
                    ):
                        print(
                            f"                 Sources: {tx.metadata['source_materials']}"
                        )

                elif tx.action == "SHIPPED":
                    r = node.get_name_by_public_key(tx.receiver)
                    print(f"   > [SHIPPED]   {tx.shipment_id} moved from {s} -> {r}")
                    print(f"                 To: {tx.location}")

                elif tx.action == "RECEIVED":
                    print(f"   > [RECEIVED]  {s} confirmed/updated {tx.shipment_id}")
                    print(f"                 At: {tx.location}")
                    if tx.quantity:
                        print(f"                 Updated Qty: {tx.quantity}")

                print(f"                 [TxID: {tx.tx_hash[:16]}...]")

            print("=" * 100)

    print("\n" + "*" * 40 + " DELEGATE STANDINGS " + "*" * 40)
    print(f"{'Candidate Name':<30} | {'Votes':<10} | {'Status'}")
    print("-" * 60)

    conn = sqlite3.connect(node.db_file)
    delegates = conn.execute(
        "SELECT name, votes FROM participants ORDER BY votes DESC"
    ).fetchall()

    for i, (name, votes) in enumerate(delegates):
        status = "ACTIVE WITNESS" if i < 3 else "Standby"
        prefix = " --(Active)-- " if i < 3 else "  "
        print(f"{prefix}{name:<28} | {votes:<10} | {status}")

    print("\n" + "#" * 40 + " WORLD STATE (Active Inventory) " + "#" * 40)
    print(
        f"{'Shipment ID':<18} | {'Good':<15} | {'Quantity':<12} | {'Owner':<20} | {'Location':<15} | {'Last Action'}"
    )
    print("-" * 100)

    # Filter by is_active = 1
    rows = conn.execute(
        """
        SELECT s.shipment_id, g.name, s.quantity, g.unit_of_measure, s.current_owner_pk, s.current_location, s.last_action
        FROM shipments s 
        JOIN goods g ON s.good_id = g.good_id
        WHERE s.is_active = 1
        ORDER BY s.last_updated_timestamp DESC
        """
    ).fetchall()
    conn.close()

    if not rows:
        print("(No active shipments in world state)")
    else:
        for row in rows:
            sh, g_name, qty, unit, own_pk, loc, action = row
            own = node.get_name_by_public_key(own_pk)
            qty_str = f"{qty} {unit}"
            print(
                f"{sh:<18} | {g_name[:15]:<15} | {qty_str:<12} | {own[:20]:<20} | {loc[:15]:<15} | {action}"
            )

    print("\n")


if __name__ == "__main__":
    view_local_ledger()
