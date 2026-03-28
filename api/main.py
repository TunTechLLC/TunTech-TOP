import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routers import engagements, signals, patterns, agents, findings, roadmap, knowledge, reporting

# ── Logging ──────────────────────────────────────────────────────────────
from config import LOG_PATH
from pathlib import Path

log_path = Path(LOG_PATH)
log_path.parent.mkdir(parents=True, exist_ok=True)

handler = RotatingFileHandler(
    log_path, maxBytes=5_000_000, backupCount=3
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s: %(message)s"
))

# Get the root logger and attach the handler directly
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)
root_logger.addHandler(logging.StreamHandler())

logger = logging.getLogger(__name__)
logger.info("TOP backend starting up — log file initialized at %s", log_path)

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
app.include_router(
    roadmap.router,
    prefix="/api/engagements",
    tags=["roadmap"]
)
app.include_router(
    knowledge.router,
    prefix="/api/engagements",
    tags=["knowledge"]
)
app.include_router(
    reporting.router,
    prefix="/api",
    tags=["reporting"]
)

# ── Global error handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "path": str(request.url)}
    )
