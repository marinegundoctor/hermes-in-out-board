# Hermes In/Out Board (Dockerized)

A modern, AI-powered digital In/Out board designed for professional environments (offices, military units, etc.). It features a clean web-based Kiosk display and uses a Telegram Bot ("Hermes") to process natural language status updates.

Instead of employees clicking buttons or using specific commands, they can simply message the bot conversationally (e.g., "Running late due to traffic, I'll be in around 0930"). The bot leverages Meta Llama 3.1 (via DeepInfra) to extract their status, location, and a professional comment, instantly updating the Kiosk display.

## Features
- **AI Natural Language Processing**: Powered by Llama 3.1 to strip conversational filler and extract structured data.
- **Real-time Kiosk Display**: A sleek, auto-updating web dashboard ideal for a TV or Raspberry Pi display monitor.
- **Telegram Integration**: Employees manage their status entirely through a secure Telegram bot.
- **Zero-Touch Setup**: Backend initializes dynamically. The web dashboard guides the administrator through the initial configuration.
- **Dockerized**: Deploy anywhere instantly using Docker Compose.

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
