from initialize import BlockchainNode, Transaction, Block, ActionType


def get_supreme_input():
    print("\n--- SUPREME MODE: Add New Entities/Transactions ---")
    sender = input("Sender: ").strip()
    receiver = input("Receiver: ").strip()
    product_id = input("Product ID: ").strip()

    while True:
        print("Actions: [M]anufactured, [S]hipped, [R]eceived, [So]ld")
        c = input("Choice: ").strip().lower()
        if c == "m":
            action = ActionType.MANUFACTURED
            break
        elif c == "s":
            action = ActionType.SHIPPED
            break
        elif c == "r":
            action = ActionType.RECEIVED
            break
        elif c == "so":
            action = ActionType.SOLD
            break

    location = input("Location: ").strip()
    return Transaction(sender, receiver, product_id, action, location)


if __name__ == "__main__":
    node = BlockchainNode()
    chain = node.load_chain()

    new_index = chain[-1].index + 1 if chain else 1
    prev_hash = chain[-1].hash if chain else "0" * 64

    tx_pool = []
    while True:
        tx_pool.append(get_supreme_input())
        if input("Add another? (y/n): ").lower() != "y":
            break

    if tx_pool:
        new_block = Block(new_index, tx_pool, prev_hash, "Admin_Node")
        node.save_block(new_block)
