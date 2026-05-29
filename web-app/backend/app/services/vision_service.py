"""
Vision service — runtime face → age + mood inference for THOTH.

What this module does
─────────────────────
- Loads the two PyTorch checkpoints produced by `web-app/backend/training/`:
  • `models/age_resnet50.pth`         — timm ResNet50, 4-class age buckets
  • `models/emotion_efficientnet.pth` — torchvision EfficientNet-B0, 7 emotions
- Crops the largest face out of an incoming JPEG using OpenCV's bundled
  Haar cascade (no extra weights to ship).
- Runs both heads on the same crop, returns ONE stable dict:

    {
      "face_detected": True,
      "age": 28,                 # integer "anchor" age within the bucket
      "age_group": "adult",      # child | teen | adult | senior
      "age_confidence": 0.74,
      "mood": "happy",           # angry | disgust | fear | happy | sad | surprise | neutral
      "mood_confidence": 0.81,
      "source": "local",         # "local" (webcam) | "ros" (future bridge)
      "ts": 1717012345.67,
      "latency_ms": 42
    }

- Keeps the latest profile in `_latest_profile` so:
  • chat_service can read it without an HTTP roundtrip.
  • the ROS bridge can overwrite it (Phase F) without any other code change.

Design rules
────────────
- **Lazy load**: models load on the first call, not on uvicorn boot. The
  /api/health endpoint stays fast and the demo machine doesn't spend GPU
  RAM if no one ever opens the camera.
- **Thread-safe**: a single lock guards both the load-once path AND the
  shared cache. FastAPI's threadpool can hit us from multiple workers.
- **Provider-agnostic dict**: every consumer (LLM prompt, frontend chip,
  ROS bridge) sees the same shape. Swap the underlying model files and
  nothing downstream changes.

Run-flag: settings.VISION_ENABLED — when false, `analyze()` returns a
disabled-stub instead of loading anything.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import settings


# ─────────────────────────────────────────────────────────────────────────
# Paths & constants
# ─────────────────────────────────────────────────────────────────────────

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_MODELS_DIR  = _BACKEND_DIR / "models"

AGE_WEIGHTS     = _MODELS_DIR / "age_resnet50.pth"
EMOTION_WEIGHTS = _MODELS_DIR / "emotion_efficientnet.pth"

# Must match training/train_age_resnet.py exactly.
AGE_CLASS_SLUGS  = ["child", "teen", "adult", "senior"]
# Representative "anchor" age we surface to the LLM. The prompt only needs
# a rough number to set tone — never a calibrated estimate.
AGE_ANCHOR       = {"child": 8, "teen": 16, "adult": 32, "senior": 65}

# Must match training/train_emotion_efficientnet.py exactly.
EMOTION_CLASSES  = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD  = [0.229, 0.224, 0.225]
IMG_SIZE  = 224


# ─────────────────────────────────────────────────────────────────────────
# Shared profile cache  (read by chat_service, written by /api/vision +
# future ROS bridge)
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class VisionProfile:
    face_detected: bool
    age: Optional[int]
    age_group: Optional[str]
    age_confidence: Optional[float]
    mood: Optional[str]
    mood_confidence: Optional[float]
    source: str           # "local" | "ros" | "disabled" | "no_face"
    ts: float
    latency_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


_lock: threading.RLock = threading.RLock()
_latest_profile: Optional[VisionProfile] = None

# Lazy singletons populated by _ensure_loaded()
_age_model = None
_emotion_model = None
_face_cascade = None
_torch = None     # imported lazily so module import stays cheap
_cv2 = None
_device = None
_transform = None


# ─────────────────────────────────────────────────────────────────────────
# Lazy initialisation
# ─────────────────────────────────────────────────────────────────────────

def _resolve_device(torch_mod):
    pref = (settings.VISION_DEVICE or "auto").strip().lower()
    if pref == "cpu":
        return torch_mod.device("cpu")
    if pref == "cuda":
        if torch_mod.cuda.is_available():
            return torch_mod.device("cuda")
        print("[vision] VISION_DEVICE=cuda but no CUDA available -> falling back to cpu")
        return torch_mod.device("cpu")
    # auto
    return torch_mod.device("cuda" if torch_mod.cuda.is_available() else "cpu")


def _build_age_model(torch_mod, nn_mod):
    """Re-create the architecture used in training/train_age_resnet.py."""
    import timm
    model = timm.create_model("resnet50", pretrained=False, num_classes=0)
    model.fc = nn_mod.Sequential(
        nn_mod.Dropout(p=0.4),
        nn_mod.Linear(model.num_features, len(AGE_CLASS_SLUGS)),
    )
    return model


def _build_emotion_model(nn_mod):
    """Re-create the architecture used in training/train_emotion_efficientnet.py."""
    from torchvision import models as tvm
    model = tvm.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn_mod.Sequential(
        nn_mod.Dropout(0.5),
        nn_mod.Linear(in_features, len(EMOTION_CLASSES)),
    )
    return model


def _ensure_loaded() -> bool:
    """Load both models + the face detector on first use.
    Returns True on success, False if weights are missing or import fails."""
    global _age_model, _emotion_model, _face_cascade
    global _torch, _cv2, _device, _transform

    if _age_model is not None and _emotion_model is not None:
        return True

    with _lock:
        if _age_model is not None and _emotion_model is not None:
            return True

        if not AGE_WEIGHTS.exists() or not EMOTION_WEIGHTS.exists():
            print(f"[vision] weights missing — age={AGE_WEIGHTS.exists()} "
                  f"emotion={EMOTION_WEIGHTS.exists()}. Vision disabled.")
            return False

        try:
            import torch
            import torch.nn as nn
            import cv2
            from torchvision import transforms as T
        except Exception as e:
            print(f"[vision] import error: {e}. Vision disabled.")
            return False

        _torch  = torch
        _cv2    = cv2
        _device = _resolve_device(torch)
        print(f"[vision] loading models on {_device} ...")
        t0 = time.time()

        # Age model
        age_model = _build_age_model(torch, nn)
        age_state = torch.load(AGE_WEIGHTS, map_location=_device, weights_only=True)
        age_model.load_state_dict(age_state)
        age_model.eval().to(_device)

        # Emotion model
        emo_model = _build_emotion_model(nn)
        emo_state = torch.load(EMOTION_WEIGHTS, map_location=_device, weights_only=True)
        emo_model.load_state_dict(emo_state)
        emo_model.eval().to(_device)

        # Haar cascade ships inside opencv-python-headless wheel
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(str(cascade_path))
        if cascade.empty():
            print(f"[vision] failed to load Haar cascade from {cascade_path}")
            return False

        # Shared eval transform — covers BOTH models. The emotion training
        # script grayscale-upcasted its 1-channel inputs to 3 channels with
        # ImageNet stats, which numerically matches feeding it the same RGB
        # crop we feed the age model. So one transform fits both.
        transform = T.Compose([
            T.ToPILImage(),
            T.Resize((IMG_SIZE, IMG_SIZE)),
            T.ToTensor(),
            T.Normalize(NORM_MEAN, NORM_STD),
        ])

        _age_model     = age_model
        _emotion_model = emo_model
        _face_cascade  = cascade
        _transform     = transform

        print(f"[vision] models ready in {time.time()-t0:.2f}s "
              f"(age={AGE_WEIGHTS.name}, emotion={EMOTION_WEIGHTS.name})")
        return True


# ─────────────────────────────────────────────────────────────────────────
# Face detection + inference
# ─────────────────────────────────────────────────────────────────────────

def _decode_jpeg(jpeg_bytes: bytes) -> Optional[np.ndarray]:
    """Decode a JPEG payload to a BGR ndarray. Returns None on failure."""
    if not jpeg_bytes:
        return None
    buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = _cv2.imdecode(buf, _cv2.IMREAD_COLOR)
    return img


def _largest_face(bgr: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    """Return (x, y, w, h) of the largest face, or None if no face."""
    gray = _cv2.cvtColor(bgr, _cv2.COLOR_BGR2GRAY)
    # Tuned for laptop webcam framing (visitor ~30-80cm away).
    faces = _face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.15,
        minNeighbors=5,
        minSize=(80, 80),
    )
    if len(faces) == 0:
        return None
    # Largest by area
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    return tuple(int(v) for v in faces[0])


def _run_models(face_rgb: np.ndarray) -> tuple[int, float, int, float]:
    """Forward pass on both heads. Returns (age_idx, age_conf, emo_idx, emo_conf)."""
    tensor = _transform(face_rgb).unsqueeze(0).to(_device)
    with _torch.no_grad():
        age_logits = _age_model(tensor)
        emo_logits = _emotion_model(tensor)
        age_probs  = _torch.softmax(age_logits, dim=1)[0]
        emo_probs  = _torch.softmax(emo_logits, dim=1)[0]
    age_idx  = int(age_probs.argmax().item())
    age_conf = float(age_probs[age_idx].item())
    emo_idx  = int(emo_probs.argmax().item())
    emo_conf = float(emo_probs[emo_idx].item())
    return age_idx, age_conf, emo_idx, emo_conf


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────

def analyze(jpeg_bytes: bytes) -> VisionProfile:
    """Run age + mood inference on a single JPEG frame.

    Always returns a VisionProfile (never raises). The 'source' field tells
    callers whether the result is real, disabled, or a no-face stub.
    Side effect: updates the shared `_latest_profile` cache."""
    now = time.time()

    if not settings.VISION_ENABLED:
        profile = VisionProfile(
            face_detected=False, age=None, age_group=None, age_confidence=None,
            mood=None, mood_confidence=None,
            source="disabled", ts=now, latency_ms=0.0,
        )
        _set_cached_profile(profile)
        return profile

    if not _ensure_loaded():
        profile = VisionProfile(
            face_detected=False, age=None, age_group=None, age_confidence=None,
            mood=None, mood_confidence=None,
            source="disabled", ts=now, latency_ms=0.0,
        )
        _set_cached_profile(profile)
        return profile

    t0 = time.time()
    bgr = _decode_jpeg(jpeg_bytes)
    if bgr is None:
        profile = VisionProfile(
            face_detected=False, age=None, age_group=None, age_confidence=None,
            mood=None, mood_confidence=None,
            source="local", ts=now, latency_ms=(time.time() - t0) * 1000.0,
        )
        _set_cached_profile(profile)
        return profile

    face_box = _largest_face(bgr)
    if face_box is None:
        profile = VisionProfile(
            face_detected=False, age=None, age_group=None, age_confidence=None,
            mood=None, mood_confidence=None,
            source="no_face", ts=now, latency_ms=(time.time() - t0) * 1000.0,
        )
        _set_cached_profile(profile)
        return profile

    x, y, w, h = face_box
    # Pad ~15% around the box so the face isn't cropped at the chin/forehead;
    # both models were trained on slightly looser crops than Haar emits.
    pad = int(0.15 * max(w, h))
    H, W = bgr.shape[:2]
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(W, x + w + pad)
    y1 = min(H, y + h + pad)
    face_bgr = bgr[y0:y1, x0:x1]
    face_rgb = _cv2.cvtColor(face_bgr, _cv2.COLOR_BGR2RGB)

    age_idx, age_conf, emo_idx, emo_conf = _run_models(face_rgb)
    age_group = AGE_CLASS_SLUGS[age_idx]

    profile = VisionProfile(
        face_detected=True,
        age=AGE_ANCHOR[age_group],
        age_group=age_group,
        age_confidence=age_conf,
        mood=EMOTION_CLASSES[emo_idx],
        mood_confidence=emo_conf,
        source="local",
        ts=now,
        latency_ms=(time.time() - t0) * 1000.0,
    )
    _set_cached_profile(profile)
    return profile


def get_latest_profile(max_age_s: Optional[float] = None) -> Optional[VisionProfile]:
    """Return the most recent profile, or None if there isn't one or it's stale.
    `max_age_s=None` uses settings.VISION_PROFILE_TTL_S. Pass 0 to disable TTL."""
    with _lock:
        if _latest_profile is None:
            return None
        ttl = settings.VISION_PROFILE_TTL_S if max_age_s is None else max_age_s
        if ttl and (time.time() - _latest_profile.ts) > ttl:
            return None
        return _latest_profile


def push_ros_profile(*, age_group: str, mood: str, age_confidence: float = 1.0,
                     mood_confidence: float = 1.0) -> VisionProfile:
    """Write path for the future ROS bridge (Phase F).

    The vision team's ROS nodes will publish on /age and /mood. The bridge
    callback will convert their messages into this call so the cache shape
    stays identical to the webcam path."""
    if age_group not in AGE_CLASS_SLUGS:
        age_group = "adult"
    if mood not in EMOTION_CLASSES:
        mood = "neutral"
    profile = VisionProfile(
        face_detected=True,
        age=AGE_ANCHOR[age_group],
        age_group=age_group,
        age_confidence=age_confidence,
        mood=mood,
        mood_confidence=mood_confidence,
        source="ros",
        ts=time.time(),
        latency_ms=None,
    )
    _set_cached_profile(profile)
    return profile


def diagnostics() -> dict:
    """Small snapshot useful for /api/vision/profile and ad-hoc debugging."""
    with _lock:
        latest = _latest_profile.to_dict() if _latest_profile else None
    return {
        "enabled":        settings.VISION_ENABLED,
        "device_pref":    settings.VISION_DEVICE,
        "models_loaded":  _age_model is not None and _emotion_model is not None,
        "age_weights":    str(AGE_WEIGHTS),
        "age_weights_ok": AGE_WEIGHTS.exists(),
        "emotion_weights":    str(EMOTION_WEIGHTS),
        "emotion_weights_ok": EMOTION_WEIGHTS.exists(),
        "profile_ttl_s":  settings.VISION_PROFILE_TTL_S,
        "latest_profile": latest,
    }


# ─────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────

def _set_cached_profile(profile: VisionProfile) -> None:
    global _latest_profile
    with _lock:
        _latest_profile = profile
