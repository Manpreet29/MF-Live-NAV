"""main.py — MF Live NAV Tracker V2"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import init_db, instrument_master_count
from routers.funds import router as funds_router
from routers.nav   import router as nav_router
from routers.admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MF NAV Tracker V2...")
    if not settings.database_url:
        logger.error("DATABASE_URL is not set!")
    else:
        try:
            init_db()
            count = instrument_master_count()
            if count == 0:
                logger.warning("Instrument master is EMPTY.")
            else:
                logger.info("Instrument master: %d instruments loaded.", count)
        except Exception as e:
            logger.error("Database init failed: %s", e)
    logger.info("Server ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="MF Live NAV Tracker",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(funds_router)
app.include_router(nav_router)
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
def root():
    """Root endpoint — used by UptimeRobot to keep the server awake."""
    return {"status": "ok", "service": "MF NAV Tracker V2"}


@app.head("/api/health", include_in_schema=False)
def health_head():
    """HEAD version of health — required by UptimeRobot monitoring."""
    return JSONResponse(content=None, status_code=200)