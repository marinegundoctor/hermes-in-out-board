# Hermes In/Out Board

A modern, AI-powered digital In/Out board designed for professional environments (offices, military units, etc.). It features a clean web-based Kiosk display and uses a Telegram Bot ("Hermes") to process natural language status updates.

Instead of employees clicking buttons or using specific commands, they can simply message the bot conversationally (e.g., "Running late due to traffic, I'll be in around 0930"). The bot leverages Meta Llama 3.1 (via DeepInfra, currently $0.02 per million tokens) to extract their status, location, and a professional comment, instantly updating the Kiosk display.

## Features
- **AI Natural Language Processing**: Powered by Llama 3.1 to strip conversational filler and extract structured data.
- **Real-time Kiosk Display**: A sleek, auto-updating web dashboard ideal for a TV or Raspberry Pi display monitor.
- **Telegram Integration**: Employees manage their status entirely through a secure Telegram bot.
- **Zero-Touch Setup**: Backend initializes dynamically. The web dashboard guides the administrator through the initial configuration.
- **Prompt Injection Protection**: The AI strictly validates user inputs and ignores off-topic chat or "jailbreak" attempts.

## Prerequisites
- Python 3.9+
- A [Telegram Bot Token](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) (from BotFather)
- A [DeepInfra](https://deepinfra.com/) API Key for Llama 3.1 inference
- SQLite (built into Python)

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/marinegundoctor/hermes-in-out-board.git
   cd hermes-in-out-board
   ```

2. **Create a virtual environment & install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set Environment Variables:**
   You must provide the application with your API keys. You can export them in your terminal or use a `.env` file (if you add `python-dotenv`).
   ```bash
   export TELEGRAM_TOKEN="your_telegram_token"
   export DEEPINFRA_API_KEY="your_deepinfra_key"
   ```

## Running the Application

The application consists of two parts running concurrently:

1. **The Web Dashboard (FastAPI):**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   *Visit `http://localhost:8000` to complete the initial setup.*

2. **The Telegram Bot (Hermes):**
   ```bash
   python telegram_bot.py
   ```

## Raspberry Pi / Kiosk Deployment (Systemd)

If you are running this on a Raspberry Pi, it is recommended to run the services via `systemd` to ensure they start on boot.

Create two service files in `/etc/systemd/system/`:

**1. `inout-api.service`**
```ini
[Unit]
Description=In/Out Board FastAPI Server
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/hermes-in-out-board
Environment="PATH=/home/pi/hermes-in-out-board/venv/bin"
ExecStart=/home/pi/hermes-in-out-board/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. `hermes-bot.service`**
```ini
[Unit]
Description=Hermes Telegram Bot
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/hermes-in-out-board
Environment="PATH=/home/pi/hermes-in-out-board/venv/bin"
Environment="TELEGRAM_TOKEN=your_telegram_token"
Environment="DEEPINFRA_API_KEY=your_deepinfra_key"
ExecStart=/home/pi/hermes-in-out-board/venv/bin/python telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start them:
```bash
sudo systemctl daemon-reload
sudo systemctl enable inout-api hermes-bot
sudo systemctl start inout-api hermes-bot
```

## Security Note
This project uses **Long Polling** (`getUpdates`) for the Telegram bot, meaning the backend reaches out to Telegram rather than exposing an inbound webhook. You can safely host this on a private network (like a Raspberry Pi behind a firewall or Tailscale) without exposing any ports to the public internet.
