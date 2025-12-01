from initialize import BlockchainNode


def verify_blockchain_integrity():
    print("\n--- STARTING INTEGRITY AUDIT ---")
    node = BlockchainNode()
    chain = node.load_chain()

    if not chain:
        print("Chain is empty.")
        return

    print(f"Checking Block 1 (Genesis)... OK")
    previous_hash = chain[0].hash

    for i in range(1, len(chain)):
        block = chain[i]

        if block.previous_hash != previous_hash:
            print(f"\n[!] FATAL ERROR AT BLOCK {block.index}")
            print("    RESULT: BROKEN CHAIN (Data manipulated)")
            return

        calculated_hash = block.calculate_block_hash()
        if block.hash != calculated_hash:
            print(f"\n[!] FATAL ERROR AT BLOCK {block.index}")
            print("    RESULT: CORRUPTED BLOCK (Content altered)")
            return

        print(f"Checking Block {block.index}... OK")
        previous_hash = block.hash

    print("\nAUDIT COMPLETE: Blockchain integrity is 100% valid.")


if __name__ == "__main__":
    verify_blockchain_integrity()
