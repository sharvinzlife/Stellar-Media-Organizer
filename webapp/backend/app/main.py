"""
Main FastAPI application
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"📁 Upload directory: {settings.upload_dir}")
    logger.info(f"🔧 API prefix: {settings.api_v1_prefix}")
    yield
    logger.info("🛑 Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="🎬 Organize & Filter with Elegance",
    version=settings.app_version,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "description": "🎬 Organize & Filter with Elegance",
        "status": "🟢 Running",
        "docs": "/docs",
        "api": settings.api_v1_prefix
    }


@app.get("/api/status")
async def status():
    """Simple status check"""
    return {
        "status": "healthy",
        "emoji": "✨",
        "message": "Media Organizer is running smoothly!"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
