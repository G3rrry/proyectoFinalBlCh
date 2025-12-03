import sys
import os
import json
import requests
import argparse
import threading
import time
from flask import Flask, jsonify, request
from blockchain_core import BlockchainNode, Block, Transaction, ActionType

#Configuracion Inicial
app = Flask(__name__)
#Usamos el nombre de la carpeta como la Identidad del nodo (ej. Node_1)
NODE_NAME = os.path.basename(os.getcwd())
DB_PATH = "blockchain.db"

#Inicializamos el Nodo Blockchain con la base de datos local
node = BlockchainNode(NODE_NAME, DB_PATH)


#Lista de compañeros conocidos en la red (Peer-to-Peer)
#Aqui definimos a quien le vamos a chismear (Gossip) la informacion
PEERS = {
    "Truck_Fleet_Alpha": "http://localhost:5001",
    "TechFoundry_Inc": "http://localhost:5002",
    "Pacific_Logistics": "http://localhost:5003",
    "OPEC_Supplier": "http://localhost:5004",
    "Mega_Consumer_Goods": "http://localhost:5005",
    "GlobalMining_Corp": "http://localhost:5006",
    "FreightTrain_Express": "http://localhost:5007",
    "Drone_Delivery_X": "http://localhost:5008",
    "Corner_Store": "http://localhost:5009",
    "CleanWater_Services": "http://localhost:5010",
    "CargoShip_EverGiven": "http://localhost:5011",
}

#Determinamos en que puerto debe correr este nodo especifico
MY_PORT = 5000 #Puerto por defecto si no lo encontramos en la lista
if NODE_NAME in PEERS:
    MY_PORT = int(PEERS[NODE_NAME].split(":")[-1])


#Hilo de Minado Automatico (Validacion)
def auto_mine_loop():
    #Esta funcion corre en segundo plano y revisa si es nuestro turno de crear un bloque
    print(f"[*] Iniciando Validacion Automatica para {NODE_NAME}")

    while True:
        time.sleep(5) #Esperamos 5 segundos entre cada chequeo (Tiempo de Bloque)

        try:
            #1. Revisamos el estado actual de la red
            last_block = node.get_last_block()
            if not last_block:
                continue

            prev_hash = last_block.hash
            height = last_block.index

            #2. Preguntamos al Consenso: Soy yo el validador de este turno?
            #RUBRICA: Metodo de Consenso (Proof of Authority / DPoS)
            expected_validator = node.select_validator(prev_hash)

            if expected_validator == NODE_NAME:
                #3. Si es mi turno reviso si hay transacciones pendientes en la mempool
                mempool = node.get_mempool_transactions()
                if mempool:
                    print(f"\n   [ ] Es mi turno! Validando {len(mempool)} transacciones...")

                    #4. Filtramos solo las transacciones validas
                    valid_txs = []
                    for tx in mempool:
                        is_valid_logic, _ = node.validate_smart_contract_rules(tx)
                        if is_valid_logic and tx.is_valid():
                            valid_txs.append(tx)

                    if valid_txs:
                        #5. Creamos el nuevo bloque
                        new_index = height + 1
                        new_block = Block(new_index, valid_txs, prev_hash, NODE_NAME)

                        #6. Lo guardamos en nuestra propia base de datos
                        success, msg = node.receive_block(new_block)
                        if success:
                            print(
                                f"   [+] Bloque #{new_index} Creado ({new_block.hash[:8]}). Propagando..."
                            )
                            #7. IMPORTANTE: Lo enviamos a todos los demas nodos (Gossip)
                            broadcast_block(new_block)
                        else:
                            print(f"   [!] Error de auto-validacion: {msg}")
        except Exception as e:
            print(f"   [!] Error en el proceso de validacion: {e}")


#API Endpoints (Interfaces para que otros nodos nos hablen)
@app.route("/info", methods=["GET"])
def get_info():
    #Devuelve informacion basica del estado de este nodo
    last_block = node.get_last_block()
    return jsonify(
        {
            "node_name": NODE_NAME,
            "height": last_block.index if last_block else 0,
            "last_hash": last_block.hash if last_block else "0" * 64,
        }
    )


@app.route("/chain", methods=["GET"])
def get_chain():
    #Permite a otros nodos descargar nuestra copia de la blockchain para sincronizarse
    chain_data = []
    last = node.get_last_block()
    height = last.index if last else 0
    for i in range(1, height + 1):
        blk = node.get_block_by_index(i)
        if blk:
            chain_data.append(json.loads(blk.to_json()))
        # 


    return jsonify(chain_data)


