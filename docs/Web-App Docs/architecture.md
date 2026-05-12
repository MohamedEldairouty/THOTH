# THOTH Architecture

```
Frontend (React/Vite/TS)          Backend (FastAPI/Python)         Database (PostgreSQL)
┌─────────────────────┐           ┌─────────────────────┐         ┌──────────────────┐
│  Pages              │           │  routers/           │         │  exhibits        │
│  ├ HomePage         │  HTTP     │  ├ exhibits.py       │  ORM    │  categories      │
│  ├ ExhibitsPage     │ ────────► │  ├ categories.py     │ ──────► │  halls           │
│  ├ ExhibitDetail    │  /api/*   │  ├ halls.py          │         │  media           │
│  ├ MapPage          │           │  ├ chat.py           │         │  chat_sessions   │
│  ├ ChatPage         │           │  ├ map.py            │         │  chat_messages   │
│  └ SettingsPage     │           │  ├ robot.py          │         │  robot_status    │
│                     │           │  └ navigation.py     │         │  nav_requests    │
│  services/api.ts    │           │                     │         └──────────────────┘
│  (axios wrappers)   │           │  services/          │
│                     │           │  (business logic)   │         External (future)
│  hooks/             │           │                     │         ┌──────────────────┐
│  ├ useLanguage      │           │  models/            │         │  LLM API         │
│                     │           │  schemas/           │         │  STT/TTS         │
│  Language resolved  │           │                     │         │  ROS2/Nav2       │
│  by backend         │           │  ?lang=en|ar|fr      │         └──────────────────┘
└─────────────────────┘           └─────────────────────┘
```

## Key Decisions

1. **Language resolution is server-side** — frontend sends `?lang=en` and receives a single `title`, `description`, `audio_url`. No language branching in frontend components.

2. **AI is backend-only** — `POST /api/chat` is the only AI surface. `chat_service.py` calls the LLM; the frontend never calls any AI provider directly.

3. **Simulated navigation** — Robot/navigation endpoints exist and return real DB state, but path planning is stubbed. Replacing the stub with ROS2 calls requires changes only in `navigation_service.py` and `robot_service.py`.

4. **Layer boundaries**:
   - routers → schemas (request/response validation)
   - routers → services (business logic)
   - services → models (DB queries via SQLAlchemy)
   - No direct DB queries in routers.
