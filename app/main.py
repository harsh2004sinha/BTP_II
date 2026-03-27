from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from app.database import create_tables
from app.config import settings
from app.routers import auth, plans, upload, weather, results, prediction

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Scheduler ────────────────────────────────────────────────────────
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


# ── App Instance ─────────────────────────────────────────────────────
app = FastAPI(
    title="Energy Management System API",
    description="Intelligent Cost-Optimized Energy Management Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Change to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(upload.router)
app.include_router(weather.router)
app.include_router(results.router)
app.include_router(prediction.router)


# ── Root ─────────────────────────────────────────────────────────────
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
    return JSONResponse({"status": "healthy", "version": settings.APP_VERSION})