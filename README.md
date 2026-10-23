# Intelligent Border Video Analytics Platform (IBVAP)

This repository contains the full-stack implementation of the IBVAP platform for AI-Based Border Surveillance (Problem Statement 26187, Sashastra Seema Bal).

The platform uses existing IP CCTV infrastructure without dedicated AI camera hardware to detect threats dynamically via centralized ML engines, with edge tolerance and permissioned blockchain evidence ledgers.

## Implementation Status
The backend logic structure is **Complete (CODE-VERIFIED)**.

## Run the application with Docker Desktop

With Docker Desktop running, start the API and its Postgres, Redis, and MinIO services from the project root:

```bash
docker compose up -d --build
docker compose ps
```

The API is available at `http://localhost:8000` (health: `http://localhost:8000/health`, docs: `http://localhost:8000/docs`). Start the Vite frontend separately with `npm run dev`; it defaults to that API address. To stop the containers, run `docker compose down`. Persistent service and backend data remains in Docker volumes. Environments without these services can still use the offline queue and local evidence ledger.

## Stack
- **Frontend**: React + Vite + TailwindCSS + Zustand
- **Backend API**: FastAPI + Uvicorn
- **Database Model**: SQLAlchemy ORM (PostgreSQL targeted)
- **AI Analytics**: PyTorch/OpenCV (YOLO-based modular adapters)
- **Edge Integrity**: Local File Ledger & UUIDv7-oriented SHA-256 chains.

## Project Structure
- `backend/app/api`: FastAPI Routers
- `backend/app/models`: Complete SQLAlchemy Database definitions (`core_models.py`)
- `backend/app/services`: Offline Queues, Multi-Camera Timelines, Alert Deduplication, Ledger
- `backend/app/vision`: AI Tracker rules and Detection processing pipelines
- `src/pages`: Frontend intelligence dashboards and React layouts

## Local Setup
See `docs/deployment.md` for infrastructure startup sequence once Docker relies are unblocked.
