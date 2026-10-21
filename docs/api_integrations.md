# API Integrations and Limitations

## 1. Currency Exchange
- **Provider:** open.er-api.com
- **Cost:** Free, no API key required.
- **Limitation:** Rates update daily.

## 2. Weather
- **Provider:** OpenWeatherMap
- **Cost:** Free tier (requires API key).
- **Limitation:** Free tier only provides 5-day forecasts (not 10-day). The Weather Agent will present long-range data as "seasonal context" rather than a strict forecast.

## 3. Places / Activities
- **Provider:** OpenTripMap (Free tier)
- **Fallback:** Mock data.
- **Limitation:** OpenTripMap does not provide ticket prices or real-time opening hours. The Activities Agent will estimate durations and flag costs as "Estimated".

## 4. Flights
- **Provider:** Amadeus Self-Service (Test Environment)
- **Fallback:** Mock data (if API keys are absent or rejected).
- **Limitation:** Amadeus test environment only allows a limited number of API calls per month and returns fake/limited flight availability.

## 5. Hotels
- **Provider:** Amadeus Self-Service (Test Environment) / Mock
- **Limitation:** Amadeus hotel search in the test environment is historically unreliable. We default to a documented mock provider to ensure the itinerary workflow can be tested end-to-end.