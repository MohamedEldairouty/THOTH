# THOTH — Smart Museum Guide

> Graduation Project — Full-Stack Touchscreen Web Application
> Grand Egyptian Museum Theme

## Overview

THOTH is an AI-powered smart museum guide designed for the Grand Egyptian Museum. It provides interactive exhibit browsing, multilingual support (EN / AR / FR), an AI chatbot, an interactive museum map, and a simulated robot navigation layer ready for future ROS2 integration.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| AI Integration | OpenAI / Gemini / Whisper (via backend) |
| Future | ROS2 / Nav2 / Docker / AWS |

---

## Repository Structure

```
thoth-smart-museum-guide/
├── frontend/         React + Vite + TypeScript frontend
├── backend/          FastAPI REST API backend
├── ai-service/       LLM / STT / TTS integration layer
├── docs/             Architecture and API documentation
├── demo-assets/      Screenshots, videos for presentation
└── docker-compose.yml
```

---

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in your DB credentials
alembic upgrade head
uvicorn app.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at: `http://localhost:5173`

---

## Features

- Home / Welcome Page with THOTH introduction
- Exhibit Browsing with search, category, era, and hall filters
- Exhibit Details with multilingual descriptions and media
- Interactive Museum Map with simulated robot location
- AI Chatbot Interface (text + voice placeholder)
- Accessibility settings (language, font scale, captions)

---

## Architecture Principles

- Clean separation: models → schemas → routers → services
- Language handled server-side (`?lang=en|ar|fr`)
- AI logic isolated in backend services layer
- Navigation APIs structured for ROS2 integration
- All APIs documented via Swagger at `/docs`
