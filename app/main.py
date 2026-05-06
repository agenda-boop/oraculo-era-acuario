"""
Oráculo Digital Era de Acuario — FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.routers import oracle, webhook
from app.models import HealthResponse

settings = get_settings()

app = FastAPI(
    title="Oráculo Digital Era de Acuario",
    description="Motor de inteligencia artificial del Oráculo. 12 arquetipos. Una presencia.",
    version="1.0.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(oracle.router, prefix="/api")
app.include_router(webhook.router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="online",
        version="1.0.0",
        environment=settings.app_env,
    )


@app.get("/")
async def root():
    return {
        "oracle": "Era de Acuario",
        "status": "El Oráculo está presente.",
        "docs": "/docs" if settings.app_env == "development" else "No disponible en producción"
    }


@app.exception_handler(404)
async def not_found(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "El Oráculo no encuentra lo que buscás."}
    )


@app.exception_handler(500)
async def server_error(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "El Oráculo está en silencio. Intentá de nuevo."}
    )
