# SOCIALPULSE AI

SOCIALPULSE AI is a social-media intelligence and trend-analysis internship
project. It includes an original Streamlit dashboard and a modern React +
FastAPI SaaS-style application.

> This is a CSV-based analysis platform. It does not claim live social-media
> monitoring unless an official real-time API is added.

## Features

- CSV dataset upload and validation
- Flexible social-media column mapping
- Text cleaning and duplicate detection
- Topic and hashtag analysis
- Positive, negative, and neutral sentiment analysis
- Platform and engagement comparisons
- Interactive Recharts visualizations
- Automated dataset-grounded insights
- Analytics assistant
- Dataset history and cleaned CSV downloads
- Responsive React dashboard with 28 routed modules
- Existing eight-tab Streamlit dashboard

## Technologies

**Frontend**

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- React Router
- Lucide React
- Framer Motion

**Backend**

- Python
- FastAPI
- Pydantic
- Pandas
- NumPy
- Scikit-learn
- SQLAlchemy
- SQLite
- TextBlob / NLTK

## Project Structure

```text
Social_Media_Trend_Analysis/
├── app.py
├── test_pipeline.py
├── generate_dataset.py
├── requirements.txt
├── dataset/
├── notebooks/
├── outputs/
├── src/
└── socialpulse-ai/
    ├── frontend/
    ├── backend/
    ├── dataset/
    ├── reports/
    ├── tests/
    ├── .env.example
    └── README.md
```

## Bundled Dataset

- Raw CSV rows: 1,265
- Cleaned rows after post-content and post-ID deduplication: 1,211
- Platforms: Instagram, LinkedIn, Twitter/X, and Facebook
- Sentiment: Positive, Negative, and Neutral
- Total engagement is calculated as likes + shares + comments

## Local Installation

### 1. Clone the repository

```powershell
git clone https://github.com/mirshabaz/social-media-trend-analysis.git
cd social-media-trend-analysis
```

### 2. Run the original Streamlit dashboard

```powershell
py -m pip install -r requirements.txt
py test_pipeline.py
py -m streamlit run app.py
```

Open http://localhost:8501.

### 3. Run the React frontend

```powershell
cd socialpulse-ai/frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173.

### 4. Run the FastAPI backend

Open a second terminal:

```powershell
cd socialpulse-ai/backend
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation:

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API health |
| POST | `/api/upload` | Upload and clean a CSV |
| GET | `/api/datasets` | List uploaded datasets |
| GET | `/api/dataset` | Active dataset |
| GET | `/api/dataset/{id}` | Dataset preview |
| POST | `/api/dataset/{id}/activate` | Switch active dataset |
| GET | `/api/dataset/{id}/download` | Download cleaned CSV |
| GET | `/api/overview` | Dashboard KPIs and charts |
| GET | `/api/trends` | Trending topics and hashtags |
| GET | `/api/sentiment` | Sentiment analysis |
| GET | `/api/engagement` | Engagement analysis |
| GET | `/api/platforms` | Platform comparison |
| GET | `/api/insights` | Dataset-generated observations |

## Tests

Run the original pipeline test:

```powershell
py test_pipeline.py
```

Run FastAPI tests:

```powershell
cd socialpulse-ai
py -m pytest tests -v
```

Build the React frontend:

```powershell
cd socialpulse-ai/frontend
npm run build
```

## Environment Variables

Copy `socialpulse-ai/.env.example` to `socialpulse-ai/.env` and replace the
development secret and database settings before deployment.

Never commit real passwords or API keys.

## Deployment

- Frontend: deploy `socialpulse-ai/frontend` to Vercel
- Backend: deploy `socialpulse-ai/backend` to Render
- Database: use PostgreSQL in production and set `DATABASE_URL`
- Set `VITE_API_URL` in the frontend to the public backend URL

## Notes

The dashboard is CSV-driven. Uploaded data is cleaned locally and stored in
SQLite for local development. Demographic claims are not shown unless reliable
demographic columns exist in the source dataset.
