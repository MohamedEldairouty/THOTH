# Trained vision model weights

This folder holds the `.pth` files produced by
`web-app/backend/training/`.

**Weights themselves are git-ignored** (each is ~17–94 MB). After training
on your machine you'll have:

```
models/
├── age_resnet50.pth                 ← trained, gitignored
├── age_resnet50.meta.json           ← provenance (can commit)
├── emotion_efficientnet.pth         ← trained, gitignored
└── emotion_efficientnet.meta.json   ← provenance (can commit)
```

The backend (`app/services/vision_service.py`) auto-detects these files at
startup. If they're absent the `/api/vision/*` endpoints simply return
`503 Service Unavailable` — the rest of the backend keeps working.

See `../training/README.md` for how to (re)produce them.
