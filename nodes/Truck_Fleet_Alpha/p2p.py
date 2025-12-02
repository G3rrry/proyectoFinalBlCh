import os
import sys
from blockchain_core import BlockchainNode


def get_network_root():
    current_dir = os.getcwd()
    if os.path.basename(os.path.dirname(current_dir)) == "nodes":
        return os.path.dirname(current_dir)
    return "nodes"


def get_peers(source_node_name):
    network_root = get_network_root()
    if not os.path.exists(network_root):
        return []
    return [
        d
        for d in os.listdir(network_root)
        if os.path.isdir(os.path.join(network_root, d)) and d != source_node_name
    ]


def broadcast_transaction(source_node_name, transaction):
    network_root = get_network_root()
    peers = get_peers(source_node_name)
    print(
        f"\n[P2P] Broadcasting Transaction {transaction.tx_hash[:8]}... to {len(peers)} peers."
    )
    count = 0
    for peer_name in peers:
        peer_db = os.path.join(network_root, peer_name, "blockchain.db")
        peer_node = BlockchainNode(peer_name, peer_db)
        success, _ = peer_node.add_to_mempool(transaction)
        if success:
            count += 1
    print(f"[P2P] Transaction propagated to {count}/{len(peers)} nodes mempools.")


def broadcast_block(source_node_name, block):
    network_root = get_network_root()
    peers = get_peers(source_node_name)
    print(f"\n[P2P] {source_node_name} is broadcasting Block #{block.index}...")
    accepted_count = 0
    for peer_name in peers:
        peer_db = os.path.join(network_root, peer_name, "blockchain.db")
        peer_node = BlockchainNode(peer_name, peer_db)
        accepted, message = peer_node.receive_block(block)
        if accepted:
            print(f"  + Node {peer_name:<20} ACCEPTED.")
            accepted_count += 1
        else:
            print(f"  - Node {peer_name:<20} REJECTED: {message}")
    print(f"[P2P] Consensus: {accepted_count}/{len(peers)} nodes updated.\n")
