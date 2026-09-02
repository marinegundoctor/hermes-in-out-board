from fastapi import FastAPI, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import os
from contextlib import asynccontextmanager
from collections import defaultdict

import os
DB_FILE = os.environ.get("DB_PATH", "inout.db")

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                uid TEXT UNIQUE,
                status TEXT NOT NULL DEFAULT 'out',
                location TEXT,
                comment TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_chat_id TEXT,
                group_name TEXT DEFAULT 'Unassigned',
                rank TEXT,
                sort_weight INTEGER DEFAULT 50
            )
        """)
        
        # Ensure new columns exist if upgrading old db
        for col in [
            "group_name TEXT DEFAULT 'Unassigned'",
            "rank TEXT",
            "sort_weight INTEGER DEFAULT 50",
            "card_id TEXT"
        ]:

            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col}")
                conn.commit()
            except sqlite3.OperationalError:
                pass # column exists

        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                name TEXT PRIMARY KEY,
                sort_index INTEGER DEFAULT 99
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                org_name TEXT NOT NULL,
                news_title TEXT DEFAULT 'Announcements',
                news_body TEXT DEFAULT 'Welcome to the In/Out Board.',
                news_author TEXT,
                onboarding_pin TEXT DEFAULT '123456'
            )
        """)
        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with get_db() as conn:
        settings = conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()
        if not settings:
            return RedirectResponse(url="/setup", status_code=status.HTTP_302_FOUND)
        
        users = conn.execute("SELECT u.*, IFNULL(g.sort_index, 99) as group_sort FROM users u LEFT JOIN groups g ON u.group_name = g.name ORDER BY group_sort ASC, u.sort_weight ASC, u.name ASC").fetchall()
        
        grouped_users = defaultdict(list)
        for u in users:
            grouped_users[u["group_name"]].append(dict(u))
            
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"settings": settings, "grouped_users": dict(grouped_users)}
    )

@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    with get_db() as conn:
        settings = conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()
        if settings:
             return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
             
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Setup - Hermes Board</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body style="display: flex; justify-content: center; align-items: center; height: 100vh; flex-direction: column;">
        <div style="background: #1e1e1e; padding: 40px; border-radius: 8px; border: 1px solid #333;">
            <h2>Initial Setup</h2>
            <form action="/setup" method="post" style="display: flex; flex-direction: column; gap: 15px; margin-top: 20px;">
                <label>Organization / Unit Name:</label>
                <input type="text" name="org_name" required placeholder="e.g. 1034th CSSB" style="padding: 10px; background: #333; color: white; border: 1px solid #555; border-radius: 4px;">
                <button type="submit" style="padding: 10px; background: #facc15; color: black; font-weight: bold; border: none; border-radius: 4px; cursor: pointer;">Initialize Board</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/setup")
def setup_submit(org_name: str = Form(...)):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO app_settings (id, org_name, news_title, news_body) VALUES (1, ?, ?, ?)", 
                     (org_name, f"{org_name} News", "Welcome to your new In/Out Board!"))
        conn.commit()
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.get("/api/users")
def get_users():
    with get_db() as conn:
        users = conn.execute("SELECT u.*, IFNULL(g.sort_index, 99) as group_sort FROM users u LEFT JOIN groups g ON u.group_name = g.name ORDER BY group_sort ASC, u.sort_weight ASC, u.name ASC").fetchall()
        return [dict(u) for u in users]

@app.get("/api/settings")
def get_settings():
    with get_db() as conn:
        settings = conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()
        return dict(settings) if settings else {}


# --- SMART CARD ENDPOINTS ---
import time
pending_card_scan = None

class PendingScan(BaseModel):
    card_id: str

@app.post("/api/scans/pending")
def set_pending_scan(scan: PendingScan):
    global pending_card_scan
    pending_card_scan = {
        "card_id": scan.card_id,
        "timestamp": time.time()
    }
    return {"success": True}

