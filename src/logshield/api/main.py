"""
FastAPI REST API Application for LogShield
"""


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from .routes import errors, health, logs, security, stats, traffic

app = FastAPI(
    title="LogShield API",
    description="Distributed Log Analytics & Security Detection Platform REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for browser dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers with /api prefix
app.include_router(health.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(traffic.router, prefix="/api")
app.include_router(errors.router, prefix="/api")
app.include_router(security.router, prefix="/api")
app.include_router(logs.router, prefix="/api")

@app.get("/")
def root_redirect():
    """Root redirect indicator."""
    return {
        "platform": "LogShield",
        "version": "1.0.0",
        "status": "operational",
        "api_docs": "/docs",
        "health_check": "/api/health"
    }

def start_server(host: str = None, port: int = None, reload: bool = None) -> None:
    """Launches the Uvicorn ASGI server."""
    import uvicorn
    h = host or settings.API_HOST
    p = port or settings.API_PORT
    r = reload if reload is not None else settings.API_RELOAD
    uvicorn.run("src.logshield.api.main:app", host=h, port=p, reload=r)
