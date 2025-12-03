#!/bin/bash

echo "--- Deteniendo la Red Blockchain ---"


#Buscamos los IDs de los procesos de python que estan ejecutando p2p.py
pids=$(pgrep -f "p2p.py")

if [ -z "$pids" ]; then
  echo "No hay nodos corriendo."
else
  echo "Matando procesos: $pids"
  kill $pids
  echo "Todos los nodos se detuvieron."
fi