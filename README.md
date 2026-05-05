# RaceBrain 🏎️

**RaceBrain** is a premium F1 race strategy simulator that models tyre strategy, pit stop timing, Monte Carlo uncertainty, and win probability through a pit wall-inspired analytics dashboard.

The goal is to build a portfolio-grade AI strategy lab: part simulation engine, part race control dashboard, part decision-support system.
---
## Current Features

- FastAPI backend
- React + TypeScript frontend
- Monte Carlo strategy simulation
- Win probability calculation
- Strategy confidence scoring
- Tyre compound and stint modelling
- Pit loss variance
- Premium paddock-style dashboard UI
- Interactive strategy controls
---
## Tech Stack

### Backend
- Python
- FastAPI
- Pydantic
- Pytest

### Frontend
- React
- TypeScript
- Tailwind CSS
- Recharts
- Lucide React
- Vite

## Project Structure

```txt
racebrain/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   └── simulation/
│   └── tests/
├── frontend/
├── data/
├── notebooks/
└── docs/
```
---
## Running Locally
### Backend
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Backend runs on:
```bash
http://127.0.0.1:8000
```

API docs:
```bash
http://127.0.0.1:8000/docs
```
### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs on:
```bash
http://localhost:5173
```
---
## Future Roadmap
- Circuit-specific race profiles
- Real F1 data ingestion
- Tyre degradation modelling
- Weather-aware simulations
- Safety car and race control events
- ML-based lap time prediction
- AI strategy recommendation agent
- Strategy explanation layer
- 'Ferrari Mode' for chaotic pit wall decisions 😂
---
##License
This project is licensed under the MIT License.
