import os
import shutil
import sqlite3
import time
from ecdsa import SigningKey, SECP256k1
from initialize import BlockchainNode

NODES_DIR = "nodes"
# Removed KEYS_SOURCE as we are generating keys fresh
FILES_TO_INSTALL = [
    "initialize.py",
    "p2p.py",
    "add_transaction.py",
    "view_blockchain.py",
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

    print(f"--- INSTALLING DECENTRALIZED NODES IN '{NODES_DIR}/' ---")

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

    # Pre-calculate Public Keys (Generating FRESH keys for everyone)
    address_book = []
    print("Generating identities...")
    for name, rep, role in participants:
        # Generate new key pair
        sk = SigningKey.generate(curve=SECP256k1)
        sk_hex = sk.to_string().hex()
        pk = sk.verifying_key.to_string().hex()

        address_book.append((name, pk, role, rep, sk_hex))

    # Initialize Each Node
    for name, pk, role, rep, sk_hex in address_book:
        node_path = os.path.join(NODES_DIR, name)
        os.makedirs(node_path)

        # 1. Install Software
        for filename in FILES_TO_INSTALL:
            if os.path.exists(filename):
                shutil.copy(filename, os.path.join(node_path, filename))
            else:
                print(f"Error: {filename} not found in root. Cannot copy.")

        # 2. Install Private Key
        with open(os.path.join(node_path, "private_key.pem"), "w") as f:
            f.write(sk_hex)

        # 3. Initialize Local DB
        db_path = os.path.join(node_path, "blockchain.db")
        BlockchainNode(name, db_path)

        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Populate Address Book
        for p_name, p_pk, p_role, p_rep, _ in address_book:
            c.execute(
                "INSERT OR IGNORE INTO participants VALUES (?,?,?,?)",
                (p_name, p_pk, p_role, p_rep),
            )

        # Populate Goods
        for g in goods_data:
            c.execute("INSERT OR IGNORE INTO goods VALUES (?,?,?)", g)

        # Genesis Shipments
        for sh in genesis_shipments:
            sh_id, g_id, qty, owner, loc = sh
            # Find owner's PK from our generated address book
            owner_pk = next(p[1] for p in address_book if p[0] == owner)
            c.execute(
                "INSERT OR IGNORE INTO shipments VALUES (?,?,?,?,?,?,?)",
                (sh_id, g_id, qty, owner_pk, loc, "EXTRACTED", time.time()),
            )

        conn.commit()
        conn.close()
        print(f"   > Node '{name}' installed.")

    print("\nNetwork Setup Complete. Each node is isolated.")


if __name__ == "__main__":
    setup_environment()
