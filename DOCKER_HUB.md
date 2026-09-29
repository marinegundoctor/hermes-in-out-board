# 🪖 Hermes In/Out Board

<p align="center">
  <img src="https://raw.githubusercontent.com/marinegundoctor/hermes-in-out-board/main/assets/hermes_social_preview.jpg" alt="Hermes In/Out Board Banner" width="100%"/>
</p>

**A smart, AI-powered digital In/Out board for professional offices and military units.**

[![Version](https://img.shields.io/badge/version-v1.4.0-blue.svg)](https://github.com/marinegundoctor/hermes-in-out-board/releases)
[![GitHub](https://img.shields.io/badge/source-GitHub-black?logo=github)](https://github.com/marinegundoctor/hermes-in-out-board)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/marinegundoctor/hermes-in-out-board/blob/main/LICENSE)

---

Employees update their status conversationally through **The Office Bot** on Telegram — no apps, no forms, no buttons to hunt down. Just text naturally, like messaging a coworker.

> *"Heading to DEERS, back around 1400"* → ✅ **OUT** | Location: DEERS | Comment: Returning at 1400

A real-time **web kiosk dashboard** updates instantly for everyone in the office.

---

## ✨ Key Features

- 🤖 **Natural Language AI** — Two-tiered inference: fast `Llama-4-Scout-17B` (MoE) for everyday updates, powerful `Hermes-3 405B` for authenticated admin operations
- 📱 **The Office Bot (Telegram)** with role-aware quick-pick buttons (IN, OUT – Lunch, OUT – Meeting, etc.)
- 🖥️ **Live Web Kiosk Dashboard** — auto-refreshing, grouped by unit/team, dark-themed
- 🏷️ **Smart Card / CAC / RFID** tap-to-check-in/out support
- 👮 **Role System** — Users, Managers, and time-limited Admin sessions (15-min timeout)
- 📢 **Broadcast** — Managers/Admins can push announcements to all registered users
- ⏰ **EOD Auto-Checkout** — Cron job checks everyone out at 1800 automatically
- 🧮 **Relative Time Math** — "Back in 45 min" resolves to an actual military time
- 🌐 **DNS Resilient** — Containers use public DNS (8.8.8.8 / 1.1.1.1) directly
- 🔒 **Prompt Injection Hardened** — Jailbreak attempts are safely caught and deflected
- 📡 **Tailscale-Ready** — Designed for private network deployment (no public ports needed)

---

## 🗺️ Planned Features / Roadmap

- 🎛️ **Dedicated Touchscreen Admin Panel**: Transition the small touchscreen display from being a passive mirror of the in/out board to an interactive kiosk control console with a secure, on-screen Admin Panel mode.
- ⚙️ **Comprehensive Kiosk Administration**: Manage board configuration directly from the screen (beyond what's practical over Telegram), including user onboarding, rank adjustments, group creation, and custom group icon selection from a visual grid.
- 🎨 **Configurable Dashboard Branding**: Customize the dashboard title and unit headers directly in settings (e.g. dynamic organization naming and custom dashboard titles).
- 🔐 **Touchscreen API Authentication**: Add secure session tokens for write actions initiated from touchscreen kiosks.

---

## 🚀 Quick Start

This image provides the Python runtime and dependencies. Your app code and `.env` config live on the host alongside it.

**1. Clone the repo:**
```bash
git clone https://github.com/marinegundoctor/hermes-in-out-board.git
cd hermes-in-out-board
```

**2. Configure your environment:**
```bash
cp .env.example .env
nano .env  # Add your Telegram Bot Token and DeepInfra API Key
```

**3. Pull the image and start:**
```bash
docker compose pull
docker compose up -d
```

**4. Open the dashboard:**
```
http://localhost:8000
```

> ⚠️ A [Telegram Bot Token](https://core.telegram.org/bots/tutorial) and a [DeepInfra API Key](https://deepinfra.com/) are required for full functionality.

---

## 🏗️ Architecture

| Container | Purpose |
|---|---|
| `hermes_api` | FastAPI backend + SQLite DB + web dashboard |
| `hermes_bot` | Telegram long-polling bot + AI status parser |

Both containers share a mounted volume (your cloned repo directory) so your data persists and updates deploy instantly without rebuilding.

---

## 🔗 Links

- 📖 [Full Documentation & Setup Guide](https://github.com/marinegundoctor/hermes-in-out-board)
- 🐛 [Report an Issue](https://github.com/marinegundoctor/hermes-in-out-board/issues)
- 📋 [Changelog](https://github.com/marinegundoctor/hermes-in-out-board/blob/main/CHANGELOG.md)

---

*Built for the office. Tested in the field.*
