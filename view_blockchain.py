import sqlite3
import time
from initialize import BlockchainNode

if __name__ == "__main__":
    node = BlockchainNode()

    print("\n" + "=" * 80)
    print(f"{'SUPPLY CHAIN LEDGER & WORLD STATE':^80}")
    print("=" * 80)

    # 1. CHAIN VIEW
    print("\n" + "-" * 30 + " BLOCKCHAIN LEDGER " + "-" * 31)
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
            print(f"Merkle Root : {block.merkle_root}")
            print("Transactions:")

            for tx in block.transactions:
                s = node.get_name_by_public_key(tx.sender)
                r = node.get_name_by_public_key(tx.receiver)

                # Contextual Print based on Action Type
                if tx.action in ["EXTRACTED", "PROCESSED"]:
                    # Try to resolve Good Name for better readability
                    conn = sqlite3.connect(node.db_file)
                    g_name_res = conn.execute(
                        "SELECT name FROM goods WHERE good_id = ?", (tx.good_id,)
                    ).fetchone()
                    g_name = g_name_res[0] if g_name_res else tx.good_id
                    conn.close()

                    print(
                        f"   > {tx.action:<10}: {s} created {tx.shipment_id} ({tx.quantity} {g_name})"
                    )
                else:
                    print(
                        f"   > {tx.action:<10}: {tx.shipment_id} moved {s} -> {r} @ {tx.location}"
                    )

            print("-" * 80)

    # 2. WORLD STATE (The Shipments Table)
    print("\n" + "-" * 30 + " CURRENT WORLD STATE (SHIPMENTS) " + "-" * 17)

    print(f"{'ID':<12} | {'Good':<18} | {'Qty':<15} | {'Owner':<20} | {'Location':<15}")
    print("-" * 88)

    conn = sqlite3.connect(node.db_file)
    cursor = conn.cursor()
    # Join shipments with goods to get the name and unit
    query = """
        SELECT s.shipment_id, g.name, g.unit_of_measure, s.quantity, s.current_owner_pk, s.current_location
        FROM shipments s
        JOIN goods g ON s.good_id = g.good_id
    """
    rows = cursor.execute(query).fetchall()
    conn.close()

    if not rows:
        print("(No active shipments)")
    else:
        for row in rows:
            sh_id, g_name, unit, qty, owner_pk, loc = row
            owner_name = node.get_name_by_public_key(owner_pk)

            # Formatting quantity string (e.g., "500.0 Tonnes")
            qty_str = f"{qty} {unit}"

            print(
                f"{sh_id:<12} | {g_name[:18]:<18} | {qty_str:<15} | {owner_name[:20]:<20} | {loc:<15}"
            )

    print("\n")
