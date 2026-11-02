# FinPilot AI — Frontend + Backend Infrastructure

Next.js dashboard and chat UI, FastAPI API gateway, JWT auth with role-based access control, and Docker packaging.
This module connects the forecasting, fraud-detection, RAG and agent modules into one product.

```
Browser (Next.js, :3000)  --HTTP + JWT-->  FastAPI gateway (:8000)  -->  module routers
                                                                         forecast / fraud / documents / agent
```

## Quick start (Windows)
Requirements: Python 3.10+, Node.js 18+.

    start.bat        # sets everything up on first run, starts both servers, opens the browser
    stop.bat         # stops both servers

## Quick start (manual / macOS / Linux)

    # backend
    cd backend
    python -m venv venv
    venv\Scripts\activate            # Windows   (macOS/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8000

    # frontend (second terminal)
    cd frontend
    npm install
    npm run dev

Open http://localhost:3000 — API docs at http://127.0.0.1:8000/docs

## Docker

    cp .env.example .env
    docker compose up --build

## Demo accounts
| Email | Password | Role | Can do |
|---|---|---|---|
| owner@aaravretail.com | demo1234 | owner | everything, incl. clearing flagged transactions |
| analyst@aaravretail.com | demo1234 | analyst | read + approve agent actions (cannot clear fraud flags) |

## Configuration (`.env`, see `.env.example`)
`JWT_SECRET`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`. Never commit a real `.env`.

## Module Integration Status

## Module Integration Status

| Module | Owner | Status | Backend Location | Details |
|---|---|---|---|---|
| Sales Forecasting | G Yaswanth Sai | COMPLETE | `backend/modules/forecasting/` | 17 Prophet models trained and backtested. RMSE: 1,708; WAPE: 70.4%. Forecasting APIs and Next.js Product Forecast tab integrated. |
| Fraud Detection | Kritagy Kaushik | COMPLETE | `backend/modules/fraud/__init__.py` | Isolation Forest-based anomaly detection combined with rule-based risk scoring. Supports transaction analysis, suspicious transaction identification, and review queue generation. |
| RAG / Document Q&A | Pallav Acharya | COMPLETE | `backend/modules/documents/__init__.py` | PDF text extraction, overlapping text chunking, TF-IDF-based retrieval, ChromaDB storage, and Gemini-powered question answering. Evaluated with 25 test cases: 25/25 passed (100% source retrieval evaluation). |
| AI Agent | Akshi Yadav | COMPLETE | `backend/modules/agent/__init__.py` | LangGraph-based workflow orchestration, fraud analysis, report generation, notifications, human approval/rejection, and audit logging. |


See `TEAM_INTEGRATION_GUIDE.docx` for the full per-person instructions.

## Project layout
    backend/                   FastAPI app (app/main.py, app/auth_utils.py = JWT + RBAC, app/routers/*)
    backend/modules/           Module implementations:
      forecasting/             [DONE] Real Prophet bundle, runtime reader, and training/ folder
      fraud/                   [STUB] Fraud detection module
      documents/               [STUB] Document retrieval / RAG module
      agent/                   [STUB] LangGraph agent module
    frontend/                  Next.js pages router (pages/, components/, lib/api.js, styles/)
      components/              ProductForecastChart (SVG), ProductForecastTab
    docker-compose.yml, start.bat, stop.bat

## Status / Current State
- **Infra & Auth**: Login, JWT authentication, RBAC enforced server-side, Docker configurations, unified `start.bat` / `stop.bat`.
- **Sales Forecasting (Yaswanth)**: 100% finished, tested, and integrated end-to-end (backend API + frontend SVG chart, search, dropdowns, table, overview KPI & top 8 cards).
- **Pending Teammates**: Fraud detection, Document Q&A, and Agent activity remain cleanly stubbed with their defined contracts, ready to plug in as soon as Kaushik, Pallav, and Akshi provide their code.
- **No Database Yet**: In-memory state for dev sessions; demo users in `routers/auth.py`.
