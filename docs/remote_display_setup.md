# Remote Display & Kiosk Configuration Guide

This guide details how to set up and deploy secondary/remote kiosk displays (e.g., Orange Pi, Raspberry Pi, or any single-board computer running DietPi or minimal Linux) connected to the central Hermes In/Out Board.

---

## 1. Architecture Overview

```
       [ Upstream WAN / Wi-Fi / MiFi / LAN ]
                         │
                         ▼ (wlan0 or eth0)
              ┌─────────────────────┐
              │   Raspberry Pi 4    │ (Central Server - Docker)
              │  "ia-rrb-board"     │ Tailscale: 100.75.95.0
              └──────────┬──────────┘
                         │ (wlan1 - USB Wi-Fi AP)
                         ▼
             Hermes-Display-Net (SSID)
             Subnet: 10.42.0.0/24
             Gateway / Server: 10.42.0.1:8000
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌──────────────────┐           ┌──────────────────┐
│    Orange Pi     │           │   Secondary Pi   │
│  (Shop Display)  │           │ (Office Display) │
│   10.42.0.42     │           │   10.42.0.x      │
└──────────────────┘           └──────────────────┘
```

### Why an Isolated Display Network?
- **Air-Gapped Resilience**: If the facility loses internet connectivity, or the upstream Wi-Fi drops, the internal display network continues to function uninterrupted. Employees can still tap their badges, view statuses, and check who is in/out locally.
- **Dedicated Bandwidth**: Kiosk traffic does not contend with general office Wi-Fi traffic.
- **Zero-Touch Discovery**: Remote displays simply connect to `Hermes-Display-Net` and point their browser to `http://10.42.0.1:8000`.

---

## 2. Remote Display Client Setup (DietPi Kiosk)

DietPi is recommended for remote displays due to its minimal footprint and built-in autostart kiosk options.

### Step 1: Configure Chromium Kiosk
1. Install **Chromium** via `dietpi-software` (Software ID `113`).
2. Run `dietpi-autostart` and select **Chromium Kiosk** (Option `11`).
3. Set the target URL to the central Hermes server:
   ```text
   http://10.42.0.1:8000
   ```
   *(Alternatively, edit `/boot/dietpi.txt` and set `SOFTWARE_CHROMIUM_AUTOSTART_URL=http://10.42.0.1:8000`)*.

### Step 2: Install Universal Emoji Fonts
Because DietPi is heavily stripped down to save space, it does not include modern color emoji fonts. Any emojis typed in by users via the Telegram Bot or Custom Comment fields will render as square boxes with X's on the kiosk display.
To fix this, install the standard Noto Color Emoji package system-wide on the remote display device:
```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-color-emoji
```
Reboot the device or restart the Chromium process so it loads the new font cache.

---

## 3. Dynamic Resolution & Fullscreen Auto-Scaling (`kiosk.sh`)

### The Problem
DietPi's lightweight kiosk runs under bare X11 (`xinit`) without a Window Manager (like Openbox or Matchbox). 

