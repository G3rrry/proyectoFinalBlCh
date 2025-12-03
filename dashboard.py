import streamlit as st
import pandas as pd
import requests
import os
import sys
import time
import random
import sqlite3
import json
from ecdsa import SigningKey, SECP256k1

#Agregamos directorio actual
sys.path.append(os.getcwd())
from blockchain_core import Transaction, ActionType

st.set_page_config(
    page_title="SupplyChain Ledger",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stDeployButton {display:none;}
    div.block-container{padding-top:2rem;}
    </style>
""", unsafe_allow_html=True)

#CONFIGURACIÓN DE RED
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

#FUNCIONES AUXILIARES

def get_node_key(node_name):
    #Buscamos la llave privada en la carpeta del nodo
    key_path = os.path.join("nodes", node_name, "private_key.pem")
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            priv = f.read().strip()
        sk = SigningKey.from_string(bytes.fromhex(priv), curve=SECP256k1)
        return priv, sk.verifying_key.to_string().hex()
    return None, None

def get_db_connection(node_name):
    #Conexion directa a la base de datos SQL del nodo
    db_path = os.path.join("nodes", node_name, "blockchain.db")
    return sqlite3.connect(db_path)

def send_transaction(node_name, tx_obj, private_key_hex):
    #Firmamos y mandamos la peticion HTTP
    tx_obj.sign_transaction(private_key_hex)
    
    port = PEERS[node_name]
    url = f"http://localhost:{port}/transaction"
    payload = tx_obj.to_dict()
    payload["signature"] = tx_obj.signature
    
    try:
        resp = requests.post(url, json=payload, timeout=2)
        return resp.status_code, resp.json()
    except Exception as e:
        return 500, {"message": str(e)}



with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2091/2091665.png", width=60) 
    st.title("Panel de Nodo")
    st.markdown("---")
    
    #Selector de usuario
    st.write("👤 **Identidad Actual**")
    selected_node = st.selectbox("Selecciona tu Nodo", list(PEERS.keys()), label_visibility="collapsed")
    
    #Cargamos credenciales
    priv_key, pub_key = get_node_key(selected_node)

    if not priv_key:
        st.error(" Error crítico: No se encontró la llave privada. ¿Corriste el setup?")
        st.stop() 


    st.success(f"🟢 **En línea**\n\nPuerto: `{PEERS[selected_node]}`")
    
    st.markdown("---")
    st.caption(f"ID Público (Hash):\n{pub_key[:15]}...")
    st.caption("Proyecto Final Blockchain v1.0")

#INTERFAZ PRINCIPAL

st.title("📦 Sistema de Trazabilidad Blockchain")
st.markdown(f"Bienvenido, **{selected_node.replace('_', ' ')}**. Aquí puedes gestionar tus activos y validar bloques.")

#Pestañas principales
tab1, tab2, tab3 = st.tabs(["🛠️ Operaciones", "🔗 Explorador de Bloques", "📊 Estadísticas de Red"])

#PESTAÑA 1: OPERACIONES
with tab1:
    st.write("#### Gestión de Activos")
    
    col_izq, col_der = st.columns([1, 2])
    
    with col_izq:

        st.info("Selecciona la acción a realizar en la red:")
        action = st.radio(
            "Tipo de Operación",
            ["Extraer Recursos", "Manufacturar", "Enviar", "Votar"],
            label_visibility="collapsed"
        )

    with col_der:
        container = st.container(border=True)
        
        if action == "Extraer Recursos":
            container.subheader("⛏️ Registrar Nueva Extracción")
            
            conn = get_db_connection(selected_node)
            try:
                goods = pd.read_sql("SELECT * FROM goods", conn)
                good_sel = container.selectbox("Recurso", goods["name"] + " (" + goods["unit_of_measure"] + ")")
                good_id = goods[goods["name"] == good_sel.split(" (")[0]]["good_id"].values[0]
            except:
                container.error("No se pudo leer la tabla de bienes.")
                good_id = None
            conn.close()
            
            c1, c2 = container.columns(2)
            qty = c1.number_input("Cantidad", min_value=1.0, value=100.0)
            loc = c2.text_input("Ubicación", "Mina Principal")
            
            if container.button("Firmar y Registrar en Blockchain", use_container_width=True):
                new_id = f"SHIP-{random.randint(10000, 99999)}"
                tx = Transaction(pub_key, pub_key, new_id, ActionType.EXTRACTED, loc, good_id, qty)
                code, res = send_transaction(selected_node, tx, priv_key)
                
                if code == 201:
                    st.toast(f"✅ Recurso creado con ID: {new_id}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Error: {res}")

        elif action == "Enviar":
            container.subheader("🚚 Enviar Mercancía")
            
            conn = get_db_connection(selected_node)
            inv = pd.read_sql(f"SELECT shipment_id, quantity FROM shipments WHERE current_owner_pk='{pub_key}' AND is_active=1", conn)
            conn.close()
            
            if inv.empty:
                container.warning("⚠️ Tu inventario está vacío. No puedes enviar nada.")
            else:
                ship_sel = container.selectbox("Selecciona Lote", inv["shipment_id"] + " | Cant: " + inv["quantity"].astype(str))
                ship_id = ship_sel.split(" |")[0]
                
                receivers = [p for p in PEERS.keys() if p != selected_node]
                dest = container.selectbox("Destinatario", receivers)
                
                #Obtenemos la PK del destino
                conn = get_db_connection(selected_node)
                dest_pk = conn.execute("SELECT public_key FROM participants WHERE name=?", (dest,)).fetchone()[0]
                conn.close()
                
                new_loc = container.text_input("Nueva Ubicación (Destino)", "En Tránsito")
                
                if container.button("Firmar Envío", use_container_width=True):
                    tx = Transaction(pub_key, dest_pk, ship_id, ActionType.SHIPPED, new_loc)
                    code, res = send_transaction(selected_node, tx, priv_key)
                    if code == 201:
                        st.toast("✅ Transacción enviada a la Mempool.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error: {res}")

        elif action == "Manufacturar":
            container.subheader("🏭 Procesamiento / Manufactura")
            container.info("Nota: Esta es una versión simplificada para la demo.")
            
            prod_name = container.text_input("Producto Resultante", "Batería de Litio")
            qty_prod = container.number_input("Cantidad Producida", 10.0)
            
            if container.button("Registrar Producción", use_container_width=True):
                new_id = f"PROD-{random.randint(1000,9999)}"
                
                tx = Transaction(pub_key, pub_key, new_id, ActionType.MANUFACTURED, "Fábrica Central", "GENERICO", qty_prod)
                code, res = send_transaction(selected_node, tx, priv_key)
                if code == 201:
                    st.success("Producción registrada exitosamente.")
                else:
                    st.error(f"Error: {res}")

        elif action == "Votar":
            container.subheader("🗳️ Consenso DPoS")
            container.write("Elige al nodo validador de confianza.")
            
            candidates = [p for p in PEERS.keys()]
            vote_for = container.selectbox("Candidato", candidates)
            
            #Buscamos la PK del candidato
            conn = get_db_connection(selected_node)
            cand_pk = conn.execute("SELECT public_key FROM participants WHERE name=?", (vote_for,)).fetchone()[0]
            conn.close()
            
            if container.button("Emitir Voto", use_container_width=True):
                tx = Transaction(pub_key, cand_pk, f"VOTE-{int(time.time())}", ActionType.VOTE, "Urna Virtual")
                code, res = send_transaction(selected_node, tx, priv_key)
                if code == 201:
                    st.balloons() 
                    st.success("Voto registrado.")
                else:
                    st.error(f"Error: {res}")

#PESTAÑA 2: EXPLORADOR 
with tab2:
    col_head, col_btn = st.columns([4, 1])
    col_head.write("#### Libro Mayor Inmutable (Ledger)")
    if col_btn.button("🔄 Refrescar"):
        st.rerun()

    try:
        #Intentamos conectar al nodo
        port = PEERS[selected_node]
        chain_res = requests.get(f"http://localhost:{port}/chain", timeout=1)
        
        if chain_res.status_code == 200:
            chain_data = chain_res.json()
            
            st.metric("Altura de la Cadena (Bloques)", len(chain_data))
            
            #Mostramos los bloques del más nuevo al más viejo
            for block in reversed(chain_data):

                icon = "⛓️" if block['index'] > 0 else "🥚"
                
                with st.expander(f"{icon} Bloque #{block['index']} | Validador: {block['validator'][:15]}..."):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Hash:** `{block['hash']}`")
                    c1.markdown(f"**Prev Hash:** `{block['previous_hash']}`")
                    c2.markdown(f"**Merkle Root:** `{block['merkle_root'][:20]}...`")
                    c2.markdown(f"**Timestamp:** {time.ctime(block['timestamp'])}")
                    
                    st.markdown("##### Transacciones")
                    if not block['transactions']:
                        st.caption("Bloque vacío (Heartbeat)")
                    else:
                        df_tx = pd.DataFrame(block['transactions'])

                        cols_to_show = ["action", "shipment_id", "sender", "receiver", "quantity"]
                        cols_final = [c for c in cols_to_show if c in df_tx.columns]
                        st.dataframe(df_tx[cols_final], use_container_width=True)
        else:
            st.warning("El nodo respondió pero con error.")
            
    except Exception as e:
        st.error(f"❌ No hay conexión con el nodo {selected_node}.")
        st.info("Tip: Abre la terminal y ejecuta 'python start_network.py'")

#PESTAÑA 3: ESTADO DEL MUNDO
with tab3:
    st.write("#### Estado Global de la Red")
    
    #Conexion para sacar datos
    conn = get_db_connection(selected_node)
    
    #Queries
    inventory_df = pd.read_sql("SELECT * FROM shipments WHERE is_active=1", conn)
    votes_df = pd.read_sql("SELECT name, votes, role FROM participants ORDER BY votes DESC", conn)
    
    #Mapeo de PK a Nombres para que se entienda
    parts = conn.execute("SELECT public_key, name FROM participants").fetchall()
    participant_map = {pk: name for pk, name in parts}
    conn.close()
    

    m1, m2, m3 = st.columns(3)
    m1.metric("Envíos Activos", len(inventory_df))
    m2.metric("Nodos Participantes", len(parts))
    m3.metric("Líder Actual (Más Votos)", votes_df.iloc[0]['name'] if not votes_df.empty else "N/A")
    
    st.divider()

    col_inv, col_votes = st.columns([2, 1])
    
    with col_inv:
        st.subheader("📦 Inventario Mundial")
        if not inventory_df.empty:
            #Reemplazamos las llaves raras por nombres
            inventory_df["Dueño"] = inventory_df["current_owner_pk"].map(participant_map)
            
            #Tabla limpia
            st.dataframe(
                inventory_df[["shipment_id", "quantity", "Dueño", "current_location"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("La cadena está vacía. ¡Crea el primer recurso!")

    with col_votes:
        st.subheader("📊 Tabla de Votos")