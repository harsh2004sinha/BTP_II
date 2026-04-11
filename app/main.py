from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import logging

from app.database import create_tables
from app.config import settings

# Import each router file directly
from app.routers.auth       import router as auth_router
from app.routers.plans      import router as plans_router
from app.routers.upload     import router as upload_router
from app.routers.weather    import router as weather_router
from app.routers.results    import router as results_router
from app.routers.prediction import router as prediction_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def scheduled_update():
    logger.info("Scheduler: running periodic update...")
    from app.database import SessionLocal
    from app.services.algorithm_service import AlgorithmService

    db = SessionLocal()
    try:
        AlgorithmService.run_scheduled_update(db)
    except Exception as e:
        logger.warning("Scheduler update failed: %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    logger.info(f"Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Server stopped")


app = FastAPI(
    title="Energy Management System API",
    description="Intelligent Cost-Optimized Energy Management Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(plans_router)
app.include_router(upload_router)
app.include_router(weather_router)
app.include_router(results_router)
app.include_router(prediction_router)


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