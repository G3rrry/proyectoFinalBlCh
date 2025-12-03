#!/bin/bash

#Mapa de nombres de nodos a puertos
declare -A nodes
nodes=(
  ["Flota_Camiones_Alfa"]=5001
  ["Fabrica_Tech_Inc"]=5002
  ["Logistica_Pacifico"]=5003
  ["Proveedor_Petroleo"]=5004
  ["Mega_Tienda_Consumo"]=5005
  ["Mina_Global_Corp"]=5006
  ["Tren_Carga_Express"]=5007
  ["Drones_Entrega_X"]=5008
  ["Tiendita_Esquina"]=5009
  ["Servicios_Agua_Limpia"]=5010
  ["Barco_Carga_EverGiven"]=5011
)

echo "--- Desplegando e Iniciando la Red ---"

#verificamos que los archivos existan
if [ ! -f "p2p.py" ] || [ ! -f "blockchain_core.py" ]; then
  echo "Error: p2p.py o blockchain_core.py no encontrados en este directorio."
  exit 1
fi

for folder in "${!nodes[@]}"; do
  port=${nodes[$folder]}
  target_dir="nodes/$folder"

  if [ -d "$target_dir" ]; then
    echo "[*] Actualizando $folder..."


    #RUBRICA: Metodo de Distribucion
    #Copiamos el codigo mas reciente a la carpeta del nodo para asegurar uniformidad
    cp p2p.py "$target_dir/"
    cp blockchain_core.py "$target_dir/"

    echo "    Iniciando en puerto $port..."
    #Ejecutamos en segundo plano (background) y redirigimos logs
    (cd "$target_dir" && python3 p2p.py --port $port >node.log 2>&1 &)
  else
    echo "[!] Advertencia: La carpeta $target_dir no existe."
  fi
done

echo "--- Red Iniciada Exitosamente ---"
echo "Los logs estan en la carpeta de cada nodo (ej. nodes/Flota_Camiones_Alfa/node.log)"