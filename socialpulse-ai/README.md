# SOCIALPULSE AI

SOCIALPULSE AI is a planned React and FastAPI platform for CSV-based social media
trend, sentiment, hashtag, and engagement analysis.

## Phase 1: Architecture

- React 19, TypeScript, Vite, and Tailwind CSS for the dashboard
- FastAPI and Pydantic for validated REST APIs
- Pandas, NumPy, Scikit-learn, TextBlob, and NLTK for analysis
- SQLite locally and PostgreSQL in production
- SQLAlchemy for database access

## Local setup

### Frontend

```powershell
cd socialpulse-ai/frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Backend

```powershell
cd socialpulse-ai/backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/api/health.
