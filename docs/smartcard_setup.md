# Smart Card / CAC / RFID Reader Setup Guide

This guide details how to configure and deploy physical smart card (CAC/PIV/RFID) badge readers with the Hermes In/Out Board.

---

## 1. Overview & Architecture

Employees can check in and out simply by tapping their ID badge or Common Access Card (CAC) against a contactless reader plugged into the kiosk.

```
┌─────────────────────────────────────────────────────────────┐
│                      Host Hardware                          │
│                                                             │
│   ┌──────────────────┐               ┌──────────────────┐   │
│   │  OMNIKEY 5422    │  (USB)        │ Keychron / USB   │   │
│   │ Smartcard Reader │               │ Keyboard         │   │
│   └────────┬─────────┘               └────────┬─────────┘   │
│            │ (PC/SC CCID)                     │ (X11 Focus) │
│            ▼                                  │             │
│   ┌────────────────────────────────┐          │             │
│   │ hermes-card-reader.service     │          │             │
│   │ (pyscard + APDU UID Reader)    │          │             │
│   └────────┬───────────────────────┘          │             │
│            │ HTTP POST /api/scans/pending     │             │
│            │ + xdotool windowactivate         │             │
│            ▼                                  ▼             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Chromium Kiosk Display 1 (1280x800 Touchscreen)     │   │
│   │ - Interactive Touch Tiles + Keyboard Key Badges     │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Highlights
- **Sub-Second Debounce & Rapid Re-Carding**: Physical contactless bounce is debounced at 1.2s; the backend action cooldown is 1.5s. This completely eliminates accidental double-taps while allowing users to immediately card again without waiting through an artificial 5+ second freeze.
- **Instant Clock-IN**: When an employee who is marked `OUT` taps their badge, the kiosk immediately registers them `IN`, displays a green confirmation badge for 1.2 seconds, and auto-dismisses.
- **Touchscreen + Keyboard Dual Usability**: When an employee who is marked `IN` taps their badge, a Check OUT modal appears featuring large, touch-friendly tiles with prominent keyboard shortcut badges. The employee can either press a number key on the keyboard **or** tap the screen directly with a finger.
- **Automatic Window Focus**: Tapping a card immediately triggers an X11 window activation (`xdotool`) targeting the kiosk browser, ensuring keyboard keystrokes are received even in dual-monitor setups.

---

## 2. Hardware Requirements

- **Smart Card Reader**: HID OMNIKEY 5422 Dual-Interface USB Reader (or any PC/SC CCID compliant smart card reader like the ACR122U or Identiv SCR3310).
- **Cards**: Standard contactless ISO/IEC 14443 Type A badges (including DoD CAC contactless chips, PIV cards, and Mifare/NFC tags).
- **Host Machine**: Raspberry Pi 5 (or Pi 4 / Linux SBC) running DietPi or Debian/Ubuntu.

---

## 3. Host System Packages & Prerequisites

Install the PC/SC smartcard daemon, development libraries, and python wrapper on the host OS:

```bash
sudo apt-get update
sudo apt-get install -y pcscd pcsc-tools libpcsclite1 python3-pyscard xdotool
```

### Verify Reader Hardware
Ensure `pcscd` is active and the reader is recognized:

```bash
sudo systemctl enable --now pcscd
pcsc_scan
```
*Output should show your reader (e.g. `HID Global OMNIKEY 5422 Smart Card Reader`) and detect when a card is presented, printing its ATR (Answer to Reset).*

---

## 4. Configuring `card_reader.py` as a System Service

The background card monitoring script lives at `card_reader.py`. It runs natively on the host OS to access USB PC/SC devices and communicate with the local Hermes API.

1. **Create the systemd service file**:
   ```bash
   sudo nano /etc/systemd/system/hermes-card-reader.service
   ```

2. **Paste the following configuration**:
   ```ini
   [Unit]
   Description=Hermes Smartcard Reader Service
   After=pcscd.service docker.service
   Wants=pcscd.service

   [Service]
   Type=simple
   User=root
   Environment="DISPLAY=:0"
   WorkingDirectory=/root/in-out_board
   ExecStart=/usr/bin/python3 /root/in-out_board/card_reader.py
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   ```
   *(Note: Adjust `WorkingDirectory` and `ExecStart` if your repository is located in a directory other than `/root/in-out_board`).*

3. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now hermes-card-reader.service
   ```

