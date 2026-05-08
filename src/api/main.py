from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from ..settings.settings import settings
from .endpoints import router

app = FastAPI(
    title="Clinic AI API", description="Medical AI assistant API", version="2.0"
)

# CORS middleware - allows frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

app.include_router(router)

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the medical app frontend"""
    html_file = static_path / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "Clinic AI API", "docs": "/docs", "health": "/health"}