@app.route("/transaction", methods=["POST"])
def receive_transaction():
    #Recibimos una transaccion nueva de otro nodo o de una wallet
    data = request.get_json()
    try:
        tx = Transaction(
            data["sender"],
            data["receiver"],
            data["shipment_id"],
            ActionType(data["action"]),
            data["location"],
            data.get("good_id"),
            data.get("quantity"),
            data.get("metadata"),
            data.get("timestamp"),
            data.get("signature"),
        )

        #Intentamos agregarla a nuestra mempool local
        success, msg = node.add_to_mempool(tx)

        if success:
            print(f"[*] Tx Recibida {tx.tx_hash[:8]} (Nueva) - Reenviando a la red...")
            #RUBRICA: Metodo de Distribucion (Gossip Protocol)
            #Si la transaccion es valida y nueva se la pasamos a nuestros vecinos
            threading.Thread(target=broadcast_transaction, args=(tx,)).start()
            return jsonify({"message": "Transaccion agregada y retransmitida"}), 201

        elif msg == "Duplicada":
            #Si ya la teniamos no hacemos nada para evitar bucles infinitos
            return jsonify({"message": "Transaccion ya conocida"}), 200

        return jsonify({"message": f"Tx Invalida: {msg}"}), 400
    except Exception as e:
        return jsonify({"message": str(e)}), 400



@app.route("/block", methods=["POST"])
def receive_block():
    #Recibimos un bloque nuevo propuesto por el validador del turno
    data = request.get_json()
    try:
        block = Block.from_json(json.dumps(data))
        print(f"[*] Bloque Recibido #{block.index} de {block.validator}")

        #1. Intentamos agregarlo a nuestra cadena local
        success, msg = node.receive_block(block)

        if success:
            print(f"    [+] Bloque Aceptado. Nueva Altura: {block.index}")

            #2. GOSSIP: Si el bloque es valido lo pasamos a los demas para que se propague rapido
            threading.Thread(target=broadcast_block, args=(block,)).start()

            return jsonify({"message": "Bloque aceptado"}), 201
        else:
            print(f"    [-] Bloque Rechazado: {msg}")
            #Si lo rechazamos porque nos faltan bloques anteriores activamos la sincronizacion
            if "Falta el bloque anterior" in msg or "Indice Invalido" in msg:
                threading.Thread(target=synchronize_chain).start()
            return jsonify({"message": f"Bloque rechazado: {msg}"}), 409
    except Exception as e:
        print(f"Error procesando bloque: {e}")
        return jsonify({"message": str(e)}), 400


#Funciones P2P para hablar con otros nodos

def broadcast_transaction(tx):
    #Envia una transaccion a todos los peers conocidos
    tx_data = tx.to_dict()
    tx_data["signature"] = tx.signature
    for name, url in PEERS.items():
        if name == NODE_NAME:
            continue
        try:
            requests.post(f"{url}/transaction", json=tx_data, timeout=1)
        except:
            pass



def broadcast_block(block):
    #Envia un bloque nuevo a todos los peers conocidos
    block_json = json.loads(block.to_json())
    for name, url in PEERS.items():
        if name == NODE_NAME:
            continue
        try:
            requests.post(f"{url}/block", json=block_json, timeout=1)
        except Exception as e:
            print(f"    [!] Fallo al contactar a {name}")



def synchronize_chain():
    #RUBRICA: Metodo de Distribucion (Sincronizacion)
    #Busca al nodo con la cadena mas larga y descarga los bloques faltantes
    print("[*] Iniciando Sincronizacion...")
    best_height = 0
    best_peer = None

    #1. Preguntamos a todos los vecinos cual es su altura
    for name, url in PEERS.items():
        if name == NODE_NAME:
            continue
        try:
            resp = requests.get(f"{url}/info", timeout=1)
            if resp.status_code == 200:
                info = resp.json()
                if info["height"] > best_height:
                    best_height = info["height"]
                    best_peer = url
        except:
            pass
    my_height = node.get_last_block().index if node.get_last_block() else 0

    #2. Si encontramos a alguien mas avanzado descargamos su cadena
    if best_height > my_height:
        print(f"[*] Cadena mas larga encontrada ({best_height}) en {best_peer}. Descargando...")
        try:
            resp = requests.get(f"{best_peer}/chain")
            if resp.status_code == 200:
                chain_dump = resp.json()
                for blk_data in chain_dump:
                    blk = Block.from_json(json.dumps(blk_data))
                    #Solo procesamos los bloques que nos faltan
                    if blk.index > my_height:
                        success, msg = node.receive_block(blk)
                        if success:
                            print(f"    Sincronizado Bloque #{blk.index}")
                        else:
                            print(f"    Error de Sincronizacion en #{blk.index}: {msg}")
                            break
        except Exception as e:
            print(f"Fallo la sincronizacion: {e}")
    else:
        print("[*] La cadena esta actualizada.")


#Arranque del Servidor
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="Puerto para correr el nodo")
    args = parser.parse_args()


    if args.port:
        MY_PORT = args.port


    #Sincronizacion Inicial al prender el nodo
    threading.Thread(target=synchronize_chain).start()

    #Iniciamos el hilo de validacion automatica
    threading.Thread(target=auto_mine_loop, daemon=True).start()

    print(f"\n=== NODO {NODE_NAME} CORRIENDO EN PUERTO {MY_PORT} ===")
    app.run(host="0.0.0.0", port=MY_PORT)