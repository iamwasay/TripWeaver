import pytest
from unittest.mock import patch
from datetime import datetime
from app.models.schemas import TripRequest, AgentResult
from app.agents.budget_agent import run_budget_agent
from app.agents.verification_agent import run_verification_agent
from app.agents.orchestrator import orchestrate_trip


# 1. Test Date Validation (Should FAIL)
def test_invalid_dates():
    with pytest.raises(ValueError):
        TripRequest(
            origin="ISB",
            destination="DXB",
            start_date="2025-12-15",
            end_date="2025-12-10",
            travelers=1,
            budget_amount=100000,
            budget_currency="PKR",
        )


# 2. Test Currency Conversion & Budget Math (Mocked API)
@pytest.mark.asyncio
async def test_budget_calculation_mocked():
    req = TripRequest(
        origin="ISB",
        destination="DXB",
        start_date="2025-12-10",
        end_date="2025-12-15",
        travelers=2,
        budget_amount=500000,
        budget_currency="PKR",
    )

    fake_flights = AgentResult(
        agent_name="Flight", data=[{"price": 100.0, "currency": "USD"}]
    )
    fake_stays = AgentResult(
        agent_name="Stay", data=[{"total_stay_cost": 100.0, "currency": "EUR"}]
    )
    fake_acts = AgentResult(
        agent_name="Activities",
        data=[{"cost": 50.0, "currency": "PKR", "is_estimated": True}],
    )

    # Mock the currency exchange rate function
    async def mock_rate(from_curr, to_curr):
        rates = {("USD", "PKR"): 280.0, ("EUR", "PKR"): 300.0, ("PKR", "PKR"): 1.0}
        return {"rate": rates.get((from_curr, to_curr), 1.0)}

    with patch("app.agents.budget_agent.get_exchange_rate", side_effect=mock_rate):
        result = await run_budget_agent(req, fake_flights, fake_stays, fake_acts)

        assert result.status == "success"
        assert result.data["flights_total"] == 28000.0
        assert result.data["stay_total"] == 30000.0
        assert result.data["activities_total"] == 50.0
        assert result.data["grand_total"] > 58050.0


# 3. Test Verification Agent (Missing Flights = FAIL)
@pytest.mark.asyncio
async def test_verification_missing_flights():
    req = TripRequest(
        origin="ISB",
        destination="DXB",
        start_date="2025-12-10",
        end_date="2025-12-15",
        travelers=2,
        budget_amount=500000,
        budget_currency="PKR",
    )
    fake_budget = AgentResult(
        agent_name="Budget", data={"over_budget_amount": 0, "grand_total": 50000}
    )
    fake_empty_flights = AgentResult(agent_name="Flight", data=[])
    fake_stays = AgentResult(agent_name="Stay", data=[{"property_name": "Hotel"}])

    result = await run_verification_agent(
        req, fake_budget, fake_empty_flights, fake_stays
    )

    assert result.status == "warning"
    assert result.data["status"] == "FAIL"
    assert any("No valid flights" in issue for issue in result.data["issues"])


