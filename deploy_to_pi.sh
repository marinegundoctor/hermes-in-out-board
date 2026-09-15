#!/bin/bash
PI_HOST="${PI_HOST:-100.86.49.97}"
PI_USER="${PI_USER:-root}"

echo "Starting deployment to Pi at ${PI_HOST}..."
echo "This script will automatically keep retrying until the connection is stable enough."

until rsync -avz --timeout=30 --exclude='.git' --exclude='data' --exclude='venv' --exclude='__pycache__' ./ "${PI_USER}@${PI_HOST}:~/in-out_board/"; do
    echo "[!] Connection dropped. Retrying in 5 seconds..."
    sleep 5
done

echo "[+] Sync successful! Recreating containers on the Pi..."
ssh -o ConnectTimeout=15 "${PI_USER}@${PI_HOST}" 'cd ~/in-out_board && sudo docker compose up -d && sudo docker compose restart'

if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "✅ SUCCESSFULLY DEPLOYED TO PI!"
    echo "=========================================="
else
    echo "Sync succeeded, but SSH failed to trigger the restart. Run this script again."
fi
