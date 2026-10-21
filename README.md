---
title: TripWeaver Backend
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# TripWeaver: Multi-Agent Budget Travel Planner

TripWeaver is a collaborative AI system that transforms user travel preferences, dates, and budgets into a complete, practical trip plan. Instead of relying on a single monolithic prompt, it uses a central Orchestrator (built with LangGraph) to coordinate 8 specialized AI agents.

## 🚀 Features
- **Multi-Agent Architecture:** 8 distinct agents handle specialized tasks: Input/Constraint, Flight, Stay, Activities, Weather, Budget, Verification, and Itinerary.
- **Deterministic Budgeting:** The Budget Agent uses pure Python math (never an LLM) to enforce budget constraints, calculate remaining funds, and flag overages.
- **Live APIs:** Integrates SerpApi (Google Flights/Hotels), Geoapify (Places), OpenWeatherMap, and Open-ER-API (Currency).
- **Graceful Fallbacks:** If an API key is missing or a quota is exceeded, the system seamlessly falls back to documented Mock Data (as permitted by the MVP guidelines).
- **Premium Frontend:** A custom Streamlit UI with a responsive dashboard, interactive flight/hotel cards, a budget tracker, and PDF itinerary export.

## 🛠️ Tech Stack
- **Backend:** Python 3.12, FastAPI, LangGraph, Pydantic, SQLite (SQLAlchemy).
- **Frontend:** Streamlit, Custom HTML/CSS, fpdf2 (PDF generation).
- **Deployment:** Backend hosted on Hugging Face Spaces (Docker); Frontend hosted on Streamlit Community Cloud.

## ⚙️ How to Run Locally

### 1. Setup Environment
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
uv pip install -r requirements.txt