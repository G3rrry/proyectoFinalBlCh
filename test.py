import os
import time
import requests
import json
import random
from ecdsa import SigningKey, SECP256k1
from blockchain_core import Transaction, ActionType

#Configuracion de la Red
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



def get_keys(node_name):
    #Carga la clave privada del disco para poder firmar las pruebas
    key_path = os.path.join("nodes", node_name, "private_key.pem")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"No se encontro la clave para {node_name}")

    with open(key_path, "r") as f:
        priv_hex = f.read().strip()
    sk = SigningKey.from_string(bytes.fromhex(priv_hex), curve=SECP256k1)
    vk = sk.verifying_key
    return priv_hex, vk.to_string().hex()


def execute_step(step_num, sender_name, tx_data, title, narrative):
    #Ejecuta un paso de la simulacion imprimiendo la historia en consola
    print(f"\n{'=' * 80}")
    print(f"PASO {step_num}/10: {title.upper()}")
    print(f"{'-' * 80}")
    print(f"HISTORIA: {narrative}")

    #1. Preparamos las credenciales del emisor
    port = PEERS[sender_name]
    priv_key, pub_key = get_keys(sender_name)

    #2. Identificamos la clave publica del receptor
    receiver_pub = pub_key 
    if "receiver_name" in tx_data:
        _, receiver_pub = get_keys(tx_data.pop("receiver_name"))

    #3. Creamos el objeto Transaccion
    tx = Transaction(
        sender_public_key=pub_key,
        receiver_public_key=receiver_pub,
        shipment_id=tx_data["shipment_id"],
        action=tx_data["action"],
        location=tx_data["location"],
        good_id=tx_data.get("good_id"),
        quantity=tx_data.get("quantity"),
        metadata=tx_data.get("metadata"),
    )

    #4. Firmamos la transaccion (Firma Digital)
    tx.sign_transaction(priv_key)

    #5. Transmitimos via HTTP
    payload = tx.to_dict()
    payload["signature"] = tx.signature


    print(f"\nACCION: Enviando Transaccion al Nodo '{sender_name}' (Puerto {port})...")
    try:
        url = f"http://localhost:{port}/transaction"
        resp = requests.post(url, json=payload, timeout=2)
        if resp.status_code == 201:
            print(f"EXITO: La red acepto la transaccion.")
            print(f"Hash Tx: {tx.tx_hash[:16]}...")
            print(f"Payload: {tx.action} -> {tx.shipment_id}")
        else:
            print(f"FALLO: El nodo rechazo la Tx: {resp.text}")
            return
    except Exception as e:
        print(f"ERROR: Fallo la conexion: {e}")
        return


    #6. Esperamos a que la red valide (Consenso)
    print("\nCONSENSO: Esperando 6 segundos para minado y propagacion...")
    for i in range(6, 0, -1):
        print(f"   {i}...", end="\r")
        time.sleep(1)
    print("   Listo! El bloque deberia estar minado.\n")


