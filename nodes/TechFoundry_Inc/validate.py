import os
import sys
import time

sys.path.append(os.getcwd())
from blockchain_core import BlockchainNode, Block  # Changed Import
import p2p


def get_identity():
    current_dir = os.getcwd()
    node_name = os.path.basename(current_dir)
    return node_name


def main():
    node_name = get_identity()
    db_path = "blockchain.db"
    if not os.path.exists(db_path):
        print("Error: Run inside a node folder.")
        return

    node = BlockchainNode(node_name, db_path)
    print(f"\n--- {node_name.upper()} VALIDATOR DASHBOARD ---")

    last_block = node.get_last_block()
    prev_hash = last_block.hash if last_block else "0" * 64
    expected_validator = node.select_validator(prev_hash)

    print(f"Current Block Height: {last_block.index if last_block else 0}")
    print(f"Expected Validator:   {expected_validator}")

    if expected_validator != node_name:
        print("\n[!] You are NOT the current validator.")
        print(f"    You must wait for {expected_validator} to forge the block.")
        return

    print("\n[+] You ARE the elected validator!")
    pending_txs = node.get_mempool_transactions()
    if not pending_txs:
        print("    Mempool is empty. Nothing to mine.")
        return

    print(f"    Found {len(pending_txs)} pending transactions.")
    valid_txs = []
    for tx in pending_txs:
        is_valid, msg = node.validate_smart_contract_rules(tx)
        if is_valid and tx.is_valid():
            valid_txs.append(tx)
            print(f"    - Tx {tx.tx_hash[:8]} ({tx.action}): VALID")
        else:
            print(f"    - Tx {tx.tx_hash[:8]}: INVALID ({msg}) - Discarding")

    if not valid_txs:
        print("    No valid transactions remaining.")
        return

    new_index = (last_block.index + 1) if last_block else 1
    new_block = Block(new_index, valid_txs, prev_hash, node_name)

    print(f"\n[+] Minting Block #{new_index}...")
    print(f"    Hash: {new_block.hash}")

    node.save_block_to_db(new_block)
    node.clear_mempool(valid_txs)
    print("    Block saved locally.")
    p2p.broadcast_block(node_name, new_block)
    print("    Block broadcasted to network.")


if __name__ == "__main__":
    main()