@app.get("/api/scans/pending")
def get_pending_scan():
    global pending_card_scan
    if pending_card_scan:
        if time.time() - pending_card_scan["timestamp"] > 30:
            pending_card_scan = None
        else:
            # Look up if user exists
            with get_db() as conn:
                user = conn.execute("SELECT * FROM users WHERE card_id = ?", (pending_card_scan["card_id"],)).fetchone()
                if user:
                    pending_card_scan["user"] = dict(user)
                else:
                    pending_card_scan["user"] = None
    return pending_card_scan or {}

class RegisterCardRequest(BaseModel):
    card_id: str
    email: str

@app.post("/api/scans/register")
def register_card(req: RegisterCardRequest):
    global pending_card_scan
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (req.email,)).fetchone()
        if user:
            conn.execute("UPDATE users SET card_id = ? WHERE id = ?", (req.card_id, user["id"]))
            conn.commit()
            if pending_card_scan and pending_card_scan.get("card_id") == req.card_id:
                pending_card_scan = None
            return {"success": True, "message": f"Card linked to {user['name']}!"}
        else:
            # Need name
            return {"success": False, "needs_name": True}

class RegisterNewUserRequest(BaseModel):
    card_id: str
    email: str
    name: str
    rank: str = ""
    group: str = "Unassigned" 

@app.post("/api/scans/register_new")
def register_new_user(req: RegisterNewUserRequest):
    global pending_card_scan
    import uuid
    uid = str(uuid.uuid4())[:8]
    with get_db() as conn:
        conn.execute("""
            INSERT INTO users (email, name, rank, uid, group_name, status, location, comment, card_id) 
            VALUES (?, ?, ?, ?, ?, 'in', '--', '--', ?)
        """, (req.email, req.name, req.rank, uid, req.group, req.card_id))
        conn.commit()
    if pending_card_scan and pending_card_scan.get("card_id") == req.card_id:
        pending_card_scan = None
    return {"success": True}

class CardActionRequest(BaseModel):
    card_id: str
    action: str  # 'IN' or 'OUT'
    location: str = ""
    comment: str = ""


class TapActionRequest(BaseModel):
    uid: str
    location: str = "--"
    comment: str = ""

@app.post("/api/tap")
def kiosk_tap_action(req: TapActionRequest):
    with get_db() as conn:
        user = conn.execute("SELECT status FROM users WHERE uid = ?", (req.uid,)).fetchone()
        if not user:
            return {"success": False, "error": "User not found"}
            
        if user['status'] == 'out':
            conn.execute("UPDATE users SET status = 'in', location = '--', comment = '--', last_updated = CURRENT_TIMESTAMP WHERE uid = ?", (req.uid,))
        else:
            conn.execute("UPDATE users SET status = 'out', location = ?, comment = ?, last_updated = CURRENT_TIMESTAMP WHERE uid = ?", (req.location, req.comment, req.uid))
        conn.commit()
    return {"success": True}

@app.post("/api/scans/action")
def resolve_card_action(req: CardActionRequest):
    global pending_card_scan
    with get_db() as conn:
        if req.action == 'IN':
            conn.execute("UPDATE users SET status = 'in', location = '--', comment = '--', last_updated = CURRENT_TIMESTAMP WHERE card_id = ?", (req.card_id,))
        else:
            conn.execute("UPDATE users SET status = 'out', location = ?, comment = ?, last_updated = CURRENT_TIMESTAMP WHERE card_id = ?", (req.location, req.comment, req.card_id))
        conn.commit()
    if pending_card_scan and pending_card_scan.get("card_id") == req.card_id:
        pending_card_scan = None
    return {"success": True}

@app.post("/api/scans/cancel")
def cancel_scan(scan: PendingScan):
    global pending_card_scan
    if pending_card_scan and pending_card_scan.get("card_id") == scan.card_id:
        pending_card_scan = None
    return {"success": True}

