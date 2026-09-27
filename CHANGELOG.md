# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-09-27

### Added
- **Two-Tiered AI Inference**: Implemented a tiered model routing system. Normal user and manager requests are handled by `meta-llama/Llama-4-Scout-17B-16E-Instruct` (fast MoE model) while authenticated Admin requests are routed to the full `NousResearch/Hermes-3-Llama-3.1-405B` for higher-reasoning tasks.
- **Relative Time Math**: The AI system prompt is now injected with the current server time on every request. Phrases like "i'll be back in 45 min" are converted to an absolute military time (e.g., `Returning at 0145`), rounded to the nearest 5 minutes.
- **Chain-of-Thought Time Reasoning**: Added a `reasoning` scratchpad field to the AI's JSON schema so the model writes out its arithmetic before producing the final comment, eliminating hallucination/anchoring bugs on relative-time calculations.
- **Broadcast Prompt Mode**: Clicking the `/broadcast` button with no message now enters a waiting state and prompts the Manager/Admin to type their broadcast message. `/cancel` exits the mode cleanly.
- **DNS Resilience**: Both Docker containers (`hermes_api` and `hermes_bot`) are now explicitly configured to use Google (`8.8.8.8`) and Cloudflare (`1.1.1.1`) public DNS, making the system immune to local office DNS outages.

### Changed
- **Traffic Accident Phrasing**: AI prompt updated to rephrase messages involving accidents as "Delayed by traffic" to avoid implying the user was personally in an accident.
- **"Dead" Location Easter Egg**: Locations containing the word "dead" now render with a ☠️ skull-crossbones icon on the dashboard.
- **Skull Icon Fix**: Corrected icon mapping to `fa-skull-crossbones` for the "dead to us" location easter egg.

### Fixed
- Fixed a Python f-string syntax error (`Invalid format specifier`) in `hermes_ai.py` caused by unescaped curly braces in the JSON schema portion of the system prompt after it was converted to an f-string.
- Fixed a bot crash loop caused by the local network's DNS resolver going down while the physical internet connection remained functional.

### Security
- **Prompt Injection Hardening**: The AI correctly rejects jailbreak attempts such as "forget all previous instructions" by routing them to the `ignore` action, falling back to the help menu.

## [1.2.1] - 2026-09-26

### Added
- **Manager Role**: Introduced a permanent Manager role that sits between normal users and Admins. Managers can update the board announcement, alter other users' statuses and groups, and send broadcasts.
- **Dynamic Keyboards**: Telegram buttons now dynamically update based on the user's role (User, Manager, or Admin) so normal users only see relevant buttons.
- **Role Management Commands**: Admins can promote users via `/promote <email> <manager/user>`, and Managers can explicitly set a user's group via `/set_group <email> <group>`.

## [1.2.0] - 2026-09-26

### Added
- **Interactive Telegram Buttons**: Added `ReplyKeyboardMarkup` to send persistent inline buttons for quick status updates (IN, OUT - Lunch, OUT - Meeting, etc.) without typing.
- **End-of-Day Auto-Checkout**: Added a cron-like task in the bot that runs at 1800 daily to automatically check out users who are still marked "IN" to `OUT - EOD`. Does not overwrite custom locations.
- **Roll Call Command**: Admins can use `/rollcall` to get a grouped, timestamped summary of all users' current statuses for accountability and emergency musters.
- **Cancel Command**: Added `/cancel` command to allow users to exit the onboarding flow or group confirmation prompts cleanly.

### Changed
- **Llama 3.1 70B Upgrade**: Upgraded the AI model from 8B to 70B for vastly improved logic processing and natural language understanding.
- **Admin Timeout**: Admin sessions via `/admin <PIN>` now automatically expire after 15 minutes of inactivity to prevent permanent privilege escalation.
- **Admin AI Bypass**: Unauthorized status modification attempts for *other* users are now safely caught by the bot script rather than the AI prompt, allowing more graceful rejection notices.

### Fixed
- Fixed an issue where the bot help menu would not distinguish between admin and standard users when using natural language queries.
- Cleaned up SQLite timezone discrepancies by ensuring local container time is explicitly parsed for user accountability reports.

## [1.1.0] - 2026-09-15

### Added
- Smart Card / CAC / RFID support via `card_reader.py` integration.
- Touchscreen and capacitive UI improvements.
- Network connection watchdog and UI status indicators.

## [1.0.0] - Initial Release

### Added
- Core In/Out board functionality.
- Basic Telegram Bot implementation.
- Kiosk mode UI with local SQLite persistence.