def main():
    print("\n" + "#" * 80)
    print("SIMULACION DE CADENA DE SUMINISTRO: DE LA MINA AL MERCADO")
    print("#" * 80)


    #Generamos IDs aleatorios para los lotes de prueba
    raw_material_id = f"SHIP-LITIO-{random.randint(1000, 9999)}"
    finished_good_id = f"SHIP-BATERIA-{random.randint(1000, 9999)}"

    #1. EXTRACCION
    execute_step(
        1,
        "Mina_Global_Corp",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.EXTRACTED,
            "location": "Cuenca de Litio Nevada",
            "good_id": "G-LI",
            "quantity": 500.0,
        },
        "Extraccion de Materia Prima",
        "Mina Global inicia operaciones extrayendo 500 Toneladas de mineral de Litio crudo.",
    )

    #2. ENVIO A MANUFACTURA
    execute_step(
        2,
        "Mina_Global_Corp",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.SHIPPED,
            "location": "En Transito (Red Ferroviaria B)",
            "receiver_name": "Fabrica_Tech_Inc",
        },
        "Envio a la Fabrica",
        "El mineral crudo se carga en trenes con destino a la planta de procesamiento de Fabrica Tech.",
    )

    #3. RECEPCION EN FABRICA
    execute_step(
        3,
        "Fabrica_Tech_Inc",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.RECEIVED,
            "location": "Centro de Procesamiento Silicon Valley",
        },
        "Ingreso en Fabrica",
        "Fabrica Tech verifica el envio al llegar a su anden firmando la custodia en la blockchain.",
    )


    #4. CONSUMO DE INSUMOS
    execute_step(
        4,
        "Fabrica_Tech_Inc",
        {
            "shipment_id": raw_material_id,
            "action": ActionType.CONSUMED,
            "location": "Sector de Fundicion 4",
            "metadata": {"proceso": "Purificacion", "ratio_desperdicio": "0.05"},
        },
        "Procesamiento de Materia Prima",
        "El mineral de Litio entra al horno de fundicion. Se marca como Consumido del inventario para crear el producto.",
    )

    #5. MANUFACTURA DE PRODUCTO FINAL
    execute_step(
        5,
        "Fabrica_Tech_Inc",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.MANUFACTURED,
            "location": "Linea de Ensamblaje A",
            "good_id": "G-CHIP", 
            "quantity": 2000.0,
            "metadata": {"lote_origen": raw_material_id, "control_calidad": "APROBADO"},
        },
        "Manufactura de Bienes Terminados",
        "El litio refinado se usa para fabricar 2000 Microchips. Se crea un gemelo digital del lote.",
    )


    #6. ENVIO A LOGISTICA
    execute_step(
        6,
        "Fabrica_Tech_Inc",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.SHIPPED,
            "location": "Carga de Salida",
            "receiver_name": "Logistica_Pacifico",
        },
        "Traspaso a Logistica",
        "Los chips terminados se paletizan y se entregan a Logistica Pacifico para distribucion internacional.",
    )

    #7. RECEPCION EN PUERTO
    execute_step(
        7,
        "Logistica_Pacifico",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.RECEIVED,
            "location": "Puerto de Los Angeles",
            "metadata": {"estado_aduanas": "LIBERADO"},
        },
        "Chequeo en Hub Logistico",
        "Logistica Pacifico escanea las cajas en el puerto. La liberacion de aduana queda registrada en los metadatos.",
    )

    #8. TRANSFERENCIA A ULTIMA MILLA
    execute_step(
        8,
        "Logistica_Pacifico",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.SHIPPED,
            "location": "Bahia de Carga 12",
            "receiver_name": "Flota_Camiones_Alfa",
        },
        "Transferencia a Camiones",
        "La carga se mueve del almacen a la Flota de Camiones Alfa para la entrega final al minorista.",
    )


    #9. TRANSITO TERRESTRE
    execute_step(
        9,
        "Flota_Camiones_Alfa",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.RECEIVED,
            "location": "Autopista 405 Sur",
            "metadata": {"chofer": "ID-442", "temp_c": "22.5"},
        },
        "Confirmacion de Transito",
        "La Flota confirma la recoleccion. Sensores IoT registran la temperatura durante el viaje.",
    )

    #10. ENTREGA FINAL
    execute_step(
        10,
        "Flota_Camiones_Alfa",
        {
            "shipment_id": finished_good_id,
            "action": ActionType.SHIPPED,
            "location": "Anden de Tienda",
            "receiver_name": "Mega_Tienda_Consumo",
        },
        "Entrega Final al Minorista",
        "El camion llega a la Mega Tienda. La propiedad se transfiere al minorista completando el ciclo.",
    )

    print("\n" + "=" * 80)
    print("SIMULACION COMPLETADA")
    print("=" * 80)
    print("Para verificar el Libro Mayor puedes correr:")
    print("  python view_blockchain.py")
    print("  desde la carpeta de cualquier nodo.")
    print("\nDeberias ver:")
    print(f"  1. Una transaccion CONSUMED para {raw_material_id}")
    print(f"  2. Una transaccion MANUFACTURED para {finished_good_id}")
    print(f"  3. Multiples eventos SHIPPED/RECEIVED rastreando la ruta.")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()