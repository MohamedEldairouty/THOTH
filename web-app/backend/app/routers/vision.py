"""
Vision router — webcam → backend → {age, mood} pipeline.

Endpoints
─────────
POST /api/vision/analyze
    multipart/form-data with a `frame` field (JPEG bytes).
    Runs the face crop + age + emotion models, updates the shared cache,
    returns the VisionProfile dict.

GET  /api/vision/profile
    Returns the most recent cached profile (or null if missing/stale).
    Used by:
      - the React WebcamCard chip to show the inferred age/mood
      - ad-hoc debugging (curl from the terminal)
      - chat_service can also read directly from vision_service for the
        LLM tone hint without going through HTTP.

GET  /api/vision/diagnostics
    "Is vision actually working?" snapshot — weights present, models loaded,
    device, TTL, latest cache. Same spirit as /api/robot/diagnostics.
"""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.services import vision_service

router = APIRouter()


@router.post("/analyze")
async def analyze_frame(frame: UploadFile = File(...)):
    """Run age + mood inference on the uploaded JPEG.

    The frontend POSTs roughly one frame every 3 seconds while the visitor
    is on the chat page. We never store the image — only the inferred
    profile is cached, and even that respects settings.VISION_PROFILE_TTL_S.
    """
    if frame is None:
        raise HTTPException(status_code=400, detail="No 'frame' field in upload")

    data = await frame.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty frame payload")

    profile = vision_service.analyze(data)
    return profile.to_dict()


@router.get("/profile")
def latest_profile():
    """Most recent cached profile, or null if missing / older than TTL."""
    profile = vision_service.get_latest_profile()
    if profile is None:
        return {"profile": None}
    return {"profile": profile.to_dict()}


@router.get("/diagnostics")
def diagnostics():
    """Backend's view of the vision pipeline — for the same 'is it actually
    LIVE?' kind of debugging we already do for ROS."""
    return vision_service.diagnostics()
