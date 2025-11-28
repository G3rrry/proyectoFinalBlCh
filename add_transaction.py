import sys
from initialize import BlockchainNode, Transaction, Block, ActionType


def get_strict_input(node: BlockchainNode):
    print("\n--- STRICT MODE: Existing Entities Only ---")

    # 1. Validate Sender
    sender = input("Sender Public Key: ").strip()
    if not node.participant_exists(sender):
        print(f"Error: Sender '{sender}' not found in database.")
        return None

    # 2. Validate Receiver
    receiver = input("Receiver Public Key: ").strip()
    if not node.participant_exists(receiver):
        print(f"Error: Receiver '{receiver}' not found in database.")
        return None

    # 3. Validate Product
    product_id = input("Product ID: ").strip()

    if not node.product_exists(product_id):
        print(
            f"Error: Product '{product_id}' not found. Use supreme_add_transaction.py to create it."
        )
        return None

    # 4. Action
    while True:
        print("Actions: [S]hipped, [R]eceived, [So]ld")
        c = input("Choice: ").strip().lower()
        if c == "s":
            action = ActionType.SHIPPED
            break
        elif c == "r":
            action = ActionType.RECEIVED
            break
        elif c == "so":
            action = ActionType.SOLD
            break
        else:
            print("Invalid choice.")

    location = input("Location: ").strip()

    return Transaction(sender, receiver, product_id, action, location)


if __name__ == "__main__":
    node = BlockchainNode()
    chain = node.load_chain()

    new_index = chain[-1].index + 1 if chain else 1
    prev_hash = chain[-1].hash if chain else "0" * 64

    tx_pool = []
    while True:
        tx = get_strict_input(node)
        if tx:
            tx_pool.append(tx)
            print("Transaction added to pool.")
        else:
            print("Transaction rejected due to validation failure.")

        if input("\nAttempt another? (y/n): ").lower() != "y":
            break

    if tx_pool:
        new_block = Block(new_index, tx_pool, prev_hash, "User_Node")
        node.save_block(new_block)
    else:
        print("No valid transactions generated.")
