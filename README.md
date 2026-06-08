# AI Integration Engineer Platform

A production-grade, AI-powered Enterprise Integration Engineering Platform. Modular, plugin-based, full-stack application that acts as an intelligent integration engineer for enterprise middleware, transformation, EDI, APIs, and mapping technologies.

## Current Focus: IBM Sterling Transformation Extender (ITX)

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (for PostgreSQL + ChromaDB)

### 1. Start Infrastructure
```bash
docker-compose up -d
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
cp ../.env.example ../.env   # Edit with your API keys
python -m alembic upgrade head
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Architecture

```
User Interface (Next.js)
        ↓
   FastAPI Backend
        ↓
  AI Orchestrator / Plugin Router
        ↓
┌──────────────────────────────────┐
│  IBM ITX Plugin                  │
│  ├── Function Explainer          │
│  ├── Type Tree Builder           │
│  ├── Mapping Assistant           │
│  ├── Rule Generator              │
│  ├── Debugging Engine            │
│  ├── Test Data Generator         │
│  └── Artifact Comparator         │
├──────────────────────────────────┤
│  RAG Knowledge Base (ChromaDB)   │
│  Training Guidance AI            │
│  Feedback Learning Engine        │
│  Documentation Generator         │
│  Admin Dashboard                 │
└──────────────────────────────────┘
```

## Plugin Architecture

Future plugins (architecture ready):
- IBM ACE | IBM MQ | SAP IDoc
- EDI X12 | EDIFACT
- API Mapping | DB Mapping | Kafka

## License
Proprietary — Enterprise Internal Use
