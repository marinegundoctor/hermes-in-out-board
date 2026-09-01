#!/bin/bash
echo "Starting deployment to Pi at 100.75.95.0..."
echo "This script will automatically keep retrying until the 4G connection is stable enough."

until rsync -avz --timeout=15 --exclude='.git' --exclude='data' ./ margun@100.75.95.0:~/in-out_board/; do
    echo "[!] Connection dropped. Retrying in 5 seconds..."
    sleep 5
done

echo "[+] Sync successful! Recreating containers on the Pi..."
ssh -o ConnectTimeout=15 margun@100.75.95.0 'cd ~/in-out_board && sudo docker compose up -d && sudo docker compose restart'

if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "✅ SUCCESSFULLY DEPLOYED TO PI!"
    echo "=========================================="
else
    echo "Sync succeeded, but SSH failed to trigger the restart. Run this script again."
fi