# 4. Test Revision Loop (Overbudget -> Retry -> Pass)
@pytest.mark.asyncio
@patch("app.agents.orchestrator.run_input_agent", side_effect=lambda r: r)
@patch("app.agents.orchestrator.run_flight_agent")
@patch("app.agents.orchestrator.run_stay_agent")
@patch("app.agents.orchestrator.run_activities_agent")
@patch("app.agents.orchestrator.run_weather_agent")
@patch("app.agents.orchestrator.run_budget_agent")
@patch("app.agents.orchestrator.run_verification_agent")
@patch("app.agents.orchestrator.run_itinerary_agent")
@patch("app.agents.orchestrator.run_final_agent")
async def test_revision_loop(
    mock_final,
    mock_itinerary,
    mock_verify,
    mock_budget,
    mock_weather,
    mock_acts,
    mock_stay,
    mock_flight,
    mock_input,
):
    # FIX: Provide TWO flights and TWO stays so the loop has an alternative!
    mock_flight.return_value = AgentResult(
        agent_name="FlightAgent",
        data=[
            {
                "airline": "Emirates (Expensive)",
                "departure_time": datetime.utcnow().isoformat(),
                "arrival_time": datetime.utcnow().isoformat(),
                "price": 500,
                "currency": "USD",
                "source": "Mock",
                "retrieved_at": datetime.utcnow().isoformat(),
            },
            {
                "airline": "Qatar (Cheaper)",
                "departure_time": datetime.utcnow().isoformat(),
                "arrival_time": datetime.utcnow().isoformat(),
                "price": 100,
                "currency": "USD",
                "source": "Mock",
                "retrieved_at": datetime.utcnow().isoformat(),
            },
        ],
    )
    mock_stay.return_value = AgentResult(
        agent_name="StayAgent",
        data=[
            {
                "property_name": "Ritz (Expensive)",
                "room_type": "Deluxe",
                "nightly_rate": 500,
                "total_stay_cost": 2500,
                "currency": "USD",
                "source": "Mock",
                "retrieved_at": datetime.utcnow().isoformat(),
            },
            {
                "property_name": "Holiday Inn (Cheaper)",
                "room_type": "Standard",
                "nightly_rate": 100,
                "total_stay_cost": 500,
                "currency": "USD",
                "source": "Mock",
                "retrieved_at": datetime.utcnow().isoformat(),
            },
        ],
    )
    mock_acts.return_value = AgentResult(agent_name="ActivitiesAgent", data=[])
    mock_weather.return_value = AgentResult(agent_name="WeatherAgent", data={})

    # Mock Budget: First call fails, second call passes
    mock_budget.side_effect = [
        AgentResult(
            agent_name="BudgetAgent",
            status="warning",
            data={"over_budget_amount": 1000, "grand_total": 501000},
        ),
        AgentResult(
            agent_name="BudgetAgent",
            status="success",
            data={"over_budget_amount": 0, "grand_total": 400000},
        ),
    ]

    # Mock Verification: First call fails, second call passes
    mock_verify.side_effect = [
        AgentResult(
            agent_name="VerificationAgent",
            status="warning",
            data={"status": "FAIL", "issues": ["Over budget"]},
        ),
        AgentResult(
            agent_name="VerificationAgent",
            status="success",
            data={"status": "PASS", "issues": []},
        ),
    ]

    mock_itinerary.return_value = AgentResult(
        agent_name="ItineraryAgent", data={"days": []}
    )
    mock_final.return_value = AgentResult(agent_name="FinalAgent", data={})

    req = TripRequest(
        origin="ISB",
        destination="DXB",
        start_date="2025-12-10",
        end_date="2025-12-15",
        travelers=2,
        budget_amount=500000,
        budget_currency="PKR",
    )

    state = await orchestrate_trip(req)

    # Verify the loop actually ran twice
    assert mock_budget.call_count == 2
    assert mock_verify.call_count == 2
    # FIX: state.validation is a dict, so use bracket notation
    assert state.validation["status"] == "PASS"


# 5. End-to-End Test (Fully Mocked)
@pytest.mark.asyncio
async def test_end_to_end_mocked():
    req = TripRequest(
        origin="ISB",
        destination="DXB",
        start_date="2025-12-10",
        end_date="2025-12-15",
        travelers=2,
        budget_amount=1000000,
        budget_currency="PKR",
    )

    with (
        patch("app.agents.orchestrator.run_flight_agent") as mf,
        patch("app.agents.orchestrator.run_stay_agent") as ms,
        patch("app.agents.orchestrator.run_activities_agent") as ma,
        patch("app.agents.orchestrator.run_weather_agent") as mw,
        patch("app.agents.budget_agent.get_exchange_rate") as mrate,
    ):
        mf.return_value = AgentResult(
            agent_name="Flight",
            data=[
                {
                    "airline": "Emirates",
                    "departure_time": datetime.utcnow().isoformat(),
                    "arrival_time": datetime.utcnow().isoformat(),
                    "price": 100,
                    "currency": "USD",
                    "source": "Mock",
                    "retrieved_at": datetime.utcnow().isoformat(),
                }
            ],
        )
        ms.return_value = AgentResult(
            agent_name="Stay",
            data=[
                {
                    "property_name": "Ritz",
                    "room_type": "Deluxe",
                    "nightly_rate": 100,
                    "total_stay_cost": 200,
                    "currency": "USD",
                    "source": "Mock",
                    "retrieved_at": datetime.utcnow().isoformat(),
                }
            ],
        )
        ma.return_value = AgentResult(
            agent_name="Act",
            data=[
                {
                    "name": "Museum",
                    "category": "Cultural",
                    "estimated_duration_hours": 2.0,
                    "cost": 10,
                    "currency": "USD",
                    "is_estimated": True,
                    "source": "Mock",
                    "retrieved_at": datetime.utcnow().isoformat(),
                }
            ],
        )
        mw.return_value = AgentResult(agent_name="Wea", data={})

        async def mock_rate(f, t):
            return {"rate": 280.0}

        mrate.side_effect = mock_rate

        state = await orchestrate_trip(req)

        # FIX: state.validation is a dict, so use bracket notation
        assert state.validation["status"] == "PASS"
        assert state.selected_flight is not None
        assert state.selected_stay is not None
        assert state.budget["grand_total"] > 0
        assert len(state.agent_messages) > 0
