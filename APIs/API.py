from fastapi import FastAPI
import logging
from logger_config import setup_logging
from contextlib import asynccontextmanager
from APIs.routers.get_routes import router as get_router
from APIs.routers.post_routes import router as post_router

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application...")
    yield
    logger.info("Shutting down FastAPI application...")

app = FastAPI(title="My First Modular API", version="1.0")

logger.info("Registering API routers...")
app.include_router(get_router)
app.include_router(post_router)
logger.info("Routers registered successfully.")
