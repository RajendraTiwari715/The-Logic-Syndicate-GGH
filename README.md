# The Logic Syndicate - GGH 🛡️
### Intelligent Border Video Analytics Platform (IBVAP)

[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-purple?logo=vite)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An advanced, military-grade border surveillance and video intelligence console engineered by **The Logic Syndicate**. The platform dynamically monitors border zones using existing IP camera infrastructures, applying centralized ML vision models, perimeter intrusion detection, automated number plate recognition (ANPR), facial identification, and permissioned cryptographic blockchain evidence ledgers for tamper-evident audit trails.

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

---

## 🛠️ Tech Stack

- **Framework**: [React 18](https://react.dev/) + [Vite](https://vitejs.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + Custom Glassmorphic Dark Tactical UI
- **Mapping & Geospatial**: [Leaflet](https://leafletjs.com/) / [React-Leaflet](https://react-leaflet.js.org/)
- **Charts & Telemetry**: [Recharts](https://recharts.org/)
- **Iconography**: [Lucide React](https://lucide.dev/)
- **Authentication & Backend Integration**: Firebase + REST API Adapters

---

## 📁 Repository Structure

```text
The-Logic-Syndicate-GGH/
├── public/                     # Static border footage, patrol snapshots & assets
├── src/
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

### Prerequisites
- Node.js (v18 or higher)
- npm or yarn

### Installation
```bash
# Clone the repository
git clone https://github.com/RajendraTiwari715/The-Logic-Syndicate-GGH.git

# Navigate into project directory
cd The-Logic-Syndicate-GGH

# Install dependencies
npm install
```

### Running Locally
```bash
# Start Vite development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser to access the tactical surveillance operator console.

---

## 👥 Developed By
**The Logic Syndicate** — Built for GGH (Grand Global Hackathon) / Border Security Operations.