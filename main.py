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
            "sort_weight INTEGER DEFAULT 50"
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
