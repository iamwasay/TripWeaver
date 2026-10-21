# TripWeaver: Multi-Agent Budget Travel Planner

TripWeaver is a collaborative AI system that turns user travel preferences, dates, and budgets into a complete, practical trip plan. It uses a shared state and a central Orchestrator (built with LangGraph) to coordinate specialized agents.

## 🚀 Features
- **Multi-Agent Architecture:** 8 distinct agents handle specialized tasks (Input, Flight, Stay, Activities, Weather, Budget, Verification, Itinerary).
- **Deterministic Budgeting:** The Budget Agent uses pure Python math (never an LLM) to enforce budget constraints.
- **Live APIs:** Integrates SerpApi (Google Flights/Hotels), Geoapify (Places), OpenWeatherMap, and Open-ER-API (Currency).
- **Resilient Fallbacks:** If an API key is missing or quota is exceeded, the system seamlessly falls back to documented Mock Data.
- **Premium UI:** A custom Streamlit frontend with a responsive dashboard, interactive cards, and PDF itinerary export.

## 🛠️ Tech Stack
- **Backend:** Python 3.12, FastAPI, LangGraph, Pydantic, SQLite.
- **Frontend:** Streamlit, Custom HTML/CSS, fpdf2 (PDF generation).

## ⚙️ How to Run Locally

### 1. Setup Environment
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
uv pip install -r requirements.txt