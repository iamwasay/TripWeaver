# TripWeaver ✈️
### Multi-Agent Budget Travel Planner

TripWeaver is a collaborative AI system that turns user travel preferences, dates, and budgets into a complete, practical trip plan. Instead of relying on a single monolithic prompt, it uses a central **Orchestrator (built with LangGraph)** to coordinate 8 specialized AI agents. 

## 🌐 Live Deployment
- **Frontend (Streamlit):** [https://tripweaver.streamlit.app/](https://tripweaver.streamlit.app/)
- **Backend API (Render):** [https://tripweaver-backend-vain.onrender.com/docs](https://tripweaver-backend-vain.onrender.com/docs)

---

## 🏗️ Architecture & Multi-Agent Workflow
The system is built around a shared `TripState` object passed through a LangGraph workflow. 

1. **Input/Constraint Agent:** Validates user requests, dates, and budgets.
2. **Orchestrator Agent:** Manages the workflow, enforces constraints, and handles the revision loop.
3. **Flight Agent:** Searches for real-time round-trip flights via SerpApi.
4. **Stay Agent:** Finds hotels via Google Hotels (SerpApi).
5. **Activities Agent:** Discovers attractions via Geoapify (with dynamic cost estimation and duplicate removal).
6. **Weather Agent:** Fetches real-time weather context via OpenWeatherMap.
7. **Budget Agent:** Deterministically calculates totals and converts currencies. *Never uses an LLM for math.*
8. **Verification/Constraint Agent:** Validates that the plan fits the budget and constraints. If it fails, it routes back to the Orchestrator for a revision loop (tries cheaper options).
9. **Itinerary & Final Response Agents:** Generates the day-by-day plan and final user-facing summary.

---

## 🚀 Key Features & P0 Fixes
- **LangGraph Revision Loop:** If a plan exceeds the budget, the graph automatically loops back and attempts to swap to cheaper flights/hotels before failing.
- **Round-Trip Flight Pricing:** The Flight Agent passes both `depart_date` and `return_date` to accurately price the entire trip, not just a one-way leg.
- **Safe Currency Conversion:** Uses `open.er-api.com`. If the API fails, it raises an error rather than silently returning a 1.0 rate (which would fake the budget).
- **Dynamic Activity Costs:** Instead of a flat $10 fee for all attractions, the system estimates $0 for free locations (beaches/walks) and $25 for premium sites (museums/palaces).
- **Professional PDF Export:** Generates a multi-page, branded PDF itinerary using `fpdf2`.

---

## 🛠️ Tech Stack
- **Backend:** Python 3.12, FastAPI, LangGraph, Pydantic, SQLAlchemy (SQLite audit logs).
- **Frontend:** Streamlit, Custom HTML/CSS, `fpdf2` for PDF generation.
- **APIs:** SerpApi (Flights/Hotels), Geoapify (Places), OpenWeatherMap, Open-ER-API (Currency).

---

## ⚙️ Local Setup Instructions

### 1. Clone & Setup Environment
```bash
git clone https://github.com/iamwasay/TripWeaver.git
cd TripWeaver
python -m venv .venv