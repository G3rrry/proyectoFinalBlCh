import sqlite3
import time
import os
import sys

#Agregamos el directorio actual para importar las clases del nucleo
sys.path.append(os.getcwd())
from blockchain_core import BlockchainNode


def view_local_ledger():
    #Esta funcion lee la base de datos local y muestra el estado completo de la blockchain
    current_dir = os.getcwd()
    node_name = os.path.basename(current_dir)
    db_file = "blockchain.db"

    if not os.path.exists(db_file):
        print(f"Error: No se encontro la base de datos en {current_dir}")
        return

    node = BlockchainNode(node_name, db_file)


    print("\n" + "=" * 100)
    print(f"[{node_name.upper()}] LIBRO MAYOR INMUTABLE (Consenso DPoS)")
    print("=" * 100)


    #Cargamos toda la cadena de bloques
    chain = node.load_chain()
    if not chain:
        print("(Cadena Vacia)")
    else:
        for block in chain:
            print(f"\n[ BLOQUE #{block.index} ]")
            print(f"Marca de Tiempo : {time.ctime(block.timestamp)}")
            print(f"Validador       : {block.validator}")
            print(f"Hash del Bloque : {block.hash}")
            print(f"Hash Anterior   : {block.previous_hash}")
            print(f"Raiz de Merkle  : {block.merkle_root}")
            print(f"Transacciones   : {len(block.transactions)}")
            print("-" * 50)

            if not block.transactions:
                print("   (Sin transacciones)")

            for tx in block.transactions:
                s = node.get_name_by_public_key(tx.sender)

                if tx.action == "VOTE":
                    c = node.get_name_by_public_key(tx.receiver)
                    print(f"   > [VOTO]        {s} voto por el candidato {c}")

                elif tx.action == "DESTROYED":
                    reason = tx.metadata.get("reason", "Desconocida")
                    print(f"   > [DESTRUIDO]   {tx.shipment_id} eliminado por {s}")
                    print(f"                   Razon: {reason}")

                elif tx.action == "CONSUMED":
                    product = tx.metadata.get("product", "Bienes")
                    print(f"   > [CONSUMIDO]   {tx.shipment_id} usado por {s}")
                    print(f"                   Insumo para: {product}")

                elif tx.action in ["EXTRACTED", "MANUFACTURED"]:
                    verb = "extrajo" if tx.action == "EXTRACTED" else "manufacturo"
                    print(f"   > [CREADO]      {s} {verb} {tx.shipment_id}")
                    print(
                        f"                   {tx.quantity} {tx.good_id} en {tx.location}"
                    )
                    if (
                        tx.action == "MANUFACTURED"
                        and "source_materials" in tx.metadata
                    ):
                        print(
                            f"                   Fuentes: {tx.metadata['source_materials']}"
                        )


                elif tx.action == "SHIPPED":
                    r = node.get_name_by_public_key(tx.receiver)
                    print(f"   > [ENVIADO]     {tx.shipment_id} movido de {s} -> {r}")
                    print(f"                   Hacia: {tx.location}")

                elif tx.action == "RECEIVED":
                    print(f"   > [RECIBIDO]    {s} confirmo/actualizo {tx.shipment_id}")
                    print(f"                   En: {tx.location}")
                    if tx.quantity:
                        print(f"                   Cantidad Actualizada: {tx.quantity}")

                print(f"                   [TxID: {tx.tx_hash[:16]}...]")

            print("=" * 100)

    #Seccion de Consenso DPoS
    print("\n" + "*" * 40 + " TABLA DE POSICIONES (VOTOS) " + "*" * 40)
    print(f"{'Candidato':<30} | {'Votos':<10} | {'Estado'}")
    print("-" * 60)


    conn = sqlite3.connect(node.db_file)
    delegates = conn.execute(
        "SELECT name, votes FROM participants ORDER BY votes DESC"
    ).fetchall()

    for i, (name, votes) in enumerate(delegates):
        status = "VALIDADOR ACTIVO" if i < 3 else "En Espera"
        prefix = " --(Activo)-- " if i < 3 else "  "
        print(f"{prefix}{name:<28} | {votes:<10} | {status}")

    #Seccion de Trazabilidad (Estado del Mundo)
    print("\n" + "#" * 40 + " ESTADO DEL MUNDO (Inventario Activo) " + "#" * 40)
    print(
        f"{'ID Envio':<18} | {'Bien':<15} | {'Cant':<12} | {'Propietario':<20} | {'Ubicacion':<15} | {'Ultima Accion'}"
    )
    print("-" * 100)

    #Filtramos solo lo que esta activo is_active = 1
    rows = conn.execute(
        """
        SELECT s.shipment_id, g.name, s.quantity, g.unit_of_measure, s.current_owner_pk, s.current_location, s.last_action
        FROM shipments s 
        JOIN goods g ON s.good_id = g.good_id
        WHERE s.is_active = 1
        ORDER BY s.last_updated_timestamp DESC
        """
    ).fetchall()
    conn.close()


    if not rows:
        print("(No hay envios activos en el estado del mundo)")
    else:
        for row in rows:
            sh, g_name, qty, unit, own_pk, loc, action = row
            own = node.get_name_by_public_key(own_pk)
            qty_str = f"{qty} {unit}"
            print(
                f"{sh:<18} | {g_name[:15]:<15} | {qty_str:<12} | {own[:20]:<20} | {loc[:15]:<15} | {action}"
            )

    print("\n")


if __name__ == "__main__":
    view_local_ledger()