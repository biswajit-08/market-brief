from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime, timezone
from pathlib import Path
import os, requests, sqlite3, re, hashlib

load_dotenv()
CHANNEL = os.getenv("CHANNEL_USERNAME", "tradingwsidhant")
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL_MINUTES", "30"))
MAX_POSTS = int(os.getenv("MAX_POSTS", "40"))
DB_PATH = os.getenv("DATABASE_PATH", "marketbrief.db")
BASE_URL = f"https://t.me/s/{CHANNEL}"

app = FastAPI(title="Market Brief API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict this before public deployment
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY, text TEXT NOT NULL, url TEXT NOT NULL,
            posted_at TEXT, category TEXT NOT NULL, priority TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS brief (
            id INTEGER PRIMARY KEY CHECK (id=1), summary TEXT, updated_at TEXT
        )""")

def classify(text):
    t = text.lower()
    if any(k in t for k in ["stop loss hit", "sl hit", "target hit", "exit", "closed the trade", "trade closed", "invalidation"]):
        return "TRADE UPDATE", "critical"
    if any(k in t for k in ["entry", "stop loss", "target", "setup", "trigger", "long", "short", "buy zone", "sell zone"]):
        return "TRADE SETUP", "high"
    if any(k in t for k in ["rbi", "fed", "inflation", "nifty", "sensex", "nasdaq", "dollar", "gold", "silver", "oil", "market", "yield", "election"]):
        return "MARKET / NEWS", "medium"
    if any(k in t for k in ["mindset", "discipline", "fomo", "revenge", "patience", "psychology", "fear", "greed"]):
        return "MINDSET", "medium"
    if any(k in t for k in ["learn", "rule", "chart", "candle", "support", "resistance", "price action", "technical analysis"]):
        return "LEARNING", "low"
    if len(t.strip()) < 45 or any(k in t for k in ["good morning", "champs", "congratulations", "join", "cohort", "course", "subscribe"]):
        return "NOISE / PROMO", "low"
    return "INSIGHT", "medium"

def clean_text(node):
    # preserve line breaks between Telegram message text elements
    text = node.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def scrape_public_channel():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MarketBrief/0.1)"}
    response = requests.get(BASE_URL, headers=headers, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    nodes = soup.select(".tgme_widget_message")
    posts = []
    for node in nodes[-MAX_POSTS:]:
        content = node.select_one(".tgme_widget_message_text")
        if not content:
            continue
        text = clean_text(content)
        if not text:
            continue
        post_ref = node.get("data-post") or ""
        if post_ref:
            post_url = "https://t.me/" + post_ref
            post_id = post_ref.rsplit("/", 1)[-1]
        else:
            link = node.select_one(".tgme_widget_message_date")
            post_url = link.get("href", BASE_URL) if link else BASE_URL
            post_id = hashlib.sha1((post_url + text).encode()).hexdigest()[:16]
        time_node = node.select_one("time")
        posted = time_node.get("datetime") if time_node else None
        category, priority = classify(text)
        posts.append({
            "id": post_id, "text": text, "url": post_url,
            "posted_at": posted, "category": category, "priority": priority
        })
    return posts

def save_posts(posts):
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    with db() as con:
        for p in posts:
            cur = con.execute("""INSERT OR IGNORE INTO posts
                (id,text,url,posted_at,category,priority,fetched_at)
                VALUES (?,?,?,?,?,?,?)""",
                (p["id"], p["text"], p["url"], p["posted_at"], p["category"], p["priority"], now))
            added += cur.rowcount
    return added

def build_basic_brief(posts):
    # Basic V1 summary: prioritized list, not a generative AI claim.
    useful = [p for p in posts if p["category"] != "NOISE / PROMO"]
    critical = [p for p in useful if p["priority"] == "critical"]
    setups = [p for p in useful if p["category"] == "TRADE SETUP"]
    news = [p for p in useful if p["category"] == "MARKET / NEWS"]
    lessons = [p for p in useful if p["category"] in ("LEARNING", "MINDSET")]
    lines = []
    if critical:
        lines.append("TRADE UPDATES: " + " | ".join(x["text"][:240] for x in critical[:3]))
    if setups:
        lines.append("SETUPS: " + " | ".join(x["text"][:240] for x in setups[:3]))
    if news:
        lines.append("MARKET / NEWS: " + " | ".join(x["text"][:240] for x in news[:3]))
    if lessons:
        lines.append("LESSONS / MINDSET: " + " | ".join(x["text"][:240] for x in lessons[:3]))
    if not lines:
        lines.append("No new high-signal posts found yet. Refresh to check the channel.")
    return "\n\n".join(lines)

def refresh():
    posts = scrape_public_channel()
    added = save_posts(posts)
    with db() as con:
        recent = [dict(r) for r in con.execute(
            "SELECT * FROM posts ORDER BY COALESCE(posted_at,'') DESC LIMIT 40"
        ).fetchall()]
        summary = build_basic_brief(recent)
        now = datetime.now(timezone.utc).isoformat()
        con.execute("INSERT OR REPLACE INTO brief(id,summary,updated_at) VALUES(1,?,?)", (summary, now))
    return {"fetched": len(posts), "new": added, "updated_at": now}

@app.on_event("startup")
def startup():
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh, "interval", minutes=FETCH_INTERVAL, id="channel_refresh", max_instances=1)
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        refresh()  # initial fetch
    except Exception as exc:
        print(f"Initial Telegram fetch failed: {exc}")

@app.on_event("shutdown")
def shutdown():
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)

@app.get("/api/health")
def health():
    return {"status": "ok", "channel": CHANNEL}

@app.get("/api/brief")
def get_brief():
    with db() as con:
        row = con.execute("SELECT * FROM brief WHERE id=1").fetchone()
        count = con.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        recent = con.execute("SELECT * FROM posts ORDER BY COALESCE(posted_at,'') DESC LIMIT 8").fetchall()
    if not row:
        return {"summary": "No digest available yet. Try refresh.", "updated_at": None, "count": count, "recent": []}
    return {
        "summary": row["summary"], "updated_at": row["updated_at"], "count": count,
        "recent": [dict(r) for r in recent]
    }

@app.get("/api/posts")
def get_posts(limit: int = 40):
    limit = max(1, min(limit, 100))
    with db() as con:
        rows = con.execute("SELECT * FROM posts ORDER BY COALESCE(posted_at,'') DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/refresh")
def manual_refresh():
    try:
        return refresh()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Telegram fetch failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
