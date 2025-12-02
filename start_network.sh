#!/bin/bash

# Map of Node Names to Ports
declare -A nodes
nodes=(
  ["Truck_Fleet_Alpha"]=5001
  ["TechFoundry_Inc"]=5002
  ["Pacific_Logistics"]=5003
  ["OPEC_Supplier"]=5004
  ["Mega_Consumer_Goods"]=5005
  ["GlobalMining_Corp"]=5006
  ["FreightTrain_Express"]=5007
  ["Drone_Delivery_X"]=5008
  ["Corner_Store"]=5009
  ["CleanWater_Services"]=5010
  ["CargoShip_EverGiven"]=5011
)

echo "--- Deploying and Starting Network ---"

# Check if source files exist
if [ ! -f "p2p.py" ] || [ ! -f "blockchain_core.py" ]; then
  echo "Error: p2p.py or blockchain_core.py not found in current directory."
  exit 1
fi

for folder in "${!nodes[@]}"; do
  port=${nodes[$folder]}
  target_dir="nodes/$folder"

  if [ -d "$target_dir" ]; then
    echo "[*] Updating $folder..."

    # Copy latest code to node folder so they all have the fixes
    cp p2p.py "$target_dir/"
    cp blockchain_core.py "$target_dir/"

    echo "    Starting on port $port..."
    # Run in background, redirect logs
    (cd "$target_dir" && python3 p2p.py --port $port >node.log 2>&1 &)
  else
    echo "[!] Warning: Directory $target_dir not found."
  fi
done

echo "--- Network Started ---"
echo "Logs are located in each node's folder (e.g., nodes/Truck_Fleet_Alpha/node.log)"
