# API Contract

All endpoints are prefixed with `/api`.
Language is passed as `?lang=en|ar|fr` (default: `en`).

## Exhibits

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exhibits?lang=en&search=X&category_id=1&hall_id=2` | List exhibits (localized) |
| GET | `/exhibits/{id}?lang=en` | Get single exhibit (localized) |
| POST | `/exhibits` | Create exhibit (raw multilingual body) |
| PUT | `/exhibits/{id}` | Update exhibit |
| DELETE | `/exhibits/{id}` | Delete exhibit |

**Response (localized):**
```json
{
  "id": 1,
  "title": "Golden Mask of Tutankhamun",
  "short_description": "...",
  "full_description": "...",
  "era": "New Kingdom",
  "category_id": 3,
  "hall_id": 2,
  "image_url": "/assets/exhibits/mask.jpg",
  "audio_url": "/assets/audio/mask_en.mp3",
  "x_position": 45.0,
  "y_position": 30.0,
  "language": "en"
}
```

## Categories & Halls

| Method | Path | Description |
|--------|------|-------------|
| GET | `/categories?lang=en` | List categories |
| GET | `/halls?lang=en` | List halls |

## Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send message, get AI reply |

**Request:**
```json
{ "message": "Tell me about Tutankhamun", "session_id": null, "language": "en", "exhibit_id": 1 }
```

**Response:**
```json
{ "reply": "...", "session_id": 42, "language": "en" }
```

## Map

| Method | Path | Description |
|--------|------|-------------|
| GET | `/map` | Map overview + robot position |
| GET | `/map/exhibits?lang=en` | Exhibit map markers |
| GET | `/map/route?to_exhibit=5` | Simulated route |

## Robot & Navigation (Simulated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/robot/status` | Battery, position, status |
| POST | `/navigation/start` | Start navigation to exhibit |
| POST | `/navigation/stop` | Stop current navigation |
| GET | `/navigation/status` | Current navigation request |
