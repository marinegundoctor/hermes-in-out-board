import time
import requests
import sqlite3
import os
import json
import uuid
from hermes_ai import parse_status_message, parse_onboarding_name
from rank_utils import get_sort_weight

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
DB_FILE = os.environ.get("DB_PATH", "inout.db")

waiting_for_comment = {} # {chat_id: {"timestamp": ...}}
onboarding_state = {} # {chat_id: {"step": "name", "name": "", "email": ""}}
group_confirm_state = {} # {chat_id: {"requested_group": "xyz", "is_onboarding": bool}}
broadcast_state = {} # {chat_id: True}

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def setup_db():
    with get_db() as conn:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN telegram_chat_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN group_name TEXT DEFAULT 'Unassigned'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE app_settings ADD COLUMN admin_pin TEXT DEFAULT '211212'")
        except sqlite3.OperationalError:
            pass
        
        # Clear all admin sessions on restart
        conn.execute("UPDATE users SET is_admin = 0")
        conn.commit()

def send_message(chat_id, text, use_keyboard=True):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if use_keyboard:
        user = get_user_by_chat_id(chat_id)
        is_admin = dict(user).get("is_admin", False) if user else False
        
        role = dict(user).get("role", "user") if user else "user"
        if is_admin:
            kb = [
                [{"text": "IN"}, {"text": "OUT - EOD"}],
                [{"text": "OUT - Lunch"}, {"text": "OUT - Meeting"}],
                [{"text": "/rollcall"}, {"text": "/users"}],
                [{"text": "/admin_help"}, {"text": "/admin_logout"}]
            ]
        elif role == "manager":
            kb = [
                [{"text": "IN"}, {"text": "OUT - EOD"}],
                [{"text": "OUT - Lunch"}, {"text": "OUT - Meeting"}],
                [{"text": "/rollcall"}, {"text": "/broadcast"}],
                [{"text": "Help"}]
            ]
        else:
            kb = [
                [{"text": "IN"}, {"text": "OUT - EOD"}],
                [{"text": "OUT - Lunch"}, {"text": "OUT - Meeting"}],
                [{"text": "Help"}]
            ]
            
        payload["reply_markup"] = {
            "keyboard": kb,
            "resize_keyboard": True,
            "is_persistent": True
        }
    requests.post(url, json=payload)

def delete_message(chat_id, message_id):
    url = f"{BASE_URL}/deleteMessage"
    requests.post(url, json={"chat_id": chat_id, "message_id": message_id})

