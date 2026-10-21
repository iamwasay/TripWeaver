from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
import uuid


# ==========================================
# 1. Trip Request (Normalized & Validated)
# ==========================================
class TripRequest(BaseModel):
    origin: str = Field(..., description="City or airport code")
    destination: str = Field(..., description="City or destination")
    start_date: date
    end_date: date
    travelers: int = Field(..., ge=1, description="Must be at least 1")
    budget_amount: float = Field(..., gt=0, description="Must be greater than 0")
    budget_currency: str = Field(..., min_length=3, max_length=3)

    accommodation_level: Optional[str] = "mid-range"
    interests: List[str] = Field(default_factory=list)
    dietary_preferences: List[str] = Field(default_factory=list)
    mobility_constraints: List[str] = Field(default_factory=list)
    pace: Optional[str] = "moderate"
    constraints: List[str] = Field(default_factory=list)

    # Requirement: Add validation for dates
    @model_validator(mode="after")
    def check_dates(self) -> "TripRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be strictly after start_date")
        return self


# ==========================================
# 2. Agent Result (Standardized Reporting)
# ==========================================
class AgentResult(BaseModel):
    agent_name: str
    status: Literal["success", "warning", "error", "pending"] = "success"
    data: Any = Field(default=None)
    source: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    assumptions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# ==========================================
# 3. Specific Option Models (Flights, Stays, Activities)
# ==========================================
class FlightOption(BaseModel):
    airline: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int
    price: float
    currency: str
    source: str
    retrieved_at: datetime


class StayOption(BaseModel):
    property_name: str
    room_type: str
    nightly_rate: float
    total_stay_cost: float
    currency: str
    rating: Optional[float] = None
    location: Optional[str] = None
    source: str
    retrieved_at: datetime


class ActivityOption(BaseModel):
    name: str
    category: str
    estimated_duration_hours: float
    cost: float
    currency: str
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    source: str
    retrieved_at: datetime


# ==========================================
# 4. Budget & Itinerary Models
# ==========================================
class BudgetBreakdown(BaseModel):
    flights_total: float = 0.0
    stay_total: float = 0.0
    activities_total: float = 0.0
    food_estimate: float = 0.0
    transport_estimate: float = 0.0
    misc_estimate: float = 0.0
    grand_total: float = 0.0
    remaining_budget: float = 0.0
    over_budget_amount: float = 0.0
    currency: str


class DailySchedule(BaseModel):
    day_number: int
    date: date
    activities: List[ActivityOption] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    days: List[DailySchedule] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# 5. Validation / Verification Result
# ==========================================
class ValidationResult(BaseModel):
    status: Literal["PASS", "WARN", "FAIL"]
    issues: List[str] = Field(default_factory=list)


# ==========================================
# 6. Trip State (The Shared Memory)
# ==========================================
class TripState(BaseModel):
    trip_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trip_request: Optional[TripRequest] = None

    search_results: Dict[str, Any] = Field(default_factory=dict)

    selected_flight: Optional[FlightOption] = None
    selected_stay: Optional[StayOption] = None
    activities: List[ActivityOption] = Field(default_factory=list)

    weather: Optional[Dict[str, Any]] = None
    budget: Optional[BudgetBreakdown] = None

    itinerary: Optional[Itinerary] = None
    validation: Optional[ValidationResult] = None

    agent_messages: List[AgentResult] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    timestamps: Dict[str, datetime] = Field(default_factory=dict)
