# Store Analytics — AI-Powered Monitoring Platform

AI-powered presence analytics, employee attendance tracking, and incident detection for restaurants and retail stores using CCTV cameras.

---

## Architecture

```
store-analytics/
├── app/                        # Backend application
│   ├── api/v1/                # FastAPI routers
│   │   ├── employees.py       # Employee CRUD + face upload
│   │   ├── customers.py       # Customer management
│   │   ├── cameras.py         # Camera configuration
│   │   ├── visits.py          # Visit session management
│   │   ├── incidents.py       # Alert/incident management
│   │   └── analytics.py       # Dashboard + reporting endpoints
│   ├── models/                # SQLAlchemy ORM models
│   ├── schemas/               # Pydantic request/response schemas
│   ├── repositories/          # Async DB access layer (CRUD)
│   ├── services/              # Business logic
│   │   ├── identity_service.py   # Face matching + identity resolution
│   │   ├── employee_service.py
│   │   ├── customer_service.py
│   │   ├── visit_service.py
│   │   ├── incident_service.py
│   │   └── analytics_service.py
│   ├── workers/               # Celery background processing
│   │   ├── celery_app.py
│   │   └── tasks.py           # process_video_segment task
│   ├── core/                  # Logging, exceptions
│   ├── config.py              # Pydantic-settings configuration
│   ├── database.py            # Async SQLAlchemy engine
│   └── main.py                # FastAPI app entry point
│
├── vision/                    # Computer vision pipeline
│   ├── pipeline.py            # Orchestrator (batch + live mode)
│   ├── detector.py            # YOLOv8 person + face detection
│   ├── tracker.py             # ByteTrack multi-person tracking
│   ├── recognizer.py          # ArcFace face embedding (insightface)
│   ├── event_detector.py      # Modular incident detection
│   └── video_buffer.py        # Pre-event ring buffer + post-event recorder
│
├── alembic/                   # Database migrations
│   └── versions/0001_initial_schema.py
│
├── scripts/
│   ├── register_employee.py   # CLI: register employee with face photo
│   └── process_video.py       # CLI: submit video for batch processing
│
├── tests/
├── models/                    # YOLOv8 .pt weight files
├── recordings/                # Incident video clips (gitignored)
├── face_db/                   # Employee/customer face photos (gitignored)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Quick Start

### 1. Prerequisites

- Docker + Docker Compose
- Python 3.11+
- NVIDIA GPU (optional, falls back to CPU)

### 2. Setup

```bash
# Copy environment config
cp .env.example .env
# Edit .env if needed (default values work for local Docker setup)

# Start PostgreSQL + Redis
docker-compose up db redis -d

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload
```

### 3. Register an Employee

```bash
python scripts/register_employee.py \
    --name "Ahmed Ali" \
    --role "Cashier" \
    --code "EMP001" \
    --image /path/to/ahmed_face.jpg
```

### 4. Process a Video Segment

```bash
# Enqueue via Celery (requires Redis)
python scripts/process_video.py --video recordings/segment.mp4

# Or run inline (synchronous, for testing)
python scripts/process_video.py --video recordings/segment.mp4 --inline
```

### 5. Start Celery Worker

```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```

### 6. Full Stack with Docker

```bash
docker-compose up --build
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health check |
| POST | `/api/v1/employees/` | Register new employee |
| POST | `/api/v1/employees/{id}/face` | Upload face photo + auto-extract embedding |
| GET | `/api/v1/analytics/dashboard` | Live dashboard snapshot |
| GET | `/api/v1/analytics/daily` | Daily summary |
| GET | `/api/v1/analytics/attendance` | Employee attendance by date |
| GET | `/api/v1/analytics/traffic/hourly` | Hourly visitor traffic chart data |
| GET | `/api/v1/incidents/open` | All pending alerts |
| POST | `/api/v1/incidents/` | Report an incident |

Full interactive docs: **http://localhost:8000/docs**

---

## Identity Resolution Logic

```
Frame → Person Detection (YOLOv8) → ByteTrack (temp track_id)
                                          │
                              Face detected + stable (N frames)?
                                          │ Yes
                              ArcFace embedding (512-dim)
                                          │
                        ┌─────────────────┼──────────────────┐
                        ▼                 ▼                  ▼
                   Employee match    Customer match     No match
                   (cosine ≥ 0.55)  (cosine ≥ 0.55)       │
                        │                 │            Unknown accumulator
                   Open Employee     Increment              │
                     Visit           visit_count     appearances ≥ 2?
                                          │                 │ Yes
                                    Promote to         Create Customer
                                    recurring?          profile + Visit
```

- **track_id** = temporary, valid only within one video session
- **DB UUID** = permanent, persists across sessions
- Unknown visitors accumulate appearances before becoming customer profiles

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + uvicorn |
| Database | PostgreSQL 16 + asyncpg + SQLAlchemy 2.0 |
| Migrations | Alembic |
| Queue | Celery + Redis |
| Person detection | YOLOv8m (ultralytics) |
| Face detection | YOLOv8s (custom face model) |
| Face recognition | insightface ArcFace (buffalo_l) |
| Tracking | ByteTrack (via boxmot) |
| Config | pydantic-settings |
| Logging | structlog |

---

## Two Processing Modes

**Batch Mode (default for MVP):**
- Record 30–60 min video segments
- Process after recording completes
- Analytics delayed by segment length (acceptable for MVP)
- Lower compute pressure

**Live Mode (lightweight):**
- Continuous frame processing
- Instant incident alerts (fire, fight detection)
- Full identity analytics can be skipped or throttled

---

## Extending the System

**Add a new event detector:**
```python
# vision/event_detector.py
class MyCustomDetector(BaseEventDetector):
    def detect(self, frame: np.ndarray) -> EventResult | None:
        # your model here
        ...

# Register it
pipeline.add(MyCustomDetector())
```

**Add a new API module:**
```python
# app/api/v1/my_feature.py, then in router.py:
api_router.include_router(my_feature.router, prefix="/my-feature", tags=["MyFeature"])
```

---

## Phase Roadmap

- [x] **Phase 1** — Core infrastructure, DB models, FastAPI backend, vision pipeline
- [ ] **Phase 2** — Dashboard frontend (React/Next.js), recurring customer analytics
- [ ] **Phase 3** — WebSocket live updates, pgvector face search, AI chat assistant
