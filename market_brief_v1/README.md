# Market Brief V1

A personal digest for the public Telegram channel `@tradingwsidhant`.

## What V1 does
- Fetches posts from Telegram's public channel preview (no Telegram account login).
- Stores posts locally in SQLite and deduplicates.
- Labels posts by rough priority/category.
- Displays the latest posts and a basic grouped brief in a mobile-first React UI.
- Polls the channel every 30 minutes by default and has a manual refresh button.

**Important:** The current summary is rule-based, not an AI-generated interpretation. This is intentionally transparent for the first prototype. AI summarization and native Android widget are next phases.

## Run backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows; on macOS/Linux use cp
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Health: http://localhost:8000/api/health

## Run frontend
Open another terminal:
```bash
cd frontend
npm install
copy .env.example .env   # Windows
npm run dev
```
Visit the Vite address (usually http://localhost:5173).

To test on your phone on the same Wi-Fi, use your PC's local IP for the Vite URL and set `VITE_API_URL` to `http://YOUR_PC_IP:8000`. Firewall may need to allow ports 5173 and 8000.

## Next milestones
1. Confirm collector parses posts reliably on your computer.
2. Add AI summarization with configurable provider.
3. Add filters, archive, daily lessons, and digest.
4. Deploy backend with persistent storage and HTTPS.
5. Build Android app + Glance home-screen widget with refresh and tap-to-open dashboard.

## Safety
This is an educational summary of posts, not financial advice or a signal service. Always open the original post, confirm current prices, and independently assess risk.
