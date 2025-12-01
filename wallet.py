import sqlite3
import os
from ecdsa import SigningKey, SECP256k1
from initialize import BlockchainNode


def create_new_wallet():
    print("\n--- CREATE NEW PARTICIPANT ---")

    name = input("Enter your unique Name (e.g., MyTransportCo): ").strip()
    if not name:
        print("Name cannot be empty.")
        return

    node = BlockchainNode()
    if node.get_public_key_by_name(name):
        print(f"Error: The name '{name}' is already taken. Please choose another.")
        return

    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.verifying_key

    private_key_hex = sk.to_string().hex()
    public_key_hex = vk.to_string().hex()

    filename = f"{name}.pem"
    try:
        with open(filename, "w") as f:
            f.write(private_key_hex)
        print(f"\nSUCCESS: Private key saved to '{filename}'")
        print("WARNING: Do not lose this file. You need it to sign transactions.")
    except Exception as e:
        print(f"Error saving file: {e}")
        return

    conn = sqlite3.connect(node.db_file)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO participants (name, public_key, role) VALUES (?, ?, ?)",
            (name, public_key_hex, "User_Created"),
        )
        conn.commit()
        print(f"SUCCESS: Participant '{name}' registered in the Blockchain Database.")
    except sqlite3.IntegrityError as e:
        print(f"Database Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    create_new_wallet()
