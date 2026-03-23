import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routers import engagements, signals, patterns, agents, findings

# ── Logging ──────────────────────────────────────────────────────────────
LOG_PATH = Path(r"C:\dev\tuntech\top\top.log")

handler = RotatingFileHandler(
    LOG_PATH, maxBytes=5_000_000, backupCount=3
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[handler, logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(title="TOP — TunTech Operations Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(
    engagements.router,
    prefix="/api/engagements",
    tags=["engagements"]
)
app.include_router(
    signals.router,     
    prefix="/api/engagements", 
    tags=["signals"]
)
app.include_router(
    patterns.router, 
    prefix="/api/engagements", 
    tags=["patterns"]
)
app.include_router(
    agents.router,
    prefix="/api/engagements",
    tags=["agents"]
)
app.include_router(
    findings.router,
    prefix="/api/engagements",
    tags=["findings"]
)

# ── Global error handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "path": str(request.url)}
    )

# ── Health check ──────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {"status": "ok"}