4. **Check status and logs**:
   ```bash
   sudo systemctl status hermes-card-reader.service
   journalctl -u hermes-card-reader.service -f
   ```

---

## 5. User Interaction & Control Scheme

### Clock IN Flow
1. Employee taps their badge against the reader.
2. The reader queries the chip's Unique Identifier (UID) using the standard ISO 14443-A APDU `[0xFF, 0xCA, 0x00, 0x00, 0x00]`.
3. If the user is currently `OUT`:
   - The screen immediately shows: **"Welcome Back, [Name]! Setting status to IN..."**
   - The API records status `in`, location `--`, and comment `--`.
   - The confirmation displays for 1.2s before auto-dismissing and refreshing the board.

### Check OUT Flow (Dual Usability)
If the user is currently `IN`, tapping their badge opens the **Check OUT** modal:

```
┌────────────────────────────────────────────────────────┐
│ Check OUT: SSG Dixon                   [X Cancel (ESC)]│
│                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │ [1] 🍔 LUNCH          │   │ [2] 📦 SUPPLY         │ │
│  └───────────────────────┘   └───────────────────────┘ │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │ [3] 🏢 JFHQ           │   │ [4] 🖧 G6             │ │
│  └───────────────────────┘   └───────────────────────┘ │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │ [5] 📅 LEAVE          │   │ [6] ✈️ TDY            │ │
│  └───────────────────────┘   └───────────────────────┘ │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │ [7] ✏️ Free Text       │   │ [0] 🌙 End of Day     │ │
│  └───────────────────────┘   └───────────────────────┘ │
│                                                        │
│  Tap screen or press 1-7, 0, Enter     Auto-submitting │
│  on keyboard                           in 7s...        │
└────────────────────────────────────────────────────────┘
```

| Key | Option | Behavior |
|:---:|:---|:---|
| `1` | **LUNCH** | Instantly clocks OUT to `Lunch` with comment `--`. |
| `2` | **SUPPLY** | Prompts: Add comment? (`Y` opens comment field, `Enter` skips to `--`). |
| `3` | **JFHQ** | Prompts for optional comment. |
| `4` | **G6** | Prompts for optional comment. |
| `5` | **LEAVE** | Prompts for optional comment. |
| `6` | **TDY** | Prompts for optional comment. |
| `7` | **Free Text** | Opens custom Location (required) and Comment (optional) text inputs. |
| `0` / `Enter` | **End of Day** | Default sign out: status `out`, location `--`, comment `--`. |
| `ESC` | **Cancel** | Immediately dismisses modal with zero status change. |

**Touch Alternative**: Every button on screen is fully touch-responsive. Users can tap the tile directly with a finger or use a physical keyboard.

---

## 6. First-Time Card Registration Flow

When a user taps an unrecognized badge:
1. The kiosk displays: **"New Card Detected. Please enter your Work Email to link your account"**.
2. The user types their email address (using the physical keyboard or the on-screen virtual keyboard) and presses **Enter**.
3. **If email matches an existing user**:
   - The card ID is linked to their record in `inout.db`.
   - The user is clocked `IN`.
4. **If email is not found**:
   - The kiosk prompts for **Rank** (optional) and **Full Name** (required).
   - The user selects an organization group.
   - A new user profile is created, linked to the card, and clocked `IN`.

---

## 7. Troubleshooting & Diagnostics

### Debouncing & Cooldown
- If a card is held against the reader for an extended period, the reader software ignores duplicate reads within **1.2 seconds**.
- Once a checkout action is submitted, the API imposes a **1.5 second** protection period on that card ID to prevent contact bounce from immediately clocking the user back in.

### Keyboard Keystrokes Not Registering
In dual-monitor kiosk setups, ensure that:
1. `/usr/local/bin/kiosk.sh` launches Display 2 first and Display 1 second.
2. `xdotool` is installed: `sudo apt-get install -y xdotool`.
3. Openbox `/etc/xdg/openbox/rc.xml` includes the focus prevention rule:
   ```xml
   <application class="*chromium-display2*">
     <focus>no</focus>
   </application>
   <application class="*chromium-display1*">
     <focus>yes</focus>
   </application>
   ```
4. Verify window class names with:
   ```bash
   DISPLAY=:0 xdotool getactivewindow
   DISPLAY=:0 xprop -id $(DISPLAY=:0 xdotool getactivewindow) WM_CLASS
   ```
