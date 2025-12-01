import os
import sys
from initialize import BlockchainNode


# Detect if running inside a node folder or root
def get_network_root():
    current_dir = os.getcwd()
    if os.path.basename(os.path.dirname(current_dir)) == "nodes":
        return os.path.dirname(current_dir)
    return "nodes"


def broadcast_block(source_node_name, block):
    network_root = get_network_root()

    print(f"\n[P2P] {source_node_name} is broadcasting Block #{block.index}...")

    if not os.path.exists(network_root):
        print("[P2P] Error: Network directory not found.")
        return

    peers = [
        d
        for d in os.listdir(network_root)
        if os.path.isdir(os.path.join(network_root, d))
    ]

    consensus_count = 0
    total_peers = 0

    for peer_name in peers:
        if peer_name == source_node_name:
            continue

        total_peers += 1
        peer_path = os.path.join(network_root, peer_name)
        peer_db = os.path.join(peer_path, "blockchain.db")

        # Instantiate peer node to handle reception
        peer_node = BlockchainNode(peer_name, peer_db)

        # Peer performs validation
        accepted, message = peer_node.receive_block(block)

        if accepted:
            print(f"  + Node {peer_name:<20} ACCEPTED block.")
            consensus_count += 1
        else:
            print(f"  - Node {peer_name:<20} REJECTED block: {message}")

    print(
        f"[P2P] Broadcast complete. Consensus: {consensus_count}/{total_peers} peers updated.\n"
    )
