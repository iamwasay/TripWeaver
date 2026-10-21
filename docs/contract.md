# TripWeaver — Build Contract

> Frozen reference for every model, agent and test in this project.
> If it's not in this file, it doesn't belong in the MVP.

---

## Inputs (what the user provides)

| Field | Required | Notes |
|---|---|---|
| origin | ✅ | city or airport (e.g. Islamabad, ISB) |
| destination | ✅ | city (e.g. Istanbul) |
| start_date | ✅ | ISO format `YYYY-MM-DD` |
| end_date | ✅ | ISO format `YYYY-MM-DD`, must be > start_date |
| travelers | ✅ | integer ≥ 1 |
| budget_amount | ✅ | positive number |
| budget_currency | ✅ | ISO code (e.g. PKR, USD) |
| accommodation_level | ❌ | `budget` / `mid-range` / `luxury` |
| interests | ❌ | list, e.g. `["cultural", "food"]` |
| dietary_preferences | ❌ | list |
| mobility_constraints | ❌ | list |
| pace | ❌ | `relaxed` / `moderate` / `packed` |

Input is accepted both as a **form** and as **natural language** (Input Agent handles the NL case).

---

## Outputs (what the system returns)

**Structured JSON:**
- ranked **flight options** — price, currency, duration, stops, source, retrieved_at
- ranked **stay options** — nightly rate, total, rating, location, source, retrieved_at
- **activities** — name, cost, duration, opening hours, source, retrieved_at
- **budget breakdown** — flights / stay / activities / food / transport / misc / total / remaining
- **day-by-day itinerary** with travel buffers
- **validation result** — PASS / WARN / FAIL + list of issues
- **alternatives** — cheaper flight, cheaper hotel, free/low-cost activities (required when over budget)
- **metadata** — assumptions, warnings, sources, timestamps per data point

**Human-readable:** trip summary, selected options with prices, budget table, daily plan, alternatives, warnings, sources.

---

## Rules I must not break

1. **No booking claims.** MVP = search & recommend only.
2. **Label estimated vs live prices.**
3. **Every external data point keeps** `source` **and** `retrieved_at`.
4. **Budget totals computed by Python, never by the LLM.**
5. **Over budget → alternatives + explanation**, never a fake-valid plan.
6. **Never invent API results.** Provider failure = record the error.
7. **API keys in `.env` only.** Never in code, frontend, or Git.

---

## Agents to build (10)

| # | Agent | Responsibility |
|---|---|---|
| 1 | Input/Constraint | parse user request → `TripRequest` |
| 2 | Orchestrator | coordinate workflow, dispatch, revisions (max 2–3 rounds) |
| 3 | Flight | search + rank flights |
| 4 | Stay | search + rank hotels |
| 5 | Activities | find attractions matching interests |
| 6 | Weather | weather context (optional, build last) |
| 7 | Budget | deterministic totals |
| 8 | Verification | PASS / WARN / FAIL checks |
| 9 | Itinerary | day-by-day plan |
| 10 | Final Response | user-facing summary |

**Each agent returns:** `agent_name, status, data, source, retrieved_at, assumptions[], warnings[], errors[]`

---

## Demo scenario (fixed)

- Origin: **Islamabad**
- Destination: **Istanbul**
- Dates: **10–15 December 2025**
- Travelers: **2**
- Budget: **PKR 350,000**
- Preferences: cultural, mid-range stay, economy flight, moderate pace

---

## Out of scope (do not build until MVP is done)

- Automatic ticket/hotel purchasing
- User accounts, payments
- Multi-destination routing
- Restaurant/Food agent, Visa agent, Price-monitoring agent
- RAG over destination guides, graph database, evaluation dashboard
- Scraping sites that prohibit it

---

## Done when

- A new user can enter destination, dates and budget
- Orchestrator launches specialist agents
- Agents return structured results
- At least one budget-feasible plan **or** a clear explanation why not
- Verification catches major conflicts
- Final itinerary generated
- UI shows sources and timestamps
- Tests pass
- Demo reproducible from README