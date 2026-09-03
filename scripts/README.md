# Wi-Fi Watchdog

This script monitors actual internet connectivity (by pinging 8.8.8.8) rather than just checking if the local Wi-Fi radio connection is alive. If the internet goes down, it will intelligently force `wpa_supplicant` to failover to your backup Wi-Fi network.

**Note:** This script is designed to run directly on the host operating system (e.g., Raspberry Pi OS, DietPi, Ubuntu), NOT inside a Docker container. Docker containers do not and should not have direct access to manage the host's physical Wi-Fi hardware.

## Features
- **SSID Agnostic**: It does not care what your network names or passwords are. It natively queries `wpa_supplicant` to see what networks you have configured.
- **Dynamic Failover**: If you have multiple networks configured (e.g., a primary Guest Wi-Fi and a backup MiFi), it will temporarily disable the broken network to force the system to connect to the backup. 
- **Auto-Recovery**: Every 5 minutes, it re-enables the primary network to check if it has come back online.
- **LAN Friendly**: If the system is connected via Ethernet, the pings will succeed over the wired connection, and the script will quietly do nothing.
- **Single-Network Safe**: If you only have one Wi-Fi network configured, it will simply bounce (reassociate) the connection to try and fix it, rather than disabling it entirely.

## Installation as a Background Service

You can set this script up to run automatically in the background using `systemd`.

1. **Make the script executable**:
   ```bash
   chmod +x scripts/wifi_watchdog.sh
   ```

2. **Create a systemd service file**:
   ```bash
   sudo nano /etc/systemd/system/wifi-watchdog.service
   ```

3. **Paste the following configuration** (adjust the `ExecStart` path to wherever you cloned this repository):
   ```ini
   [Unit]
   Description=Wi-Fi Internet Watchdog
   After=network.target

   [Service]
   Type=simple
   ExecStart=/home/margun/in-out_board/scripts/wifi_watchdog.sh
   Restart=on-failure
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable wifi-watchdog.service
   sudo systemctl start wifi-watchdog.service
   ```

5. **Check the logs** to verify it is running:
   ```bash
   sudo journalctl -u wifi-watchdog.service -f
   ```
