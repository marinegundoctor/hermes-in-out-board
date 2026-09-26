# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
