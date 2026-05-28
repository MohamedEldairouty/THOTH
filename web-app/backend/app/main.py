import sys

# ──────────────────────────────────────────────────────────────────────
# Force UTF-8 on stdout/stderr BEFORE any other import.
# On Windows, when uvicorn is launched from a .bat with `>> logfile`,
# Python falls back to cp1252 and crashes on any non-ASCII char
# (Arabic transcript, em-dash, etc.) → 500 Internal Server Error.
# Setting errors='replace' guarantees no print() can ever crash the
# request handler, regardless of dynamic content.
# ──────────────────────────────────────────────────────────────────────
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import exhibits, categories, halls, chat, map, robot, navigation, tours
from app.services import ros_service

app = FastAPI(
    title="THOTH Smart Museum Guide API",
    description="Backend API for the Grand Egyptian Museum smart guide system.",
    version="1.0.0",
    # Disable trailing-slash redirects. Behind ngrok HTTPS the absolute Location
    # header pointed at http://localhost:8001 and the browser upgraded it to
    # https://, causing SSL_PROTOCOL_ERROR on mobile.
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes (must be registered BEFORE the catch-all SPA mount) ──────
app.include_router(exhibits.router, prefix="/api/exhibits", tags=["Exhibits"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(halls.router, prefix="/api/halls", tags=["Halls"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(map.router, prefix="/api/map", tags=["Map"])
app.include_router(robot.router, prefix="/api/robot", tags=["Robot"])
app.include_router(navigation.router, prefix="/api/navigation", tags=["Navigation"])
app.include_router(tours.router, prefix="/api/tours", tags=["Tours"])


@app.on_event("startup")
def _startup_ros_bridge():
    """Bring the ROS bridge up immediately so AMCL gets its initial pose
    BEFORE the first user click. Without this, the first tour/navigate-here
    fired a goal at bt_navigator before AMCL had established map→odom and
    every goal got rejected for a missing transform."""
    try:
        ros_service.init_eager()
    except Exception as e:
        print(f"[startup] ros_service.init_eager() failed: {e}")


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "THOTH Museum API"}


# ──────────────────────────────────────────────────────────────────────
# SPA static-file serving for production
#
# When the React frontend is built (`npm run build` inside web-app/frontend),
# we serve `frontend/dist/` directly from FastAPI. This means:
#   - one port (8001) for both API and UI
#   - one Cloudflare/ngrok tunnel exposes the whole app
#   - no CORS issues — frontend and API share an origin
#
# In dev (no `dist/` folder), this block is a no-op; you keep using
# `npm run dev` on :5173 with Vite's /api proxy to :8001.
# ──────────────────────────────────────────────────────────────────────


class SPAStaticFiles(StaticFiles):
    """Serve a SPA: any 404 inside the static directory falls back to
    index.html so React Router deep-links work after a hard refresh."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists() and (_FRONTEND_DIST / "index.html").exists():
    print(f"[main] Serving frontend from {_FRONTEND_DIST}")
    app.mount(
        "/",
        SPAStaticFiles(directory=str(_FRONTEND_DIST), html=True),
        name="frontend",
    )
else:
    print(f"[main] No frontend build found at {_FRONTEND_DIST} -- dev mode only.")
