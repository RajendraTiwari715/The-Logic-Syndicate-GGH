# The Logic Syndicate - GGH 🛡️
### Intelligent Border Video Analytics Platform (IBVAP)

[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-blue?logo=typescript)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8n-FF5722?logo=ultralytics)](https://github.com/ultralytics/ultralytics)
[![Vite](https://img.shields.io/badge/Vite-5.4-purple?logo=vite)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An advanced, military-grade border surveillance and video intelligence platform engineered by **The Logic Syndicate**. The platform dynamically monitors border zones using existing IP camera infrastructures, applying centralized ML vision models, perimeter intrusion detection, automated number plate recognition (ANPR), facial identification, and permissioned cryptographic blockchain evidence ledgers for tamper-evident audit trails.

---

## 🚀 Key Modules & Capabilities

- **🛰️ Multi-Camera Live Surveillance Console**: Real-time multi-camera stream grids with pan-tilt-zoom, interactive layout switching, and tactical focus views.
- **🚨 Global Threat Alarm & Siren System**: Immediate threat escalation engine featuring visual alerts, audio sirens, and border patrol deployment dispatch.
- **🚗 Automated Number Plate Recognition (ANPR)**: Real-time vehicle classification, license plate extraction, speed profiling, and suspect vehicle watchlist verification.
- **👤 Facial Recognition & Access Control**: Face ID logging, blacklist / whitelist screening, and biometric event timestamps.
- **🚧 Virtual Geofencing & Intrusion Detection**: Customizable tripwire and polygon geofencing boundaries with breach detection alerts.
- **📊 Behavioral Anomaly Detection**: AI detection of crawling, weapon wielding, crowd formation, and suspicious border crossing activities.
- **⛓️ Immutable Blockchain Evidence Ledger**: SHA-256 cryptographic hash-chained audit trail guaranteeing evidence integrity for all security incidents.
- **📡 Camera Network Health Diagnostics**: Real-time latency tracking, RTSP stream health, signal status, and offline fallback telemetry.
- **⚡ Offline Edge Queue Synchronization**: Resilient local event buffering ensuring zero telemetry data loss during connectivity dropouts.

---

## 🛠️ Full-Stack Technology Stack

### Frontend Intelligence Console
- **Framework**: [React 18](https://react.dev/) + [Vite](https://vitejs.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + Custom Glassmorphic Dark Tactical UI
- **Mapping & Geospatial**: [Leaflet](https://leafletjs.com/) / [React-Leaflet](https://react-leaflet.js.org/)
- **Charts & Telemetry**: [Recharts](https://recharts.org/)
- **Iconography**: [Lucide React](https://lucide.dev/)
- **Authentication**: Firebase Auth + JWT Bearer Tokens

### Backend Services & Vision Engine
- **Web API Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous ASGI)
- **Computer Vision & ML**: PyTorch, OpenCV, YOLOv8 (`ultralytics`), EasyOCR
- **Database & ORM**: SQLAlchemy 2.0, SQLite / PostgreSQL, Alembic migrations
- **Caching & Message Broker**: Redis Pub/Sub, Multi-process Worker Pool
- **Audit & Evidence Integrity**: SHA-256 Cryptographic Hash-Chain Ledger
- **Storage**: Local Evidence Cache + S3 / MinIO Object Storage

---

## 📁 Repository Structure

```text
The-Logic-Syndicate-GGH/
├── backend/                    # Python FastAPI & AI vision services
│   ├── alembic/                # Relational database schema migrations
│   ├── app/
│   │   ├── api/                # FastAPI v1 endpoints & router mounts
│   │   │   └── routers/        # Auth, Cameras, Alerts, Analytics, Streams, Zones
│   │   ├── core/               # App configuration, security, Redis, worker pool
│   │   ├── database/           # Engine setup and ORM base classes
│   │   ├── models/             # SQLAlchemy entity definitions & schemas
│   │   ├── schemas/            # Pydantic request/response validation schemas
│   │   ├── services/           # ANPR, Audit, Incident engine, Ledger, CCTV connectors
│   │   ├── vision/             # YOLO detector, ByteTrack, ANPR OCR, Zone rules
│   │   └── websocket/          # Real-time WebSocket connection manager
│   ├── data/                   # ANPR captures, edge queue, evidence cache, ledger
│   ├── tests/                  # Automated integration & unit test suites
│   ├── yolov8n.pt              # Pre-trained YOLO weights
│   ├── main.py                 # Backend application entrypoint
│   └── requirements.txt        # Python package dependencies
├── public/                     # Static border footage, patrol snapshots & assets
├── src/                        # React TypeScript frontend console
│   ├── components/             # Reusable tactical UI components
│   │   ├── CameraFeed.tsx      # Video player & stream viewer
│   │   ├── GlobalAlarm.tsx     # Perimeter intrusion sirens & alerts
│   │   ├── Layout.tsx          # Main tactical navigation shell
│   │   ├── ModeSelector.tsx    # Multi-view grid switcher
│   │   ├── RecentVehicleLog.tsx# License plate tracking widget
│   │   └── VehiclesDetected.tsx# Vehicle metrics card
│   ├── context/
│   │   └── AuthContext.tsx     # Operator authentication state
│   ├── data/
│   │   └── demoData.ts         # Surveillance telemetry & camera datasets
│   ├── hooks/
│   │   └── useSurveillanceLogic.ts # Real-time event simulation hooks
│   ├── lib/
│   │   ├── api.ts              # API client endpoints
│   │   └── firebase.ts         # Firebase configuration
│   ├── pages/                  # Security intelligence dashboards
│   │   ├── ANPR.tsx            # Number plate recognition console
│   │   ├── BlockchainLedger.tsx# Cryptographic audit logs
│   │   ├── CameraHealth.tsx    # Stream status & diagnostics
│   │   ├── Cameras.tsx         # Camera registry & management
│   │   ├── Events.tsx          # Real-time incident logs
│   │   ├── FaceAccess.tsx      # Biometric access logs
│   │   ├── FaceDetection.tsx   # Live facial classification
│   │   ├── Home.tsx            # Welcome & navigation portal
│   │   ├── IntrusionLogs.tsx   # Border breach history
│   │   ├── LiveSurveillance.tsx# Tactical multi-feed operations
│   │   ├── Login.tsx           # Operator authentication portal
│   │   ├── Overview.tsx        # High-level mission command center
│   │   ├── PeopleDetected.tsx  # Pedestrian detection analytics
│   │   ├── SuspiciousActivity.tsx # Anomaly detection view
│   │   ├── Tracking.tsx        # Target trajectory tracking
│   │   ├── VehicleDetection.tsx# Vehicle statistics & metrics
│   │   └── VirtualFences.tsx   # Geofence boundary configuration
│   ├── store.tsx               # Global surveillance state management
│   ├── types.ts                # TypeScript domain models
│   ├── App.tsx                 # Root router & layout orchestrator
│   └── main.tsx                # Application entrypoint
├── index.html                  # HTML5 application shell
├── package.json                # Project dependencies and npm scripts
├── tailwind.config.js          # Tailwind theme configuration
├── tsconfig.json               # TypeScript configuration
└── vite.config.ts              # Vite bundler configuration
```

---

## ⚡ Quick Start

### 1. Frontend Setup
```bash
# Clone the repository
git clone https://github.com/RajendraTiwari715/The-Logic-Syndicate-GGH.git

# Navigate into project directory
cd The-Logic-Syndicate-GGH

# Install frontend dependencies
npm install

# Start Vite development server
npm run dev
```

The operator console will be live at `http://localhost:5173`.

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux / macOS

# Install Python dependencies
pip install -r requirements.txt

# Run database setup & camera seeders
python init_db.py
python seed_cameras.py

# Launch FastAPI ASGI server
python main.py
```

FastAPI Swagger Documentation will be accessible at `http://localhost:8000/docs`.

---

## 👥 Developed By
**The Logic Syndicate** — Built for GGH (Grand Global Hackathon) / Border Security Operations.