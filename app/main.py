from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import logging

from app.database import create_tables
from app.config import settings

# Import routers directly - not from __init__
from app.routers.auth import router as auth_router
from app.routers.plans import router as plans_router
from app.routers.upload import router as upload_router
from app.routers.weather import router as weather_router
from app.routers.results import router as results_router
from app.routers.prediction import router as prediction_router

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Scheduler ────────────────────────────────────────────────
scheduler = BackgroundScheduler()


def scheduled_update():
    """Runs every 15 minutes to refresh predictions."""
    logger.info("Scheduler: running periodic prediction update...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting Energy Management System...")
    create_tables()
    logger.info("Database tables created/verified")
    scheduler.add_job(
        scheduled_update,
        'interval',
        minutes=settings.UPDATE_INTERVAL_MINUTES,
        id='prediction_update'
    )
    scheduler.start()
    logger.info(f"Scheduler started (every {settings.UPDATE_INTERVAL_MINUTES} min)")
    yield
    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped")


# ── App Instance ─────────────────────────────────────────────
app = FastAPI(
    title="Energy Management System API",
    description="Intelligent Cost-Optimized Energy Management Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ───────────────────────────────────────────
app.include_router(auth_router)
app.include_router(plans_router)
app.include_router(upload_router)
app.include_router(weather_router)
app.include_router(results_router)
app.include_router(prediction_router)


# ── Root Endpoints ────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "running",
        "docs":    "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return JSONResponse({
        "status":  "healthy",
        "version": settings.APP_VERSION
    })