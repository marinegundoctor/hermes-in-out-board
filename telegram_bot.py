import time
import requests
import sqlite3
import os
import json
import uuid
from hermes_ai import parse_status_message, parse_onboarding_name

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
DB_FILE = os.environ.get("DB_PATH", "inout.db")

waiting_for_comment = {} # {chat_id: {"timestamp": ...}}
onboarding_state = {} # {chat_id: {"step": "name", "name": "", "email": ""}}
group_confirm_state = {} # {chat_id: {"requested_group": "xyz", "is_onboarding": bool}}


def get_sort_weight(rank: str) -> int:
    r = rank.upper().strip().replace(".", "")
    weights = {
        "GEN": 1, "LTG": 2, "MG": 3, "BG": 4, "COL": 5, "LTC": 6, "MAJ": 7, "CPT": 8, "1LT": 9, "2LT": 10,
        "CW5": 11, "CW4": 12, "CW3": 13, "CW2": 14, "WO1": 15,
        "SMA": 16, "CSM": 17, "SGM": 17, "1SG": 18, "MSG": 18, "SFC": 19, "SSG": 20, "SGT": 21, "CPL": 22, "SPC": 22, "PFC": 23, "PV2": 24, "PV1": 24,
        "MR": 30, "MS": 30, "MRS": 30, "CIV": 30
    }
    return weights.get(r, 50)

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
        conn.commit()

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def get_user_by_chat_id(chat_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_chat_id = ?", (str(chat_id),)).fetchone()

def get_all_groups():
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT group_name FROM users WHERE group_name IS NOT NULL").fetchall()
        return [r[0] for r in rows]

def check_timeouts():
    now = time.time()
    to_remove = []
    for chat_id, state in waiting_for_comment.items():
        if now - state["timestamp"] > 300:
            send_message(chat_id, "⏱️ Okay, no comment added.")
            to_remove.append(chat_id)
    for chat_id in to_remove:
        del waiting_for_comment[chat_id]

def create_account(chat_id, email, name, group_name, rank="", sort_weight=50):
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

def process_message(chat_id, text):
    global waiting_for_comment, onboarding_state, group_confirm_state
    
    user = get_user_by_chat_id(chat_id)
    text_clean = text.strip()
    
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
    if not user:
        if chat_id not in onboarding_state:
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
                    
                send_message(chat_id, f"🎉 You're all set, {state['name']}!\n\nYou've been added to the **{group_name}** group. You can now text me your status updates!\n\n🔑 **IMPORTANT**: Since you are the first user, the default Onboarding PIN for new members is set to **{pin}**. I highly recommend you reply right now to change it (e.g., 'Change onboarding PIN to 987654').")
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
        if text_clean.lower() in ["no", "nope", "nah", "no thanks", "none", "negative", "no comment"]:
            send_message(chat_id, "✅ Okay, no comment.")
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

    # AI Parsing
    send_message(chat_id, "🤔 Parsing your message...")
    
    try:
        parsed_data = parse_status_message(text)
        action = parsed_data.get("action", "update_status")
        
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

        if action == "update_announcement":
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

        if action == "ignore":
            send_message(chat_id, "❌ I can only process In/Out Board status updates and administrative commands. Please try again with a valid request.")
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
            # When OUT: If no new location was given, usually carry over the old one (e.g. for "running late")
            if location.lower() == "unknown" or location == "--":
                # But if they just say "Out" or "I'm out", wipe it clean instead of carrying over
                if text_clean.lower() in ["out", "out.", "i'm out", "im out", "leaving", "heading out", "gone"]:
                    location = "--"
                else:
                    location = user["location"]
            
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
                        
                        print(f"Received from {chat_id}: {text}")
                        process_message(chat_id, text)
                        
        except requests.exceptions.ReadTimeout:
            pass
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
