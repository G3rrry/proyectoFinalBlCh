import os
import shutil
import sqlite3
import time
import random
from ecdsa import SigningKey, SECP256k1
from blockchain_core import BlockchainNode

NODES_DIR = "nodes"
FILES_TO_INSTALL = [
    "blockchain_core.py",
    "p2p.py",
    "add_transaction.py",
    "view_blockchain.py",
    "validate.py",
]


def setup_environment():
    if os.path.exists(NODES_DIR):
        shutil.rmtree(NODES_DIR)
    os.makedirs(NODES_DIR)

    participants = [
        ("GlobalMining_Corp", 100, "Extractor"),
        ("Pacific_Logistics", 95, "Logistics"),
        ("TechFoundry_Inc", 90, "Manufacturer"),
        ("CargoShip_EverGiven", 10, "Transporter"),
        ("FreightTrain_Express", 10, "Transporter"),
        ("Truck_Fleet_Alpha", 5, "Transporter"),
        ("Drone_Delivery_X", 5, "Transporter"),
        ("OPEC_Supplier", 50, "Extractor"),
        ("CleanWater_Services", 40, "Utility"),
        ("Mega_Consumer_Goods", 60, "Retailer"),
        ("Corner_Store", 5, "Retailer"),
    ]

    print(f"--- INSTALLING DPoS NODES IN '{NODES_DIR}/' ---")

    goods_data = [
        ("G-LI", "Lithium Ore", "Tonnes"),
        ("G-TI", "Titanium Alloy", "Kg"),
        ("G-OIL", "Crude Oil", "Barrels"),
        ("G-H2O", "Industrial Water", "Liters"),
        ("G-WHT", "Wheat", "Tonnes"),
        ("G-CHIP", "Silicon Microchips", "Units"),
        ("G-PHONE", "Smartphone V15", "Units"),
        ("G-MED", "Vaccines", "Vials"),
    ]

    genesis_shipments = [
        ("SHIP-1001", "G-LI", 500.0, "GlobalMining_Corp", "Nevada Mine"),
        ("SHIP-1002", "G-OIL", 1000.0, "OPEC_Supplier", "Offshore Platform"),
        ("SHIP-1003", "G-H2O", 50000.0, "CleanWater_Services", "Reservoir A"),
    ]

    address_book = []
    print("Generating identities...")
    for name, rep, role in participants:
        sk = SigningKey.generate(curve=SECP256k1)
        sk_hex = sk.to_string().hex()
        pk = sk.verifying_key.to_string().hex()
        address_book.append((name, pk, role, rep, sk_hex))

    print("Conducting Genesis Election...")
    genesis_votes = {name: 0 for name, _, _, _, _ in address_book}

    for voter_name, _, _, _, _ in address_book:
        candidates = [p[0] for p in address_book if p[0] != voter_name]
        choice = random.choice(candidates)
        genesis_votes[choice] += 1
        print(f"   > {voter_name} cast genesis vote for {choice}")

    for name, pk, role, rep, sk_hex in address_book:
        node_path = os.path.join(NODES_DIR, name)
        os.makedirs(node_path)

        for filename in FILES_TO_INSTALL:
            if os.path.exists(filename):
                shutil.copy(filename, os.path.join(node_path, filename))
            else:
                print(f"Error: {filename} not found.")

        with open(os.path.join(node_path, "private_key.pem"), "w") as f:
            f.write(sk_hex)

        db_path = os.path.join(node_path, "blockchain.db")
        BlockchainNode(name, db_path)  # creates DB with is_active

        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        for p_name, p_pk, p_role, p_rep, _ in address_book:
            vote_count = genesis_votes[p_name]
            c.execute(
                "INSERT OR IGNORE INTO participants (name, public_key, role, reputation, votes) VALUES (?,?,?,?,?)",
                (p_name, p_pk, p_role, p_rep, vote_count),
            )

        for g in goods_data:
            c.execute("INSERT OR IGNORE INTO goods VALUES (?,?,?)", g)

        for sh in genesis_shipments:
            sh_id, g_id, qty, owner, loc = sh
            owner_pk = next(p[1] for p in address_book if p[0] == owner)
            # Default is_active=1
            c.execute(
                "INSERT OR IGNORE INTO shipments (shipment_id, good_id, quantity, current_owner_pk, current_location, last_action, last_updated_timestamp, is_active) VALUES (?,?,?,?,?,?,?,1)",
                (sh_id, g_id, qty, owner_pk, loc, "EXTRACTED", time.time()),
            )

        conn.commit()
        conn.close()
        print(f"   > Node '{name}' installed.")

    print("\nNetwork Setup Complete.")


if __name__ == "__main__":
    setup_environment()