Because there is no window manager to maximize windows, Chromium requires the `--window-size=X,Y` switch. Without it, Chromium defaults to a partial-screen window (often 960x1080 on the left half of the display). However, hardcoding a resolution breaks if you move the device between different monitors (e.g., from a 1080p desktop monitor to a 42" 4K TV in a workshop).

### The Solution: Hardware-Adaptive Wrapper
Create a wrapper script that dynamically queries the connected display's active resolution via `xrandr` before Chromium launches.

1. Create `/usr/local/bin/kiosk.sh`:
   ```bash
   sudo nano /usr/local/bin/kiosk.sh
   ```

2. Add the following script:
   ```bash
   #!/bin/bash
   # Query xrandr for active display mode (marked with '*')
   RES=$(xrandr | grep '*' | head -n 1 | awk '{print $1}')
   RES_X=$(echo $RES | cut -d 'x' -f 1)
   RES_Y=$(echo $RES | cut -d 'x' -f 2)

   # Fallback to standard 1080p if detection fails
   RES_X=${RES_X:-1920}
   RES_Y=${RES_Y:-1080}

   # Launch Chromium with dynamic size and forward all autostart arguments ("$@")
   exec /usr/bin/chromium --kiosk --window-size=${RES_X},${RES_Y} --window-position=0,0 "$@"
   ```

3. Make the wrapper executable:
   ```bash
   sudo chmod +x /usr/local/bin/kiosk.sh
   ```

4. Update DietPi's autostart script `/var/lib/dietpi/dietpi-software/installed/chromium-autostart.sh`:
   Replace the executable call from `/usr/bin/chromium` to `/usr/local/bin/kiosk.sh`.

Now, whenever the device boots or is plugged into a different screen, it automatically queries the EDID of the display and renders full-screen border-to-border.

---

## 4. Troubleshooting Tailscale on Filtered / Corporate Networks

If you install Tailscale on your remote display driver (Orange Pi, Pi Zero, etc.) so that it can be managed remotely on your Tailnet, you may run into an issue when running behind enterprise, guest, or military network connections.

### The Symptom
The remote display is connected to the internet through the host Pi's NAT (it can ping `8.8.8.8` and curl public websites), but Tailscale fails to connect:
```bash
root@orangepi:~# tailscale status
# Health check:
#     - You are logged out. The last login error was: fetch control key: Get "https://controlplane.tailscale.com/key?v=142": remote error: tls: handshake failure

unexpected state: NoState
```
In the Tailscale management console, the device remains stuck as **"Offline"** or **"Not Connected"**.

### The Root Cause: DNS Filtering & Sinkholing
Many enterprise and guest Wi-Fi networks enforce DNS filtering (e.g., **Cisco Umbrella / OpenDNS**, Palo Alto Networks, Fortinet). 
- These filters frequently categorize VPN and overlay network control servers (`controlplane.tailscale.com` and `login.tailscale.com`) as blocked (e.g., categorizing them as anonymizers or proxies).
- Instead of returning Tailscale's actual IP address, the network's DNS server returns a sinkhole or block-page IP (for example, OpenDNS returns `146.112.61.106` pointing to `hit-adult.opendns.com`).
- When the `tailscaled` daemon attempts an HTTPS handshake with `146.112.61.106`, it receives a TLS certificate for OpenDNS instead of `*.tailscale.com`. The SSL handshake immediately fails with `remote error: tls: handshake failure`.
- Because enterprise networks also block outbound UDP/TCP port 53 (dropping direct queries to `8.8.8.8` or `1.1.1.1`) and often block DNS-over-HTTPS (DoH) domains, standard DNS fallbacks will time out.

### The Fix: Hardcode Control Plane IPs in `/etc/hosts`
Because Tailscale uses Anycast IP addresses for its public control plane infrastructure, you can bypass local DNS interception by hardcoding Tailscale's Anycast IPs directly in the remote display's `/etc/hosts` file.

1. Open `/etc/hosts` on the remote display device:
   ```bash
   sudo nano /etc/hosts
   ```

2. Add static mappings for Tailscale's control and login endpoints:
   ```text
   # Tailscale Control Plane bypass for filtered/guest DNS
   192.200.0.116 controlplane.tailscale.com
   192.200.0.116 login.tailscale.com
   ```
   *(Note: Tailscale operates Anycast control plane nodes across the `192.200.0.101` through `192.200.0.116` range).*

3. Restart the Tailscale daemon:
   ```bash
   sudo systemctl restart tailscaled
   ```

4. Verify status:
   ```bash
   tailscale status
   ```
   The device will immediately establish a secure TLS handshake with the control plane, authenticate, and appear online on your Tailnet.

---

## 5. Host Pi Hotspot & NAT Reference

For reference, the central host Pi runs the following services to provide the `Hermes-Display-Net` network:

1. **`hostapd`** (`/etc/hostapd/hostapd.conf`):
   Binds to the secondary Wi-Fi adapter (e.g., `wlan1`), broadcasting SSID `Hermes-Display-Net` on WPA2-PSK.

2. **`dnsmasq`** (`/etc/dnsmasq.conf`):
   Serves DHCP on `wlan1` across `10.42.0.10` - `10.42.0.50` with subnet mask `255.255.255.0` and gateway `10.42.0.1`.

3. **IPv4 Forwarding & NAT**:
   - `net.ipv4.ip_forward=1` enabled in `/etc/sysctl.conf`.
   - `iptables` NAT masquerading rules:
     ```bash
     sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
     sudo iptables -A FORWARD -i wlan0 -o wlan1 -m state --state RELATED,ESTABLISHED -j ACCEPT
     sudo iptables -A FORWARD -i wlan1 -o wlan0 -j ACCEPT
     ```
   - Persisted via `iptables-persistent` or `netfilter-persistent save`.
