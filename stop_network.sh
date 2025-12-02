#!/bin/bash

echo "--- Stopping Blockchain Network ---"

# Find PIDs of python processes running p2p.py
pids=$(pgrep -f "p2p.py")

if [ -z "$pids" ]; then
  echo "No nodes running."
else
  echo "Killing processes: $pids"
  kill $pids
  echo "All nodes stopped."
fi
