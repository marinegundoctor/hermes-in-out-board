#!/bin/bash
# wifi_watchdog.sh
# Monitors internet connection and forces failover to backup Wi-Fi networks if needed.
# This script is meant to be run as a background service on the host OS (e.g. Raspberry Pi),
# not inside a Docker container, as it requires direct access to wpa_cli.

PING_TARGET="8.8.8.8"
INTERFACE="wlan0"
CHECK_INTERVAL=20
MAX_FAILS=3

fails=0
disabled_net=""
disabled_time=0

echo "Starting Wi-Fi Watchdog on interface $INTERFACE..."

while true; do
    # Check if a network was disabled for more than 5 minutes (300s). If so, re-enable it.
    if [ ! -z "$disabled_net" ]; then
        current_time=$(date +%s)
        if [ $((current_time - disabled_time)) -gt 300 ]; then
            echo "Re-enabling network ID $disabled_net to retry primary connection..."
            wpa_cli -i $INTERFACE enable_network $disabled_net >/dev/null
            wpa_cli -i $INTERFACE reconnect >/dev/null
            disabled_net=""
            fails=-5 # Pause checks to allow reconnection
        fi
    fi

    # Check internet
    if ping -c 1 -W 3 $PING_TARGET >/dev/null 2>&1; then
        fails=0
    else
        fails=$((fails + 1))
        echo "Ping failed ($fails/$MAX_FAILS)"
        
        if [ $fails -ge $MAX_FAILS ]; then
            echo "Internet connection lost. Initiating Wi-Fi failover..."
            
            # Count configured networks
            net_count=$(wpa_cli -i $INTERFACE list_networks | tail -n +2 | wc -l)
            current_id=$(wpa_cli -i $INTERFACE status | grep "^id=" | cut -d= -f2)

            if [ "$net_count" -gt 1 ] && [ ! -z "$current_id" ]; then
                # Multiple networks exist. Disable current to force failover to backup.
                echo "Multiple networks configured. Disabling current network ID $current_id."
                if [ ! -z "$disabled_net" ]; then
                    wpa_cli -i $INTERFACE enable_network $disabled_net >/dev/null
                fi
                wpa_cli -i $INTERFACE disable_network $current_id >/dev/null
                disabled_net=$current_id
                disabled_time=$(date +%s)
                wpa_cli -i $INTERFACE reconnect >/dev/null
            else
                # Only 1 network (or disconnected). Just bounce the connection.
                echo "Only 1 network configured. Reassociating..."
                wpa_cli -i $INTERFACE reassociate >/dev/null
            fi
            
            fails=-3 # Pause checks to allow connection to stabilize
        fi
    fi
    sleep $CHECK_INTERVAL
done
