import os
import random
import sqlite3
import sys
import time
import requests


# Agregamos el directorio actual para poder importar nuestros modulos
sys.path.append(os.getcwd())

# Importamos las clases necesarias que controlan la logica de la blockchain
from blockchain_core import BlockchainNode, Transaction, ActionType


# Lista de los nodos y sus puertos para saber a donde conectarnos
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


def get_identity():
    # Esta funcion lee el nombre de la carpeta y carga la clave privada del archivo
    current_dir = os.getcwd()
    node_name = os.path.basename(current_dir)
    key_path = "private_key.pem"

    if not os.path.exists(key_path):
        return None, None

    with open(key_path, "r") as f:
        private_key = f.read().strip()
    return node_name, private_key


def get_node_port(node_name):
    # Buscamos el puerto que le corresponde al nodo
    return PEERS.get(node_name, 5000)


def select_from_menu(items, title, formatter):
    # Funcion auxiliar para mostrar menus y que el usuario elija una opcion
    if not items:
        print(f"\n {title} \n  (No hay elementos disponibles)")
        input("Presiona Enter para volver...")
        return None
    while True:
        print(f"\n {title} ")
        for i, item in enumerate(items, 1):
            print(f"{i}. {formatter(item)}")
        print("B. Volver")

        choice = input("\nSelecciona una opcion: ").strip().lower()
        if choice == "b":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            else:
                print("Seleccion invalida.")
        except ValueError:
            print("Por favor ingresa un numero.")


