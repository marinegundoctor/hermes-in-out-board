# Hermes In/Out Board (Dockerized)

A modern, AI-powered digital In/Out board designed for professional environments (offices, military units, etc.). It features a clean web-based Kiosk display and uses a Telegram Bot ("Hermes") to process natural language status updates.

Instead of employees clicking buttons or using specific commands, they can simply message the bot conversationally (e.g., "Running late due to traffic, I'll be in around 0930"). The bot leverages Meta Llama 3.1 8B Instruct Turbo (via DeepInfra) which is extremely low cost (around $0.02 per 1M tokens in, $0.04 per 1M tokens out) to extract their status, location, and a professional comment, instantly updating the Kiosk display.

## Features
- **Smart Card / CAC / Badge Integration**: Employees can simply tap their ID badge or CAC to check in/out instantly at the Kiosk. Supports HID OMNIKEY 5422, ACR122U, and all standard PC/SC CCID compliant readers with sub-second debounce protection. See [docs/smartcard_setup.md](docs/smartcard_setup.md).
- **Touchscreen & Keyboard Dual Usability**: The kiosk interface supports both physical keyboards (Keychron K1 Pro / standard USB keyboards with keys 1-7, 0, Enter, ESC) AND direct capacitive touch controls with large interactive tiles, on-screen keyboard (`simple-keyboard`), and touch-optimized date/time pickers (`flatpickr`).
- **Real-time Dual-Screen Kiosk Display**: A sleek, auto-updating web dashboard. The host Raspberry Pi simultaneously drives an interactive touch display for employee check-ins and an external display (e.g. facing an office window) with Openbox window focus isolation.
- **Backend Internet Watchdog**: The Python backend continuously monitors upstream connectivity and roundtrip latency using captive portal probes, driving live connection health indicators (Online, Degraded, Offline) uniformly across all connected screens.
- **Telegram Integration**: Employees manage their status conversationally through a secure Telegram bot ("Hermes") powered by Meta Llama 3.1 8B Instruct Turbo.
- **Zero-Touch Setup**: Backend initializes dynamically. The web dashboard guides the administrator through initial configuration.
- **Dockerized**: Deploy anywhere instantly using Docker Compose.

## Optional OS-Level Features & Architecture
- **Smart Card Reader Service**: A lightweight Python service running on the host OS (`card_reader.py`) that monitors smart card insertions via `pyscard`, reads ISO 14443-A UIDs, routes status updates to the local API, and guarantees X11 kiosk window focus. See [docs/smartcard_setup.md](docs/smartcard_setup.md) for complete hardware and systemd setup.
- **Dual-Screen Host Kiosk**: The primary host Pi runs a customized X11 Openbox session that outputs the touch-interactive kiosk UI (`?view=kiosk`) to a 10" touchscreen display while running an independent Chromium instance on an external monitor for public viewing. Includes window rules to prevent the public display from stealing keyboard focus. See [docs/remote_display_setup.md](docs/remote_display_setup.md).
- **Wi-Fi Watchdog**: Includes a host-level script (`scripts/wifi_watchdog.sh`) for advanced setups requiring resilient Wi-Fi internet failover (e.g. Guest Wi-Fi with MiFi backup). See [scripts/README.md](scripts/README.md).
- **Remote Kiosk Displays (Hermes Display Net)**: Connect secondary displays (Orange Pi, Raspberry Pi, or any single-board computer running DietPi or minimal Linux) across shops or hallways over an isolated local hotspot (`Hermes-Display-Net`). Features dynamic display auto-scaling and Tailscale bypass techniques for filtered corporate networks. See [docs/remote_display_setup.md](docs/remote_display_setup.md).

## Prerequisites
- Docker and Docker Compose
- A [Telegram Bot Token](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) (from BotFather)
- A [DeepInfra](https://deepinfra.com/) API Key for Llama 3.1 inference

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/marinegundoctor/hermes-in-out-board.git
   cd hermes-in-out-board
   ```

2. **Configure Environment Variables:**
   Copy the example environment file and add your actual API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your favorite text editor
   nano .env
   ```

3. **Start the Application:**
   Run the following command to build the image and start both the API and the Telegram Bot in the background:
   ```bash
   docker-compose up -d
   ```

4. **Access the Dashboard:**
   Visit `http://localhost:8000` (or the IP of your host machine) to complete the initial setup and view the board!

## Data Persistence
The `docker-compose.yml` automatically mounts a `./data` folder in the project directory. Your `inout.db` database is securely stored here and will persist across container restarts or server reboots.

## Security Note
This project uses **Long Polling** (`getUpdates`) for the Telegram bot, meaning the backend reaches out to Telegram rather than exposing an inbound webhook. You can safely host this on a private network (like a Raspberry Pi behind a firewall or Tailscale) without exposing any ports to the public internet.
