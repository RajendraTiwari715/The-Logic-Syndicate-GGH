# Intelligent Border Video Analytics Platform (IBVAP)

This repository contains the full-stack implementation of the IBVAP platform for AI-Based Border Surveillance (Problem Statement 26187, Sashastra Seema Bal).

The platform uses existing IP CCTV infrastructure without dedicated AI camera hardware to detect threats dynamically via centralized ML engines, with edge tolerance and permissioned blockchain evidence ledgers.

## Implementation Status
The backend logic structure is **Complete (CODE-VERIFIED)**.
Due to lack of local Docker availability (PostgreSQL, Minio, Redis cannot run on standard Windows shell without hypervisors available in this instance), the core application is constrained strictly to **Offline/Dry-Run states**. 
We built an extensive offline-fallback edge queue (`offline_sync.py`) to buffer events locally over HTTP boundaries and a pure local hash-chain (`ledger.json`) as a workaround to missing infrastructure.

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
