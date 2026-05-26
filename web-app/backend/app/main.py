from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "THOTH Museum API"}
