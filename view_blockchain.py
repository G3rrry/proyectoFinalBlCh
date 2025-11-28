import time
from initialize import BlockchainNode

if __name__ == "__main__":
    node = BlockchainNode()

    print("\n" + "=" * 50)
    print("🔎 BLOCKCHAIN VIEWER")
    print("=" * 50)

    # 1. View Ledger
    chain = node.load_chain()
    print(f"\n[ LEDGER HEIGHT: {len(chain)} ]")
    for block in chain:
        print(f"\n--- Block #{block.index} ---")
        print(f"Hash: {block.hash}")
        for tx in block.transactions:
            print(f"   > {tx.sender} -> {tx.receiver} | {tx.product_id} ({tx.action})")

    # 2. View World State
    print("\n" + "=" * 50)
    print("🌍 CURRENT WORLD STATE")
    print("=" * 50)
    print(f"{'Product':<15} | {'Owner':<15} | {'Location':<15} | {'Status':<15}")
    print("-" * 65)

    rows = node.get_world_state()
    if not rows:
        print("(Database empty)")
    else:
        for row in rows:
            # row: product_id, owner, location, action, timestamp
            print(f"{row[0]:<15} | {row[1]:<15} | {row[2]:<15} | {row[3]:<15}")

    print("\n")