def main():
    # Cargamos la identidad del nodo y su llave privada para poder firmar despues
    node_name, priv_key = get_identity()
    if not node_name:
        print("Error: No se encontro private_key.pem o la identidad del nodo.")
        return

    # Configuramos la conexion local
    my_port = get_node_port(node_name)
    base_url = f"http://localhost:{my_port}"

    db_path = "blockchain.db"
    # Iniciamos el nodo en modo lectura para consultar datos de la base de datos
    node = BlockchainNode(node_name, db_path)

    # Obtenemos nuestra clave publica que servira como nuestra direccion
    sender_pub = node.get_public_key_by_name(node_name)

    if not sender_pub:
        print(
            f"Error: La clave publica para {node_name} no se encontro en la base de datos."
        )
        return

    while True:
        print(f"\n{'=' * 40}")
        print(f" BILLETERA DE {node_name.upper()} (Puerto {my_port})")
        print(f"{'=' * 40}")
        print("1. Extraer Recursos      (E)")
        print("2. Manufacturar Bienes   (M)")
        print("3. Enviar Mercancia      (S)")
        print("4. Destruir Mercancia    (D)")
        print("5. Votar por Delegado    (V)")
        print("6. Salir                 (Q)")
        print(f"{'-' * 40}")

        choice = input("Selecciona una Accion: ").upper().strip()

        if choice in ["6", "Q"]:
            print("Saliendo...")
            break
        txs = []

        # Opcion 1 Extraer recursos crea nuevos bienes en el sistema
        if choice in ["1", "E"]:
            with sqlite3.connect(db_path) as conn:
                goods = conn.execute(
                    "SELECT good_id, name, unit_of_measure FROM goods"
                ).fetchall()

            print("\n[ Extraer Nuevos Recursos ]")
            sel = select_from_menu(
                goods, "Selecciona Tipo de Recurso", lambda x: f"{x[1]} ({x[0]})"
            )
            if sel:
                try:
                    qty = float(input(f"Cantidad ({sel[2]}): "))
                    loc = input("Ubicacion Actual: ")

                    new_ship_id = f"SHIP-{random.randint(10000, 99999)}"

                    # Creamos la transaccion para registrar la extraccion del recurso
                    txs.append(
                        Transaction(
                            sender_pub,
                            sender_pub,
                            new_ship_id,
                            ActionType.EXTRACTED,
                            loc,
                            sel[0],
                            qty,
                        )
                    )
                    print(f"   -> En cola: Extraer {qty} {sel[1]}")
                except ValueError:
                    print("Cantidad invalida.")

        # Opcion 2 Manufacturar consume insumos y crea un producto nuevo
        elif choice in ["2", "M"]:
            print("\n[ Manufacturar Bienes ]")

            # Paso 1 Seleccionamos que materiales vamos a usar del inventario
            print(" Paso 1: Seleccionar Materiales de Entrada ")
            processing_inputs = []

            while True:
                with sqlite3.connect(db_path) as conn:
                    selected_ids = [i["id"] for i in processing_inputs]
                    # Buscamos solo los envios activos que nos pertenecen
                    query = "SELECT shipment_id, g.name, s.quantity, g.unit_of_measure, g.good_id FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=? AND s.is_active=1"

                    if selected_ids:
                        placeholders = ",".join("?" for _ in selected_ids)
                        query += f" AND s.shipment_id NOT IN ({placeholders})"
                        params = (sender_pub, *selected_ids)
                    else:
                        params = (sender_pub,)

                    ships = conn.execute(query, params).fetchall()

                if not ships:
                    if not processing_inputs:
                        print("  (No tienes inventario activo disponible)")
                        break
                    print("  (No hay mas items disponibles)")
                    break

                sel = select_from_menu(
                    ships,
                    "Tu Inventario",
                    lambda x: f"{x[0]} - {x[1]} ({x[2]} {x[3]})",
                )
                if not sel:
                    break

                current_qty = sel[2]
                try:
                    use_qty = float(input(f"Cantidad a usar (Max {current_qty}): "))
                    if use_qty <= 0 or use_qty > current_qty:
                        print(f"Error: Tienes {current_qty} pero ingresaste {use_qty}.")
                        continue

                    processing_inputs.append(
                        {
                            "id": sel[0],
                            "name": sel[1],
                            "total": current_qty,
                            "used": use_qty,
                            "good_id": sel[4],
                            "unit": sel[3],
                        }
                    )
                    print(f"   -> Agregado {use_qty} de {sel[1]} a los insumos.")

                    if input("Agregar otro insumo? (S/n): ").lower() == "n":
                        break
                except ValueError:
                    print("Numero invalido.")
                    continue

            if not processing_inputs:
                continue

            # Paso 2 Definimos que producto vamos a crear con esos insumos
            print("\n Paso 2: Definir Producto de Salida ")
            with sqlite3.connect(db_path) as conn:
                goods = conn.execute(
                    "SELECT good_id, name, unit_of_measure FROM goods"
                ).fetchall()

            out_sel = select_from_menu(
                goods, "Selecciona Producto Final", lambda x: f"{x[1]} ({x[0]})"
            )
            if not out_sel:
                continue

            try:
                out_qty = float(input(f"Cantidad Producida ({out_sel[2]}): "))
                prod_loc = input("Ubicacion de Produccion: ")

                input_ids = []

                # Actualizamos los insumos para marcarlos como consumidos o reducidos
                for item in processing_inputs:
                    input_ids.append(item["id"])
                    remaining = item["total"] - item["used"]

                    if remaining == 0:
                        # Si se usa todo marcamos como consumido
                        txs.append(
                            Transaction(
                                sender_pub,
                                sender_pub,
                                item["id"],
                                ActionType.CONSUMED,
                                "Consumido en Manufactura",
                                metadata={"product": out_sel[1]},
                            )
                        )
                    else:
                        # Si sobra actualizamos la cantidad restante
                        txs.append(
                            Transaction(
                                sender_pub,
                                sender_pub,
                                item["id"],
                                ActionType.RECEIVED,
                                prod_loc,
                                item["good_id"],
                                remaining,
                            )
                        )

                # Creamos la transaccion del producto nuevo vinculando los insumos usados
                new_product_id = f"SHIP-{random.randint(10000, 99999)}"
                txs.append(
                    Transaction(
                        sender_pub,
                        sender_pub,
                        new_product_id,
                        ActionType.MANUFACTURED,
                        prod_loc,
                        out_sel[0],
                        out_qty,
                        metadata={"source_materials": input_ids},
                    )
                )

                print(
                    f"\nResumen: Consumiendo {len(processing_inputs)} insumos -> Creando {out_qty} {out_sel[1]}"
                )

            except ValueError:
                print("Cantidad de salida invalida.")
                continue

        # Opcion 3 Enviar mercancia transfiere la propiedad a otro nodo
        elif choice in ["3", "S"]:
            with sqlite3.connect(db_path) as conn:
                ships = conn.execute(
                    "SELECT shipment_id, g.name, s.current_location FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=? AND s.is_active=1",
                    (sender_pub,),
                ).fetchall()
            print("\n[ Enviar Mercancia ]")
            sel = select_from_menu(
                ships, "Tu Inventario", lambda x: f"{x[0]} - {x[1]} en {x[2]}"
            )
            if sel:
                with sqlite3.connect(db_path) as conn:
                    partners = conn.execute(
                        "SELECT name, role FROM participants WHERE name != ?",
                        (node_name,),
                    ).fetchall()

                rec = select_from_menu(
                    partners, "Selecciona Receptor", lambda x: f"{x[0]} ({x[1]})"
                )
                if rec:
                    rec_pub = node.get_public_key_by_name(rec[0])
                    loc = input("Nueva Ubicacion: ")

                    # Generamos la transaccion de envio cambiando el propietario
                    txs.append(
                        Transaction(
                            sender_pub, rec_pub, sel[0], ActionType.SHIPPED, loc
                        )
                    )

        # Opcion 4 Destruir mercancia la retira del inventario activo
        elif choice in ["4", "D"]:
            with sqlite3.connect(db_path) as conn:
                ships = conn.execute(
                    "SELECT shipment_id, g.name FROM shipments s JOIN goods g ON s.good_id=g.good_id WHERE s.current_owner_pk=? AND s.is_active=1",
                    (sender_pub,),
                ).fetchall()
            print("\n[ Destruir Mercancia ]")
            sel = select_from_menu(
                ships, "Selecciona Item a Destruir", lambda x: f"{x[0]} ({x[1]})"
            )
            if sel:
                reason = input("Razon: ")
                txs.append(
                    Transaction(
                        sender_pub,
                        sender_pub,
                        sel[0],
                        ActionType.DESTROYED,
                        "Destruido",
                        metadata={"reason": reason},
                    )
                )

        # Opcion 5 Votar por delegado genera una transaccion especial de voto
        elif choice in ["5", "V"]:
            with sqlite3.connect(db_path) as conn:
                partners = conn.execute(
                    "SELECT name, votes FROM participants WHERE name != ? ORDER BY votes DESC",
                    (node_name,),
                ).fetchall()

            print("\n[ Votar por Delegado ]")
            rec = select_from_menu(
                partners, "Candidatos", lambda x: f"{x[0]} (Votos actuales: {x[1]})"
            )
            if rec:
                cand_pub = node.get_public_key_by_name(rec[0])
                # Creamos la transaccion de voto
                txs.append(
                    Transaction(
                        sender_pub,
                        cand_pub,
                        f"VOTE-{int(time.time())}",
                        ActionType.VOTE,
                        "Boleta Electoral",
                    )
                )

        # Procesamiento de las transacciones generadas para enviarlas a la red
        if txs:
            print(f"\nProcesando {len(txs)} transaccion(es)...")

            for i, tx in enumerate(txs, 1):
                # Hacemos una revision local basica antes de intentar enviar
                is_valid_logic, error_msg = node.validate_smart_contract_rules(tx)
                if not is_valid_logic:
                    print(f"    [!] Tx {i}/{len(txs)} FALLO CHEQUEO LOCAL: {error_msg}")
                    continue

                # Aqui aplicamos la firma digital usando nuestra clave privada para asegurar que somos nosotros
                if tx.sign_transaction(priv_key):
                    # Preparamos los datos y adjuntamos la firma generada
                    payload = tx.to_dict()
                    payload["signature"] = tx.signature

                    try:
                        # Enviamos la transaccion al nodo local mediante HTTP
                        resp = requests.post(
                            f"{base_url}/transaction", json=payload, timeout=2
                        )
                        if resp.status_code == 201:
                            print(
                                f"    [+] Tx {i}/{len(txs)} Transmitida exitosamente ({tx.action})"
                            )
                        else:
                            print(
                                f"    [!] Tx {i}/{len(txs)} Rechazada por el Nodo: {resp.text}"
                            )
                    except requests.exceptions.ConnectionError:
                        print(
                            f"    [X] Error: No se pudo conectar a {base_url} esta corriendo p2p?"
                        )
                else:
                    print(f"    [!] Tx {i}/{len(txs)} Fallo al Firmar.")

            input("\nLote completado. Presiona Enter para volver al menu...")


if __name__ == "__main__":
    main()

