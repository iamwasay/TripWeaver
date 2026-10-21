import pytest
from app.models.schemas import TripRequest, AgentResult
from app.agents.budget_agent import run_budget_agent
from app.agents.verification_agent import run_verification_agent


# 1. Test Date Validation (Should FAIL)
def test_invalid_dates():
    with pytest.raises(ValueError):
        TripRequest(
            origin="ISB",
            destination="DXB",
            start_date="2025-12-15",
            end_date="2025-12-10",  # Return before departure!
            travelers=1,
            budget_amount=100000,
            budget_currency="PKR",
        )


# 2. Test Budget Math (Deterministic Calculation)
@pytest.mark.asyncio
async def test_budget_calculation():
    req = TripRequest(
        origin="ISB",
        destination="DXB",
        start_date="2025-12-10",
        end_date="2025-12-15",
        travelers=2,
        budget_amount=500000,
        budget_currency="PKR",
    )

    # Fake agent results (1 flight = $100, 1 stay = $100)
    fake_flights = AgentResult(
        agent_name="Flight", data=[{"price": 100.0, "currency": "USD"}]
    )
    fake_stays = AgentResult(
        agent_name="Stay", data=[{"total_stay_cost": 100.0, "currency": "USD"}]
    )
    fake_acts = AgentResult(agent_name="Activities", data=[{"cost": 50.0}])

    result = await run_budget_agent(req, fake_flights, fake_stays, fake_acts)

    assert result.status == "success"
    assert result.data["flights_total"] > 0
    assert result.data["grand_total"] > 0
    # 500k PKR is ~$1800. Fake costs are $250 total. Should be under budget.
    assert result.data["remaining_budget"] > 0


# 3. Test Verification Agent (Over Budget Detection)
@pytest.mark.asyncio
async def test_verification_fails_on_overbudget():
    req = TripRequest(
        origin="ISB",
        destination="DXB",
        start_date="2025-12-10",
        end_date="2025-12-15",
        travelers=2,
        budget_amount=10000,
        budget_currency="PKR",
    )

    # Fake budget result that is massively over budget
    fake_budget = AgentResult(
        agent_name="Budget",
        data={"over_budget_amount": 50000.0, "grand_total": 60000.0},
    )

    result = await run_verification_agent(req, fake_budget)

    assert result.status == "warning"
    assert result.data["status"] == "FAIL"
    assert "Over budget" in result.data["issues"][0]
