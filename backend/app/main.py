import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, forecast, fraud, documents, agent

app = FastAPI(title="FinPilot AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(forecast.router, prefix="/api/v1/forecast", tags=["forecast"])
app.include_router(fraud.router, prefix="/api/v1/fraud", tags=["fraud"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])

@app.get("/health")
def health():
    return {"status": "ok"}
