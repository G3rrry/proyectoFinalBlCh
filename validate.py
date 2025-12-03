import os
import sys
import requests
import time
import json
from blockchain_core import BlockchainNode, Block

#Configuracion basica
NODE_NAME = os.path.basename(os.getcwd())

#Mapa de nombres de nodos a puertos
PEERS = {
    "Flota_Camiones_Alfa": 5001,
    "Fabrica_Tech_Inc": 5002,
    "Logistica_Pacifico": 5003,
    "Proveedor_Petroleo": 5004,
    "Mega_Tienda_Consumo": 5005,
    "Mina_Global_Corp": 5006,
    "Tren_Carga_Express": 5007,
    "Drones_Entrega_X": 5008,
    "Tiendita_Esquina": 5009,
    "Servicios_Agua_Limpia": 5010,
    "Barco_Carga_EverGiven": 5011,
}

MY_PORT = PEERS.get(NODE_NAME, 5000)
BASE_URL = f"http://localhost:{MY_PORT}"



def main():
    print(f"\n--- PANEL DE VALIDACION DE {NODE_NAME.upper()} ---")
    #1.Obtener informacion del nodo servidor local
    try:
        resp = requests.get(f"{BASE_URL}/info", timeout=2)
        info = resp.json()
    except requests.exceptions.ConnectionError:
        print(f"[!] Error El servidor del nodo no esta corriendo en {BASE_URL}")
        print(f"    Asegurate de que p2p.py este ejecutandose.")
        return

    print(f"Altura Actual: {info['height']}")

    #2.Verificar logica de consenso leyendo la base de datos
    node = BlockchainNode(NODE_NAME, "blockchain.db")
    last_block = node.get_last_block()
    prev_hash = last_block.hash if last_block else "0" * 64


    #RUBRICA:Metodo de Consenso
    #Verificamos si segun las reglas de votacion DPoS es nuestro turno de validar
    expected_validator = node.select_validator(prev_hash)
    print(f"Validador Esperado: {expected_validator}")

    if expected_validator != NODE_NAME:
        print("\n[!] NO eres el validador actual.")
        print(f"    Esperando a {expected_validator}...")
        return

    print("\n[+] ERES el validador electo!")

    #3.Proceso de creacion de bloque o minado
    mempool = node.get_mempool_transactions()
    if not mempool:
        print("    La Mempool esta vacia no hay nada que minar.")
        return

    print(f"    Encontradas {len(mempool)} transacciones.")
    valid_txs = []
    for tx in mempool:
        #RUBRICA:Aspectos Relevantes
        #Validamos reglas de contrato inteligente y firma digital antes de incluir
        is_valid, msg = node.validate_smart_contract_rules(tx)
        if is_valid and tx.is_valid():
            valid_txs.append(tx)
        else:
            print(f"    Saltando tx invalida: {tx.tx_hash[:8]} ({msg})")

    if not valid_txs:
        print("    No hay transacciones validas para empaquetar.")
        return

    new_index = (last_block.index + 1) if last_block else 1
    new_block = Block(new_index, valid_txs, prev_hash, NODE_NAME)

    print(f"\n[+] Minando Bloque #{new_index}...")


    #4.Enviar el bloque nuevo al servidor para que lo propague
    try:
        block_payload = json.loads(new_block.to_json())

        r = requests.post(f"{BASE_URL}/block", json=block_payload)
        if r.status_code == 201:
            print(f"Exito Bloque #{new_index} minado y transmitido.")
        else:
            print(f"Error enviando bloque: {r.text}")
    except Exception as e:
        print(f"    Error de comunicacion: {e}")



if __name__ == "__main__":
    main()