def get_user_by_chat_id(chat_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_chat_id = ?", (str(chat_id),)).fetchone()

def get_all_groups():
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT group_name FROM users WHERE group_name IS NOT NULL").fetchall()
        return [r[0] for r in rows]


last_eod_date = None
admin_timeouts = {}
admin_auth_state = {}

def run_eod_reset():
    with get_db() as conn:
        conn.execute("UPDATE users SET status = 'out', location = '--', comment = 'EOD Auto-checkout', last_updated = CURRENT_TIMESTAMP WHERE status = 'in'")
        conn.commit()
    print("EOD Auto-checkout ran successfully.")

def check_timeouts():
    global last_eod_date
    now = time.time()
    
    # 1. Comment Timeouts
    to_remove = []
    for chat_id, state in waiting_for_comment.items():
        if now - state["timestamp"] > 300:
            send_message(chat_id, "⏱️ Okay, no comment added.")
            to_remove.append(chat_id)
    for chat_id in to_remove:
        del waiting_for_comment[chat_id]
        
    # 2. Admin Timeouts
    expired_admins = []
    for chat_id, expire_time in admin_timeouts.items():
        if now > expire_time:
            expired_admins.append(chat_id)
    for chat_id in expired_admins:
        user = get_user_by_chat_id(chat_id)
        if user and dict(user).get("is_admin"):
            with get_db() as conn:
                conn.execute("UPDATE users SET is_admin = 0 WHERE id = ?", (user["id"],))
                conn.commit()
            send_message(chat_id, "🔒 **Admin Session Expired.** You have been reverted to a normal user. (15-minute timeout)")
        del admin_timeouts[chat_id]
        
    # 3. EOD Reset
    local_time = time.localtime(now)
    current_date = f"{local_time.tm_year}-{local_time.tm_mon}-{local_time.tm_mday}"
    if local_time.tm_hour >= 18 and last_eod_date != current_date:
        run_eod_reset()
        last_eod_date = current_date

def create_account(chat_id, email, name, group_name, rank="", sort_weight=None):
    if sort_weight is None or sort_weight == 50:
        sort_weight = get_sort_weight(rank)
    uid = str(uuid.uuid4())[:8]
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
        if existing:
            conn.execute("UPDATE users SET telegram_chat_id = ?, name = ?, group_name = ?, rank = ?, sort_weight = ? WHERE id = ?", 
                         (str(chat_id), name, group_name, rank, sort_weight, existing["id"]))
        else:
            conn.execute("""
                INSERT INTO users (email, name, uid, telegram_chat_id, group_name, rank, sort_weight, status, location, comment) 
                VALUES (?, ?, ?, ?, ?, ?, ?, 'out', '--', '--')
            """, (email, name, uid, str(chat_id), group_name, rank, sort_weight))
        conn.commit()

def process_message(chat_id, text, message_id):
    global waiting_for_comment, onboarding_state, group_confirm_state, admin_auth_state, broadcast_state
    
    user = get_user_by_chat_id(chat_id)
    text_clean = text.strip()

    # Handle pending admin auth
    if chat_id in admin_auth_state:
        del admin_auth_state[chat_id]
        delete_message(chat_id, message_id)  # Mask the PIN by deleting it immediately
        
        # Clear any pending interactive states
        if chat_id in waiting_for_comment: del waiting_for_comment[chat_id]
        if chat_id in group_confirm_state: del group_confirm_state[chat_id]
        if chat_id in onboarding_state: del onboarding_state[chat_id]
        
        with get_db() as conn:
            settings = conn.execute("SELECT admin_pin FROM app_settings WHERE id = 1").fetchone()
            admin_pin = settings["admin_pin"] if settings else "211212"
            
        if text_clean == admin_pin:
            if not user: return # Cannot be admin without an account
            with get_db() as conn:
                conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user["id"],))
                admin_timeouts[chat_id] = __import__("time").time() + 900
                conn.commit()
            send_message(chat_id, "🔓 **Admin Mode Activated!** (15-minute timeout)\n\nYou now have access to advanced commands. Type `/admin_help` to see them.")
        else:
            send_message(chat_id, "❌ Incorrect PIN.")
        return


    role = dict(user).get("role", "user") if user else "user"
    is_manager = dict(user).get("is_admin", False) or role == "manager"
    
    # Handle pending broadcast message
    if chat_id in broadcast_state:
        del broadcast_state[chat_id]
        if text_clean.lower() == "/cancel":
            send_message(chat_id, "✅ Broadcast cancelled.")
            return
            
        msg = text_clean
        sender_rank = dict(user).get("rank", "").strip()
        sender_name = user['name']
        sender_display = f"{sender_rank} {sender_name}".strip()
        b_msg = f"📢 **BROADCAST FROM {sender_display}**\n\n{msg}"
        with get_db() as conn:
            chats = conn.execute("SELECT telegram_chat_id FROM users WHERE telegram_chat_id IS NOT NULL").fetchall()
        count = 0
        for c in chats:
            try:
                send_message(c["telegram_chat_id"], b_msg)
                count += 1
            except Exception as e:
                pass
        send_message(chat_id, f"✅ Broadcast sent to {count} users.")
        return
    if text_clean.lower().startswith("/promote "):
        if not dict(user).get("is_admin"): 
            send_message(chat_id, "❌ Only Admins can promote users.")
            return
        parts = text_clean.split(" ", 2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: `/promote <email> <manager/user>`")
            return
        target_email, new_role = parts[1], parts[2].lower()
        if new_role not in ["manager", "user"]:
            send_message(chat_id, "Role must be 'manager' or 'user'.")
            return
        with get_db() as conn:
            conn.execute("UPDATE users SET role = ? WHERE email = ? COLLATE NOCASE", (new_role, target_email))
            conn.commit()
        send_message(chat_id, f"✅ User `{target_email}` has been updated to role: **{new_role}**")
        return

    if text_clean.lower().startswith("/set_group "):
        if not is_manager: 
            send_message(chat_id, "❌ Only Managers or Admins can explicitly set groups.")
            return
        parts = text_clean.split(" ", 2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: `/set_group <email> <group_name>`")
            return
        target_email, new_group = parts[1], parts[2]
        with get_db() as conn:
            conn.execute("UPDATE users SET group_name = ? WHERE email = ? COLLATE NOCASE", (new_group, target_email))
            conn.commit()
        send_message(chat_id, f"✅ User `{target_email}` moved to group: **{new_group}**")
        return

    if text_clean.lower() == "/cancel":
        if chat_id in onboarding_state:
            del onboarding_state[chat_id]
        if chat_id in group_confirm_state:
            del group_confirm_state[chat_id]
        if chat_id in waiting_for_comment:
            del waiting_for_comment[chat_id]
        if chat_id in broadcast_state:
            del broadcast_state[chat_id]
        send_message(chat_id, "✅ Action cancelled. I'm listening for status updates.")
        return

    if text_clean.lower() == "/rollcall":
        if not is_manager: 
            send_message(chat_id, "❌ Only Managers or Admins can perform a roll call.")
            return
        with get_db() as conn:
            users = conn.execute("SELECT name, status, location, datetime(last_updated, 'localtime') as local_time, group_name FROM users ORDER BY group_name, name").fetchall()
        if not users:
            send_message(chat_id, "No users found.")
            return
        
        from collections import defaultdict
        groups = defaultdict(list)
        for u in users:
            groups[u['group_name']].append(dict(u))
            
        msg = "📋 **Roll Call / Accountability Report**\n\n"
        for group_name, members in groups.items():
            msg += f"**{group_name}**\n"
            for u in members:
                time_str = u['local_time']
                if time_str:
                    parts = time_str.split(" ")
                    date_parts = parts[0].split("-")
                    time_parts = parts[1].split(":")
                    time_str = f"{date_parts[1]}/{date_parts[2]} {time_parts[0]}:{time_parts[1]}"
                loc = f" ({u['location']})" if u['status'] == 'out' else ""
                msg += f"• {u['name']}: {u['status'].upper()}{loc} _[{time_str}]_\n"
            msg += "\n"
        send_message(chat_id, msg)
        return


    if text_clean.lower() == "/admin_help":
        admin_help = (
            "🛠️ **The Office Bot Admin Commands**\n\n"
            "`/rollcall` - Grouped accountability report\n"
            "`/users` - List all registered users (Name, Email, Status)\n"
            "`/promote <email> <manager/user>` - Set a user's role (Admin ONLY)\n"
            "`/remove_user <email>` - Delete a user completely\n"
            "`/remove_group <group>` - Delete a group (moves members to 'Unassigned')\n"
            "`/set_group <email> <group>` - Move user to a group (Manager+)\n"
            "`/set_status <email> <in/out> <location>` - Force update someone's status (Manager+)\n"
            "`/broadcast <message>` - Send a Telegram message to ALL users (Manager+)\n"
            "`/reset_all` - Force all users to OUT (Admin ONLY)\n"
            "`/admin_logout` - De-elevate back to your default role\n\n"
            "*Plus, you can now use natural language to remove users/groups, move members, promote users, and change the PIN, Org Name, or Group Order!*"
        )
        send_message(chat_id, admin_help)
        return

    if text_clean.lower() == "/admin_logout":
        if not dict(user).get("is_admin"):
            send_message(chat_id, "❌ You are not currently in Admin Mode.")
            return
        with get_db() as conn:
            conn.execute("UPDATE users SET is_admin = 0 WHERE id = ?", (user["id"],))
            conn.commit()
        send_message(chat_id, "🔒 **Admin Mode Deactivated.**")
        return

    if text_clean.lower().startswith("/admin"):
        # Clear any pending interactive states
        if chat_id in waiting_for_comment: del waiting_for_comment[chat_id]
        if chat_id in group_confirm_state: del group_confirm_state[chat_id]
        if chat_id in onboarding_state: del onboarding_state[chat_id]

        # If they type `/admin` with no PIN, ask for it
        parts = text_clean.split(" ")
        if len(parts) == 1:
            admin_auth_state[chat_id] = {"timestamp": __import__("time").time()}
            send_message(chat_id, "🔒 Please enter your Admin PIN.\n*(Your next message will be automatically deleted for security).*")
            return
            
        # If they passed the PIN in the command (e.g. `/admin 211212`)
        delete_message(chat_id, message_id) # Delete it immediately so it doesn't show in chat history!
        
        with get_db() as conn:
            settings = conn.execute("SELECT admin_pin FROM app_settings WHERE id = 1").fetchone()
            admin_pin = settings["admin_pin"] if settings else "211212"
            
        pin = parts[1]
        if pin == admin_pin:
            if not user: return
            with get_db() as conn:
                conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user["id"],))
                admin_timeouts[chat_id] = __import__("time").time() + 900
                conn.commit()
            send_message(chat_id, "🔓 **Admin Mode Activated!** (15-minute timeout)\n\nYou now have access to advanced commands. Type `/admin_help` to see them.")
        else:
            send_message(chat_id, "❌ Incorrect PIN.")
        return

    if text_clean.lower() == "/users":
        if not dict(user).get("is_admin"): return
        with get_db() as conn:
            users = conn.execute("SELECT name, email, group_name FROM users ORDER BY group_name, name").fetchall()
        if not users:
            send_message(chat_id, "No users found.")
            return
            
        from collections import defaultdict
        groups = defaultdict(list)
        for u in users:
            groups[u['group_name'] or 'Unassigned'].append(dict(u))
            
        msg = "📋 **All Registered Users**\n\n"
        for group_name, members in groups.items():
            msg += f"**{group_name}**\n"
            for u in members:
                msg += f"• {u['name']} ({u['email']})\n"
            msg += "\n"
            
        send_message(chat_id, msg.strip())
        return

    if text_clean.lower().startswith("/remove_user"):
        if not dict(user).get("is_admin"): 
            send_message(chat_id, "❌ Only Admins can remove users.")
            return
        parts = text_clean.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "ℹ️ Usage: `/remove_user <email or name>`")
            return
        target_identifier = parts[1].strip()
        with get_db() as conn:
            target = conn.execute(
                "SELECT id, name, email FROM users WHERE email = ? COLLATE NOCASE OR name LIKE ? COLLATE NOCASE",
                (target_identifier, f"%{target_identifier}%")
            ).fetchone()
            if not target:
                send_message(chat_id, f"❌ No user found matching `{target_identifier}`.")
                return
            conn.execute("DELETE FROM users WHERE id = ?", (target["id"],))
            conn.commit()
        send_message(chat_id, f"🗑️ User **{target['name']}** (`{target['email']}`) has been removed.")
        return

    if text_clean.lower().startswith("/remove_group"):
        if not dict(user).get("is_admin"): 
            send_message(chat_id, "❌ Only Admins can remove groups.")
            return
        parts = text_clean.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "ℹ️ Usage: `/remove_group <group_name>`")
            return
        group = parts[1].strip()
        with get_db() as conn:
            conn.execute("DELETE FROM groups WHERE name = ? COLLATE NOCASE", (group,))
            conn.execute("UPDATE users SET group_name = 'Unassigned' WHERE group_name = ? COLLATE NOCASE", (group,))
            conn.commit()
        send_message(chat_id, f"🗑️ Group **{group}** removed. Any members have been moved to 'Unassigned'.")
        return

    if text_clean.lower().startswith("/set_status "):
        if not is_manager: return
        parts = text_clean.split(" ")
        if len(parts) < 3:
            send_message(chat_id, "ℹ️ Usage: `/set_status <email> <in/out> <location>`")
            return
        email = parts[1].strip()
        status = parts[2].strip().lower()
        if status not in ["in", "out"]:
            send_message(chat_id, "❌ Status must be 'in' or 'out'.")
            return
        loc = " ".join(parts[3:]) if len(parts) > 3 else "--"
        with get_db() as conn:
            target = conn.execute("SELECT id, name FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
            if target:
                conn.execute("UPDATE users SET status = ?, location = ?, comment = '--', last_updated = CURRENT_TIMESTAMP WHERE id = ?", (status, loc, target["id"]))
                conn.commit()
                send_message(chat_id, f"✅ Updated **{target['name']}** to {status.upper()} ({loc}).")
            else:
                send_message(chat_id, f"❌ No user found with email: {email}")
        return

    if text_clean.lower().startswith("/broadcast"):
        if not is_manager: return
        parts = text_clean.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            broadcast_state[chat_id] = True
            send_message(chat_id, "📢 **Broadcast Mode**\nWhat message would you like to send to all users? (Type `/cancel` to abort)")
            return
        msg = parts[1].strip()
        sender_rank = dict(user).get("rank", "").strip()
        sender_name = user['name']
        sender_display = f"{sender_rank} {sender_name}".strip()
        b_msg = f"📢 **BROADCAST FROM {sender_display}**\n\n{msg}"
        with get_db() as conn:
            chats = conn.execute("SELECT telegram_chat_id FROM users WHERE telegram_chat_id IS NOT NULL").fetchall()
        count = 0
        for c in chats:
            try:
                send_message(c["telegram_chat_id"], b_msg)
                count += 1
            except: pass
        send_message(chat_id, f"✅ Broadcast sent to {count} users.")
        return

    if text_clean.lower() == "/reset_all":
        if not dict(user).get("is_admin"): return
        with get_db() as conn:
            conn.execute("UPDATE users SET status = 'out', location = '--', comment = '--', last_updated = CURRENT_TIMESTAMP")
            conn.commit()
        send_message(chat_id, "✅ All users have been reset to OUT.")
        return


    
    # Handle Group Confirmation
    if chat_id in group_confirm_state:
        conf_state = group_confirm_state[chat_id]
        if text_clean.lower() in ['yes', 'y']:
            group = conf_state["requested_group"]
            if conf_state.get("is_onboarding"):
                state = onboarding_state[chat_id]
                create_account(chat_id, state["email"], state["name"], group, state.get("rank", ""), state.get("sort_weight", 50))
                send_message(chat_id, f"🎉 You're all set, {state['name']}!\n\nYou've been added to the **{group}** group.")
                del onboarding_state[chat_id]
            else:
                with get_db() as conn:
                    conn.execute("UPDATE users SET group_name = ? WHERE id = ?", (group, user["id"]))
                    conn.commit()
                send_message(chat_id, f"✅ Created new group and moved you to **{group}**.")
            del group_confirm_state[chat_id]
        elif text_clean.lower() in ['no', 'n', 'cancel']:
            send_message(chat_id, "❌ Action cancelled. Please reply with a different group name.")
            del group_confirm_state[chat_id]
        else:
            # They provided a different group name
            new_group = text_clean
            if conf_state.get("is_onboarding"):
                state = onboarding_state[chat_id]
                create_account(chat_id, state["email"], state["name"], new_group, state.get("rank", ""), state.get("sort_weight", 50))
                send_message(chat_id, f"🎉 You're all set, {state['name']}!\n\nYou've been added to the **{new_group}** group.")
                del onboarding_state[chat_id]
            else:
                with get_db() as conn:
                    conn.execute("UPDATE users SET group_name = ? WHERE id = ?", (new_group, user["id"]))
                    conn.commit()
                send_message(chat_id, f"✅ Moved you to **{new_group}**.")
            del group_confirm_state[chat_id]
        return

    # Handle Onboarding Flow
    if not user or text_clean.lower() == "/start" or chat_id in onboarding_state:
        if chat_id not in onboarding_state or text_clean.lower() == "/start":
            onboarding_state[chat_id] = {"step": "name"}
            send_message(chat_id, "👋 Welcome to Hermes!\n\nI don't recognize your account yet. Let's get you set up.\n\nWhat is your **Rank and Name**? (e.g., SSG Dixon)")
            return
            
        state = onboarding_state[chat_id]
        
        if state["step"] == "name":
            parsed_name = parse_onboarding_name(text_clean)
            state["rank"] = parsed_name.get("rank", "")
            state["name"] = parsed_name.get("name", text_clean)
            state["sort_weight"] = get_sort_weight(state["rank"])
            
            display_name = f"{state['rank']} {state['name']}".strip()
            state["step"] = "email"
            send_message(chat_id, f"Got it, {display_name}. Now, what is your **work email address**?")
            return
            
        if state["step"] == "email":
            state["email"] = text_clean.lower()
            state["step"] = "group"
            groups = get_all_groups()
            group_txt = ", ".join(groups) if groups else "Ops, S6, Leadership, etc."
            send_message(chat_id, f"Thanks. Lastly, what **group** are you in?\n(e.g., {group_txt})")
            return
            
        if state["step"] == "group":
            group_name = text_clean
            state["group_name"] = group_name
            
            with get_db() as conn:
                user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                
            if user_count == 0:
                # First user! Bypass PIN
                create_account(chat_id, state["email"], state["name"], group_name, state.get("rank", ""), state.get("sort_weight", 50))
                
                with get_db() as conn:
                    settings = conn.execute("SELECT onboarding_pin FROM app_settings WHERE id = 1").fetchone()
                    pin = settings["onboarding_pin"] if settings else "123456"
                    
                send_message(chat_id, f"🎉 You're all set, {state['name']}!\n\nYou've been added to the **{group_name}** group. You can now text me your status updates!\n\n🔑 **IMPORTANT**: Since you are the first user, please set a custom Onboarding PIN for new members right now (e.g., 'Change onboarding PIN to 987654').")
                del onboarding_state[chat_id]
                return
            else:
                state["step"] = "pin"
                send_message(chat_id, "🔒 **Security Check**\n\nSince this board is already active, please enter the **6-digit Onboarding PIN** to complete your registration. Ask a coworker if you don't know it.")
                return
                
        if state["step"] == "pin":
            entered_pin = text_clean
            with get_db() as conn:
                settings = conn.execute("SELECT onboarding_pin FROM app_settings WHERE id = 1").fetchone()
                correct_pin = settings["onboarding_pin"] if settings else "123456"
                
            if entered_pin == correct_pin:
                group_name = state["group_name"]
                groups = [g.lower() for g in get_all_groups()]
                if group_name.lower() not in groups and len(groups) > 0:
                    group_confirm_state[chat_id] = {"requested_group": group_name, "is_onboarding": True}
                    send_message(chat_id, f"⚠️ The group '**{group_name}**' doesn't exist yet.\n\nAre you sure you want to create a new group? (Reply 'Yes' to create it, 'No' to cancel, or type the correct group name).")
                    return
                
                create_account(chat_id, state["email"], state["name"], group_name, state.get("rank", ""), state.get("sort_weight", 50))
                send_message(chat_id, f"🎉 You're all set, {state['name']}!\n\nYou've been added to the **{group_name}** group. You can now text me your status updates!")
                del onboarding_state[chat_id]
            else:
                send_message(chat_id, "❌ Incorrect PIN. Please try again.")
            return

    # Check if we are waiting for a comment
    if chat_id in waiting_for_comment:
        quick_commands = [
            "in", "i'm in", "im in", "here", "back",
            "out", "out - eod", "out - lunch", "out - meeting",
            "help", "/help", "/start", "/cancel", "/admin", "/rollcall",
            "/users", "/broadcast", "/admin_help", "/admin_logout"
        ]
        
        # If user sends a command, slash command, or button press, cancel comment wait and process normally
        if text_clean.lower() in quick_commands or text_clean.startswith("/"):
            del waiting_for_comment[chat_id]
            # Fall through to process as a command/status update
        elif text_clean.lower() in ["no", "nope", "nah", "no thanks", "none", "negative", "no comment", "cancel", "nevermind", "never mind", "skip"]:
            send_message(chat_id, "✅ Okay, no comment.")
            del waiting_for_comment[chat_id]
            return
        else:
            send_message(chat_id, "🤔 Processing your comment...")
            try:
                # We wrap their text so the AI knows it's meant to be a comment, allowing it to strip conversational filler
                parsed_comment_data = parse_status_message(f"My status update comment is: {text}")
                new_comment = parsed_comment_data.get("comment", "--")
                
                if new_comment == "--" or new_comment.lower() in ["no", "none"]:
                    send_message(chat_id, "✅ Okay, no comment.")
                else:
                    with get_db() as conn:
                        conn.execute("UPDATE users SET comment = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", (new_comment, user["id"]))
                        conn.commit()
                    send_message(chat_id, f"✅ Got it! Added comment: {new_comment}")
            except Exception as e:
                print(f"Comment parsing error: {e}")
                send_message(chat_id, "❌ Sorry, I had trouble parsing that comment.")
            del waiting_for_comment[chat_id]
            return



    # Handle literal simple acknowledgments to save API calls
    if text_clean.lower() in ["thanks", "thank you", "ok", "okay", "got it", "cool", "roger", "copy", "👍"]:
        return

    # Handle Literal Help Command
    if text_clean.lower() in ["help", "/help"]:
        help_msg = (
            "🤖 **The Office Bot Help**\n\n"
            "**Updating your status:**\n"
            "Just message me naturally! Examples:\n"
            "- \"Heading to lunch\"\n"
            "- \"I'm at the dentist, back at 1400\"\n"
            "- \"Back in the office\"\n\n"
            "**Changing your Profile (Rank, Name, Group, Email):**\n"
            "If you get promoted, married, or switch groups, just type `/start` at any time to re-enter your information.\n\n"
            "**Other Commands:**\n"
            "- \"Move me to the S6 group\""
        )
        send_message(chat_id, help_msg)
        return

    # AI Parsing
    # Removed to save network roundtrip
    try:
        norm_text = text_clean.upper()
        if norm_text in ["IN", "OUT - EOD", "OUT - LUNCH", "OUT - MEETING"] or text_clean in ["Help", "/help", "help"]:
            if text_clean in ["Help", "/help", "help"]:
                action = "help"
                parsed_data = {"action": "help"}
            else:
                action = "update_status"
                if norm_text == "IN":
                    parsed_data = {"action": "update_status", "status": "in", "location": "--", "comment": "--"}
                elif norm_text == "OUT - EOD":
                    parsed_data = {"action": "update_status", "status": "out", "location": "--", "comment": "--"}
                else:
                    loc = text_clean.split("-")[1].strip()
                    parsed_data = {"action": "update_status", "status": "out", "location": loc, "comment": "--"}
        else:
            parsed_data = parse_status_message(text, is_admin=dict(user).get("is_admin", False))
        action = parsed_data.get("action", "update_status")
        
        if action == "help":
            if dict(user).get("is_admin"):
                help_msg = (
                    "🤖 **The Office Bot Admin Help**\n\n"
                    "**Updating your status:**\n"
                    "Just message me naturally! (e.g. \"Heading to lunch\")\n\n"
                    "**Admin Commands:**\n"
                    "`/users` - List all registered users\n"
                    "`/promote <email> <manager/user>` - Set user role\n"
                    "`/remove_user <email>` - Delete a user\n"
                    "`/remove_group <group>` - Delete a group\n"
                    "`/set_group <email> <group>` - Move a user\n"
                    "`/set_status <email> <in/out> <location>` - Update status\n"
                    "`/broadcast <message>` - Send a global broadcast\n"
                    "`/reset_all` - Force all users to OUT\n"
                    "`/admin_logout` - De-elevate back to normal role\n\n"
                    "*You can also use natural language to remove users/groups, move members, promote users, and change the PIN, Org Name, or Group Order!*"
                )
            elif dict(user).get("role") == "manager":
                help_msg = (
                    "🤖 **The Office Bot Manager Help**\n\n"
                    "**Updating your status:**\n"
                    "Just message me naturally! (e.g. \"Heading to lunch\")\n\n"
                    "**Updating OTHER people's status:**\n"
                    "Since you are a manager, you can say: \"Set Dixon to out at the dentist\".\n\n"
                    "**Manager Commands:**\n"
                    "`/rollcall` - Grouped accountability report\n"
                    "`/set_group <email> <group>` - Move a user\n"
                    "`/broadcast <message>` - Send a global broadcast\n"
                    "`/admin <PIN>` - Elevate to Admin (15 mins)\n\n"
                    "*You can also use natural language to update the Board Announcement!*"
                )
            else:
                help_msg = (
                    "🤖 **The Office Bot Help**\n\n"
                    "**Updating your status:**\n"
                    "Just message me naturally! Examples:\n"
                    "- \"Heading to lunch\"\n"
                    "- \"I'm at the dentist, back at 1400\"\n"
                    "- \"Back in the office\"\n\n"
                    "**Changing your Profile (Rank, Name, Group, Email):**\n"
                    "If you get promoted, married, or switch groups, just type `/start` at any time to re-enter your information.\n\n"
                    "**Other Commands:**\n"
                    "`/cancel` - Exit onboarding or any confirmation prompt\n"
                    "- \"Move me to the S6 group\"\n"
                )
            send_message(chat_id, help_msg)
            return

        if action == "change_group":
            target_group = parsed_data.get("target_group", "")
            if not target_group:
                send_message(chat_id, "❌ I didn't catch the group name. Please try again.")
                return
                
            groups = [g.lower() for g in get_all_groups()]
            if target_group.lower() not in groups:
                group_confirm_state[chat_id] = {"requested_group": target_group, "is_onboarding": False}
                send_message(chat_id, f"⚠️ The group '**{target_group}**' doesn't exist yet.\n\nAre you sure you want to create a new group? (Reply 'Yes' to create it, 'No' to cancel, or type the correct group name).")
            else:
                # Group exists, update instantly
                with get_db() as conn:
                    conn.execute("UPDATE users SET group_name = ? WHERE id = ?", (target_group, user["id"]))
                    conn.commit()
                send_message(chat_id, f"✅ Moved you to **{target_group}**.")
            return

        if action == "admin_update_status":
            if not is_manager:
                send_message(chat_id, "❌ Only Managers or Admins can update another user's status.")
                return
            target_user_name = parsed_data.get("target_user")
            if not target_user_name:
                send_message(chat_id, "❌ I didn't catch the name of the user to update.")
                return
            
            target_status = parsed_data.get("status", "out").lower()
            if target_status not in ["in", "out"]:
                target_status = "out"
            target_loc = parsed_data.get("location", "--")
            target_comment = parsed_data.get("comment", "--")
            
            with get_db() as conn:
                target = conn.execute("SELECT id, name FROM users WHERE name LIKE ? COLLATE NOCASE", (f"%{target_user_name}%",)).fetchone()
                if target:
                    conn.execute("UPDATE users SET status = ?, location = ?, comment = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", (target_status, target_loc, target_comment, target["id"]))
                    conn.commit()
                    send_message(chat_id, f"✅ Updated **{target['name']}** to {target_status.upper()} ({target_loc}).")
                else:
                    send_message(chat_id, f"❌ No user found matching the name: {target_user_name}")
            return


        if action == "promote_user":
            if not dict(user).get("is_admin"):
                send_message(chat_id, "❌ Only Admins can change user roles.")
                return
            target_name = parsed_data.get("target_user")
            new_role = parsed_data.get("target_role", "").lower()
            if not target_name or new_role not in ["manager", "user"]:
                send_message(chat_id, "❌ I couldn't understand the name or role. Please specify 'manager' or 'user'.")
                return
            
            with get_db() as conn:
                target_user = conn.execute("SELECT email, name FROM users WHERE name LIKE ?", (f"%{target_name}%",)).fetchone()
                if not target_user:
                    send_message(chat_id, f"❌ No user found matching: {target_name}")
                    return
                
                conn.execute("UPDATE users SET role = ? WHERE email = ?", (new_role, target_user['email']))
                conn.commit()
            send_message(chat_id, f"✅ **{target_user['name']}** has been updated to role: **{new_role}**")
            return

        if action == "remove_user":
            if not dict(user).get("is_admin"):
                send_message(chat_id, "❌ Only Admins can remove users.")
                return
            target_identifier = parsed_data.get("target_user", "").strip()
            if not target_identifier:
                send_message(chat_id, "❌ Please specify the user's name or email to remove.")
                return
            with get_db() as conn:
                target = conn.execute(
                    "SELECT id, name, email FROM users WHERE email = ? COLLATE NOCASE OR name LIKE ? COLLATE NOCASE",
                    (target_identifier, f"%{target_identifier}%")
                ).fetchone()
                if not target:
                    send_message(chat_id, f"❌ No user found matching: {target_identifier}")
                    return
                conn.execute("DELETE FROM users WHERE id = ?", (target["id"],))
                conn.commit()
            send_message(chat_id, f"🗑️ User **{target['name']}** (`{target['email']}`) has been removed.")
            return

        if action == "remove_group":
            if not dict(user).get("is_admin"):
                send_message(chat_id, "❌ Only Admins can remove groups.")
                return
            group = parsed_data.get("target_group", "").strip()
            if not group:
                send_message(chat_id, "❌ Please specify the group name to remove.")
                return
            with get_db() as conn:
                conn.execute("DELETE FROM groups WHERE name = ? COLLATE NOCASE", (group,))
                conn.execute("UPDATE users SET group_name = 'Unassigned' WHERE group_name = ? COLLATE NOCASE", (group,))
                conn.commit()
            send_message(chat_id, f"🗑️ Group **{group}** removed. Any members have been moved to 'Unassigned'.")
            return

        if action == "set_user_group":
            if not is_manager:
                send_message(chat_id, "❌ Only Managers or Admins can move users between groups.")
                return
            target_name = parsed_data.get("target_user", "").strip()
            target_group = parsed_data.get("target_group", "").strip()
            if not target_name or not target_group:
                send_message(chat_id, "❌ Please specify both the user and the group name (e.g., 'Move Dixon to S6').")
                return
            with get_db() as conn:
                target_user = conn.execute(
                    "SELECT id, name, email FROM users WHERE email = ? COLLATE NOCASE OR name LIKE ? COLLATE NOCASE",
                    (target_name, f"%{target_name}%")
                ).fetchone()
                if not target_user:
                    send_message(chat_id, f"❌ No user found matching: {target_name}")
                    return
                conn.execute("UPDATE users SET group_name = ? WHERE id = ?", (target_group, target_user["id"]))
                conn.commit()
            send_message(chat_id, f"✅ Moved **{target_user['name']}** to group: **{target_group}**.")
            return

        if action == "update_announcement":
            if not is_manager:
                send_message(chat_id, "❌ Only Managers or Admins can update the announcement.")
                return
            title = parsed_data.get("announcement_title", "Announcement")
            body = parsed_data.get("announcement_body", "")
            if not body or body == "--":
                send_message(chat_id, "❌ Please provide the title and body in your request.\n\nExample: *Update the announcement. Title: Command Climate Survey. Body: Please complete by Friday.*")
                return
            
            with get_db() as conn:
                conn.execute("UPDATE app_settings SET news_title = ?, news_body = ?, news_author = ? WHERE id = 1", (title, body, user["name"]))
                conn.commit()
            
            send_message(chat_id, f"✅ Announcement updated by {user['name']}!\n**{title}**\n{body}")
            return

        if action == "update_pin":
            if not dict(user).get("is_admin"):
                send_message(chat_id, "❌ Only Admins can update the onboarding PIN.")
                return
            new_pin = parsed_data.get("target_group", "")
            if not new_pin:
                send_message(chat_id, "❌ I didn't catch the new PIN. Please try again.")
                return
            with get_db() as conn:
                conn.execute("UPDATE app_settings SET onboarding_pin = ? WHERE id = 1", (new_pin,))
                conn.commit()
            send_message(chat_id, f"✅ Onboarding PIN successfully updated to **{new_pin}** by {user['name']}.")
            return

        if action == "update_org_name":
            if not dict(user).get("is_admin"):
                send_message(chat_id, "❌ Only Admins can update the organization name.")
                return
            new_org = parsed_data.get("target_group", "")
            if not new_org:
                send_message(chat_id, "❌ I didn't catch the new organization name. Please try again.")
                return
            with get_db() as conn:
                conn.execute("UPDATE app_settings SET org_name = ? WHERE id = 1", (new_org,))
                conn.commit()
            send_message(chat_id, f"✅ Unit/Organization name successfully updated to **{new_org}** by {user['name']}.")
            return
            
        
        if action == "update_group_order":
            if not dict(user).get("is_admin"):
                send_message(chat_id, "❌ Only Admins can update the group order.")
                return
            target_groups = parsed_data.get("target_groups", [])
            if not target_groups:
                send_message(chat_id, "❌ I didn't catch the list of groups. Please try again.")
                return
            with get_db() as conn:
                conn.execute("DELETE FROM groups")
                for i, g in enumerate(target_groups):
                    conn.execute("INSERT INTO groups (name, sort_index) VALUES (?, ?)", (g, i + 1))
                conn.commit()
            send_message(chat_id, f"✅ Group order successfully updated by {user['name']}:\n" + ", ".join(target_groups))
            return

        if action == "clarify":
            prompt = parsed_data.get("clarification_prompt") or "I couldn't quite understand that. Could you please clarify your status update?"
            send_message(chat_id, f"❓ {prompt}")
            return

        if action == "ignore":
            send_message(chat_id, "❌ I can only process In/Out Board status updates and administrative commands. Please try again with a valid request.")
            return
            
        if action == "acknowledge":
            return

        # Regular status update
        status = parsed_data.get("status", "out").lower()
        if status not in ["in", "out"]:
            status = "out"
            
        location = parsed_data.get("location", "--")
        
        if status == "in":
            # When checking IN, wipe the location clean unless they specified a very specific alternate base
            if location.lower() in ["unknown", "--"]:
                location = "--"
        else:
            # When OUT:
            if location.lower() in ["unknown", "--"]:
                # Check if this message describes transit, weather/traffic delay, arrival, or explicit clearance
                transit_or_clear_words = [
                    "out", "leaving", "heading out", "gone", "traffic", "fog", "weather", 
                    "accident", "en route", "transit", "driving", "heading in", "coming in", 
                    "be in", "arriving", "on my way", "not at", "do not mark", "clear", "home", "delayed"
                ]
                is_transit_or_clear = any(w in text_clean.lower() for w in transit_or_clear_words)
                
                # Only carry over existing location if user was ALREADY out, has an actual location, 
                # and this is strictly a return-time update without transit/clearance context
                if (not is_transit_or_clear 
                    and user["status"] == "out" 
                    and user["location"] not in ["--", "Unknown", "unknown", ""]):
                    location = user["location"]
                else:
                    location = "--"
            
        comment = parsed_data.get("comment", "--")
        
        with get_db() as conn:
            conn.execute("""
                UPDATE users 
                SET status = ?, location = ?, comment = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, location, comment, user["id"]))
            conn.commit()
            
        reply = f"✅ Got it! Marked you as **{status.upper()}**.\n"
        if status == "out":
            reply += f"📍 Location: {location}\n"
            if comment != "--":
                reply += f"💬 Comment: {comment}"
            else:
                waiting_for_comment[chat_id] = {"timestamp": time.time()}
                reply += "\nDo you want to add a comment? (Reply with a comment, 'no', or just ignore this. Closes in 5 mins)"
                
        send_message(chat_id, reply)
        
    except Exception as e:
        print(f"Error processing: {e}")
        send_message(chat_id, "❌ Sorry, I hit an error trying to process that.")

def main():
    setup_db()
    print("Hermes Bot started!")
    offset = 0
    
    while True:
        try:
            check_timeouts()
            url = f"{BASE_URL}/getUpdates?offset={offset}&timeout=30"
            resp = requests.get(url, timeout=35).json()
            
            if resp.get("ok"):
                for update in resp.get("result", []):
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"]
                        message_id = update["message"]["message_id"]
                        
                        print(f"Received from {chat_id}: {text}")
                        process_message(chat_id, text, message_id)
                        
        except requests.exceptions.ReadTimeout:
            pass
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
