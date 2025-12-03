import os
import shutil
import sqlite3
import time
import random
from ecdsa import SigningKey, SECP256k1
from blockchain_core import BlockchainNode, Transaction, Block

#Definimos donde se guardaran los nodos simulados
NODES_DIR = "nodes"


#Lista de archivos que copiaremos a cada nodo para que funcionen independientemente
FILES_TO_INSTALL = [
    "blockchain_core.py",
    "p2p.py",
    "add_transaction.py",
    "view_blockchain.py",
]


def setup_environment():
    #1. Limpieza del Entorno
    #Borramos la carpeta de nodos anterior para empezar desde cero
    if os.path.exists(NODES_DIR):
        print(f"[*] Limpiando directorio '{NODES_DIR}/'...")
        shutil.rmtree(NODES_DIR)
    os.makedirs(NODES_DIR)

    #2. Definir Participantes de la Red (Consorcio)
    #Aqui definimos quienes forman parte de la cadena de suministro
    participants = [
        ("Mina_Global_Corp", 100, "Extractor"),        #Proveedor de Materia Prima
        ("Logistica_Pacifico", 95, "Logistica"),       #Empresa de transporte
        ("Fabrica_Tech_Inc", 90, "Manufactura"),       #Fabrica de productos
        ("Barco_Carga_EverGiven", 10, "Transportista"),#Transporte maritimo
        ("Tren_Carga_Express", 10, "Transportista"),   #Transporte ferroviario
        ("Flota_Camiones_Alfa", 5, "Transportista"),   #Transporte terrestre
        ("Drones_Entrega_X", 5, "Transportista"),      #Ultima milla
        ("Proveedor_Petroleo", 50, "Extractor"),       #Energia
        ("Servicios_Agua_Limpia", 40, "Utilidad"),     #Recursos basicos
        ("Mega_Tienda_Consumo", 60, "Minorista"),      #Venta al publico
        ("Tiendita_Esquina", 5, "Minorista"),          #Pequeño comercio
    ]

    print(f"--- INSTALANDO NODOS DPoS EN '{NODES_DIR}/' ---")


    #3. Definir Bienes y Estado Inicial
    #Catalogo de productos que existiran en la red
    goods_data = [
        ("G-LI", "Mineral de Litio", "Toneladas"),
        ("G-TI", "Aleacion de Titanio", "Kg"),
        ("G-OIL", "Petroleo Crudo", "Barriles"),
        ("G-H2O", "Agua Industrial", "Litros"),
        ("G-WHT", "Trigo", "Toneladas"),
        ("G-CHIP", "Microchips de Silicon", "Unidades"),
        ("G-PHONE", "Smartphone V15", "Unidades"),
        ("G-MED", "Vacunas", "Viales"),
    ]

    #Envios que ya existen desde el principio (Genesis)
    genesis_shipments = [
        ("SHIP-1001", "G-LI", 500.0, "Mina_Global_Corp", "Mina Nevada"),
        ("SHIP-1002", "G-OIL", 1000.0, "Proveedor_Petroleo", "Plataforma Marina"),
        ("SHIP-1003", "G-H2O", 50000.0, "Servicios_Agua_Limpia", "Embalse A"),
    ]

    #4. Generar Credenciales (Identidad Digital)
    #Creamos claves privadas y publicas para cada participante
    address_book = []
    print("Generando identidades criptograficas...")
    for name, rep, role in participants:
        #Usamos la curva SECP256k1 (la misma de Bitcoin) para las firmas
        sk = SigningKey.generate(curve=SECP256k1)
        sk_hex = sk.to_string().hex()
        pk = sk.verifying_key.to_string().hex()
        address_book.append((name, pk, role, rep, sk_hex))

    #5. Eleccion Genesis (Inicio Aleatorio)
    #Simulamos una votacion inicial para decidir quien valida el primer bloque
    print("Realizando Eleccion Genesis...")
    genesis_votes = {name: 0 for name, _, _, _, _ in address_book}

    for voter_name, _, _, _, _ in address_book:
        candidates = [p[0] for p in address_book if p[0] != voter_name]
        choice = random.choice(candidates)
        genesis_votes[choice] += 1
        print(f"   > {voter_name} voto por {choice}")


    #6. Crear Bloque Genesis
    #El primer bloque de la cadena no tiene padre previous_hash es cero
    genesis_validator = participants[0][0] #Por defecto el primero valida el genesis
    genesis_tx = Transaction(
        sender_public_key="0" * 64,
        receiver_public_key="0" * 64,
        shipment_id="GENESIS",
        action="MANUFACTURED",
        location="RAIZ",
        metadata={"msg": "Lanzamiento de la Red"},
    )
    #Firma dummy para el genesis
    genesis_tx.signature = "0" * 128
    genesis_block = Block(
        index=1,
        transactions=[genesis_tx],
        previous_hash="0" * 64,
        validator_address=genesis_validator,
        timestamp=time.time(),
    )

    #7. Configurar Nodos (Instalacion)
    for name, pk, role, rep, sk_hex in address_book:
        node_path = os.path.join(NODES_DIR, name)
        os.makedirs(node_path)

        #Copiamos los scripts de python a la carpeta del nodo
        for filename in FILES_TO_INSTALL:
            if os.path.exists(filename):
                shutil.copy(filename, os.path.join(node_path, filename))
            else:
                print(f"Error: {filename} no encontrado en directorio raiz.")


        #Guardamos la clave privada en un archivo seguro
        with open(os.path.join(node_path, "private_key.pem"), "w") as f:
            f.write(sk_hex)

        #Inicializamos la base de datos local del nodo
        db_path = os.path.join(node_path, "blockchain.db")
        BlockchainNode(name, db_path)

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        #Registramos a todos los participantes en la base de datos del nodo
        for p_name, p_pk, p_role, p_rep, _ in address_book:
            vote_count = genesis_votes[p_name]
            c.execute(
                "INSERT OR IGNORE INTO participants (name, public_key, role, reputation, votes) VALUES (?,?,?,?,?)",
                (p_name, p_pk, p_role, p_rep, vote_count),
            )

        #Registramos el catalogo de bienes
        for g in goods_data:
            c.execute("INSERT OR IGNORE INTO goods VALUES (?,?,?)", g)

        #Registramos los envios iniciales (Genesis State)
        for sh in genesis_shipments:
            sh_id, g_id, qty, owner, loc = sh
            #Buscamos la clave publica del dueno inicial
            owner_pk = next(p[1] for p in address_book if p[0] == owner)
            c.execute(
                "INSERT OR IGNORE INTO shipments (shipment_id, good_id, quantity, current_owner_pk, current_location, last_action, last_updated_timestamp, is_active) VALUES (?,?,?,?,?,?,?,1)",
                (sh_id, g_id, qty, owner_pk, loc, "EXTRACTED", time.time()),
            )

        #Insertamos el Bloque Genesis en la cadena local
        c.execute(
            "INSERT INTO blocks (block_index, block_hash, previous_hash, validator, timestamp, data) VALUES (?, ?, ?, ?, ?, ?)",
            (
                genesis_block.index,
                genesis_block.hash,
                genesis_block.previous_hash,
                genesis_block.validator,
                genesis_block.timestamp,
                genesis_block.to_json(),
            ),
        )

        conn.commit()
        conn.close()
        print(f"   > Nodo '{name}' instalado.")
    print("\nConfiguracion de Red Completa.")
    print("Ejecuta './start_network.sh' (o el de Windows) para iniciar los servidores.")


if __name__ == "__main__":
    setup_environment()