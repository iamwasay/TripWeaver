import csv
from pathlib import Path
from functools import lru_cache

DATA_FILE = Path(__file__).with_name("airports.csv")

# The hardcoded list acts as our "Guaranteed" fallback and ensures our most
# important cities are always perfectly named.
MANUAL_AIRPORTS = {
    # --- Pakistan ---
    "ISB": "Islamabad",
    "LHE": "Lahore",
    "KHI": "Karachi",
    "PEW": "Peshawar",
    "MUX": "Multan",
    "SKT": "Sialkot",
    "UET": "Quetta",
    # --- Middle East ---
    "DXB": "Dubai",
    "AUH": "Abu Dhabi",
    "SHJ": "Sharjah",
    "DOH": "Doha",
    "JED": "Jeddah",
    "RUH": "Riyadh",
    "MCT": "Muscat",
    "KWI": "Kuwait",
    "BAH": "Bahrain",
    "AMM": "Amman",
    "BEY": "Beirut",
    "TLV": "Tel Aviv",
    # --- Europe ---
    "LHR": "London",
    "LGW": "London Gatwick",
    "CDG": "Paris",
    "FRA": "Frankfurt",
    "AMS": "Amsterdam",
    "MAD": "Madrid",
    "BCN": "Barcelona",
    "FCO": "Rome",
    "MXP": "Milan",
    "IST": "Istanbul",
    "ATH": "Athens",
    "ZRH": "Zurich",
    "VIE": "Vienna",
    "BRU": "Brussels",
    "CPH": "Copenhagen",
    "ARN": "Stockholm",
    "OSL": "Oslo",
    "HEL": "Helsinki",
    "DUB": "Dublin",
    "LIS": "Lisbon",
    "WAW": "Warsaw",
    "PRG": "Prague",
    "BUD": "Budapest",
    "SVO": "Moscow",
    # --- Asia ---
    "HND": "Tokyo",
    "NRT": "Tokyo Narita",
    "KIX": "Osaka",
    "BKK": "Bangkok",
    "SIN": "Singapore",
    "KUL": "Kuala Lumpur",
    "CGK": "Jakarta",
    "MNL": "Manila",
    "HKG": "Hong Kong",
    "PEK": "Beijing",
    "PVG": "Shanghai",
    "CAN": "Guangzhou",
    "SZX": "Shenzhen",
    "ICN": "Seoul",
    "TPE": "Taipei",
    "HAN": "Hanoi",
    "SGN": "Ho Chi Minh City",
    "DPS": "Bali",
    "DEL": "Delhi",
    "BOM": "Mumbai",
    "BLR": "Bangalore",
    "MAA": "Chennai",
    "CCU": "Kolkata",
    "KTM": "Kathmandu",
    "CMB": "Colombo",
    "DAC": "Dhaka",
    # --- North America ---
    "JFK": "New York",
    "LAX": "Los Angeles",
    "ORD": "Chicago",
    "MIA": "Miami",
    "SFO": "San Francisco",
    "SEA": "Seattle",
    "DFW": "Dallas",
    "ATL": "Atlanta",
    "DEN": "Denver",
    "LAS": "Las Vegas",
    "PHX": "Phoenix",
    "IAH": "Houston",
    "EWR": "Newark",
    "MCO": "Orlando",
    "CLT": "Charlotte",
    "MSP": "Minneapolis",
    "DTW": "Detroit",
    "PHL": "Philadelphia",
    "LGA": "New York LaGuardia",
    "YYZ": "Toronto",
    "YVR": "Vancouver",
    "YUL": "Montreal",
    "YYC": "Calgary",
    "MEX": "Mexico City",
    "CUN": "Cancun",
    # --- South America ---
    "GRU": "Sao Paulo",
    "EZE": "Buenos Aires",
    "BOG": "Bogota",
    "SCL": "Santiago",
    "LIM": "Lima",
    # --- Oceania ---
    "SYD": "Sydney",
    "MEL": "Melbourne",
    "BNE": "Brisbane",
    "PER": "Perth",
    "AKL": "Auckland",
    # --- Africa ---
    "JNB": "Johannesburg",
    "CPT": "Cape Town",
    "CAI": "Cairo",
    "NBO": "Nairobi",
    "LOS": "Lagos",
    "ADD": "Addis Ababa",
    "CMN": "Casablanca",
}


@lru_cache(maxsize=1)
def load_airports():
    """
    Load the CSV if it exists, and merge it with our guaranteed manual list.
    The manual list acts as the base, and the CSV fills in the rest of the world.
    """
    # 1. Start with the manual dictionary as the base
    merged_airports = {}
    for code, city in MANUAL_AIRPORTS.items():
        merged_airports[code] = {"city": city, "name": city}

    # 2. If the CSV exists, read it and add missing airports
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    iata = (row.get("iata_code") or "").strip().upper()
                    atype = (row.get("type") or "").strip()
                    scheduled = (
                        row.get("scheduled_service") or ""
                    ).strip().lower() == "yes"

                    # Filter out small/closed airports and keep only commercial ones
                    if (
                        iata
                        and scheduled
                        and atype in ("large_airport", "medium_airport")
                    ):
                        if iata not in merged_airports:
                            city = (row.get("municipality") or "").strip()
                            name = (row.get("name") or "").strip()
                            merged_airports[iata] = {
                                "city": city if city else name,
                                "name": name,
                            }
        except Exception:
            # Silently fall back to just the manual list if CSV fails to parse
            pass

    return merged_airports


def get_city_name(location: str) -> str:
    """Convert an airport code into its city name (e.g., DXB -> Dubai)."""
    loc = location.strip().upper()
    airports = load_airports()
    if loc in airports:
        return airports[loc]["city"]
    return location.strip()


def get_iata_code(location: str) -> str:
    """Converts a city name to an IATA code (e.g., Dubai -> DXB)."""
    loc = location.strip().upper()
    airports = load_airports()

    # Check if it's already a code
    if loc in airports:
        return loc

    # Search by city name
    for code, data in airports.items():
        if data["city"].upper() == loc:
            return code

    return loc


@lru_cache(maxsize=1)
def get_popular_airports() -> list[str]:
    """
    Returns a formatted list of all available airports for the UI dropdown.
    Format: "City (CODE)"
    """
    airports = load_airports()
    formatted = set()

    for code, data in airports.items():
        formatted.add(f"{data['city']} ({code})")

    result = list(formatted)
    result.sort()
    return result
