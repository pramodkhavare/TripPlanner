"""
Flight tool: takes a plain-English query and returns live flight info
from Aviationstack.

Examples of queries it understands:
    "flights from Pune to Delhi"
    "Plan a 7 days Japan trip from India"
    "PNQ to DEL"
    "flights to Goa"            (origin defaults to DEFAULT_ORIGIN_IATA)
    "all country flight info"   (global live flights)

.env needed:
    AVIATION_API_KEY=your_key_here
Optional:
    DEFAULT_ORIGIN_IATA=PNQ
    AVIATION_BASE_URL=https://api.aviationstack.com/v1/flights   (paid plans)
"""

import os
import re

import airportsdata
import certifi
import pycountry
import requests
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

API_KEY = os.getenv("AVIATION_API_KEY") or os.getenv("AVIATIONSTACK_API_KEY")

# Used when the user gives only a destination, e.g. "Japan trip"
DEFAULT_ORIGIN_IATA = os.getenv("DEFAULT_ORIGIN_IATA", "PNQ")

# The free plan supports HTTP only. Paid plans can set AVIATION_BASE_URL to https.
BASE_URL = os.getenv("AVIATION_BASE_URL", "http://api.aviationstack.com/v1/flights")

AIRPORTS = airportsdata.load("IATA")

COUNTRY_ALIASES = {
    "usa": "US",
    "u.s.a": "US",
    "america": "US",
    "united states": "US",
    "uk": "GB",
    "britain": "GB",
    "england": "GB",
    "uae": "AE",
    "dubai": "AE",
    "south korea": "KR",
    "korea": "KR",
    "russia": "RU",
    "vietnam": "VN",
    "bangladesh": "BD",
    "india": "IN",
    "japan": "JP",
    "china": "CN",
    "singapore": "SG",
    "malaysia": "MY",
    "thailand": "TH",
    "indonesia": "ID",
    "nepal": "NP",
    "qatar": "QA",
    "saudi arabia": "SA",
    "turkey": "TR",
    "canada": "CA",
    "australia": "AU",
    "germany": "DE",
    "france": "FR",
    "italy": "IT",
    "spain": "ES",
}

# Preferred main airport for country-level searches
COUNTRY_MAIN_AIRPORT = {
    "BD": "DAC", "IN": "DEL", "JP": "NRT", "US": "JFK", "GB": "LHR",
    "AE": "DXB", "SG": "SIN", "MY": "KUL", "TH": "BKK", "ID": "CGK",
    "CN": "PEK", "KR": "ICN", "NP": "KTM", "QA": "DOH", "SA": "JED",
    "TR": "IST", "CA": "YYZ", "AU": "SYD", "DE": "FRA", "FR": "CDG",
    "IT": "FCO", "ES": "MAD",
}

CITY_MAIN_AIRPORT = {
    # India
    "pune": "PNQ",
    "mumbai": "BOM",
    "delhi": "DEL",
    "new delhi": "DEL",
    "goa": "GOI",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "hyderabad": "HYD",
    "chennai": "MAA",
    "kolkata": "CCU",
    "ahmedabad": "AMD",
    "jaipur": "JAI",
    "kochi": "COK",
    # International
    "dhaka": "DAC",
    "tokyo": "NRT",
    "osaka": "KIX",
    "kyoto": "KIX",
    "new york": "JFK",
    "london": "LHR",
    "dubai": "DXB",
    "singapore": "SIN",
    "kuala lumpur": "KUL",
    "bangkok": "BKK",
    "doha": "DOH",
    "istanbul": "IST",
    "toronto": "YYZ",
    "sydney": "SYD",
    "paris": "CDG",
    "rome": "FCO",
    "madrid": "MAD",
    "frankfurt": "FRA",
}

STOP_WORDS = {
    "flight", "flights", "ticket", "tickets", "trip", "travel", "plan",
    "complete", "days", "day", "including", "hotel", "hotels", "sightseeing",
    "under", "budget", "info", "information", "a", "the",
}

# Words that end a place name inside a sentence
_END = r"(?:\s+(?:on|for|under|including|with|in|at|tomorrow|today|next|this|and|budget)\b|[.,!?]|$)"


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------
def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [w for w in text.split() if w not in STOP_WORDS]
    return " ".join(words).strip()


def country_name_to_code(text: str):
    text = clean_text(text)
    if not text:
        return None

    if text in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[text]

    try:
        return pycountry.countries.lookup(text).alpha_2
    except LookupError:
        pass

    for country in pycountry.countries:
        if re.search(rf"\b{re.escape(country.name.lower())}\b", text):
            return country.alpha_2

    for alias, code in COUNTRY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return code

    return None


def get_best_airport_for_country(country_code: str):
    preferred = COUNTRY_MAIN_AIRPORT.get(country_code)
    if preferred and preferred in AIRPORTS:
        return preferred

    candidates = []
    for iata, airport in AIRPORTS.items():
        if not iata or str(airport.get("country", "")).upper() != country_code:
            continue
        name = str(airport.get("name", "")).lower()
        score = 0
        if "international" in name:
            score += 50
        if "intl" in name:
            score += 40
        if "capital" in name:
            score += 20
        candidates.append((score, iata))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def resolve_location_to_iata(location: str):
    """Convert a city / country / airport / IATA code into an IATA code."""
    if not location:
        return None

    raw = location.strip()

    loc = clean_text(raw)
    if not loc:
        return None

    # Known city names win over IATA codes ("goa" is Goa, not Genoa's GOA)
    if loc in CITY_MAIN_AIRPORT:
        return CITY_MAIN_AIRPORT[loc]

    # Known country aliases win too ("usa" is the USA, not Concord's USA airport)
    if loc in COUNTRY_ALIASES:
        airport = get_best_airport_for_country(COUNTRY_ALIASES[loc])
        if airport:
            return airport

    # Direct IATA code (e.g. "pnq", "DEL")
    if re.fullmatch(r"[A-Za-z]{3}", raw) and raw.upper() in AIRPORTS:
        return raw.upper()

    country_code = country_name_to_code(loc)
    if country_code:
        airport = get_best_airport_for_country(country_code)
        if airport:
            return airport

    # Fallback: search the airport database by city name
    matches = []
    for iata, airport in AIRPORTS.items():
        city = str(airport.get("city", "")).lower().strip()
        name = str(airport.get("name", "")).lower().strip()
        score = 0
        if city == loc:
            score += 100
        elif loc in city:
            score += 70
        if loc in name:
            score += 50
        if score and "international" in name:
            score += 10
        if score:
            matches.append((score, iata))

    if matches:
        matches.sort(reverse=True)
        return matches[0][1]

    return None


def find_location_mentions(query: str):
    """Find country/city names in free text, ordered by position in the text."""
    q = query.lower()
    found = {}  # name -> position

    names = (
        list(COUNTRY_ALIASES)
        + list(CITY_MAIN_AIRPORT)
        + [c.name.lower() for c in pycountry.countries if len(c.name) >= 4]
    )
    for name in names:
        m = re.search(rf"\b{re.escape(name)}\b", q)
        if m and name not in found:
            found[name] = m.start()

    return [n for n, _ in sorted(found.items(), key=lambda kv: kv[1])]


# --------------------------------------------------------------------------
# Query parsing
# --------------------------------------------------------------------------
def parse_route(query: str):
    """
    Returns (dep_iata, arr_iata). Either can be None.
    (None, None) means global live flights.
    """
    q = query.strip()
    q_lower = q.lower()

    global_keywords = [
        "all country", "all countries", "global flight", "global flights",
        "all flight", "all flights", "worldwide flight", "worldwide flights",
    ]
    if any(k in q_lower for k in global_keywords):
        return None, None

    # Explicit IATA codes (must be real airport codes, so "USA" / "UAE" are ignored)
    codes = [c for c in re.findall(r"\b[A-Z]{3}\b", q) if c in AIRPORTS]
    if len(codes) >= 2:
        return codes[0], codes[1]

    # "from X to Y"
    m = re.search(rf"\bfrom\s+(.+?)\s+to\s+(.+?){_END}", q_lower)
    if m:
        dep = resolve_location_to_iata(m.group(1))
        arr = resolve_location_to_iata(m.group(2))
        if dep or arr:
            return dep, arr

    # "to Y from X"
    m = re.search(rf"\bto\s+(.+?)\s+from\s+(.+?){_END}", q_lower)
    if m:
        arr = resolve_location_to_iata(m.group(1))
        dep = resolve_location_to_iata(m.group(2))
        if dep or arr:
            return dep, arr

    # "... Japan trip from Bangladesh": origin after "from", destination before it
    m = re.search(rf"\bfrom\s+(.+?){_END}", q_lower)
    if m:
        dep = resolve_location_to_iata(m.group(1))
        before = q_lower[: m.start()]
        mentions = find_location_mentions(before)
        arr = resolve_location_to_iata(mentions[0]) if mentions else None
        if dep or arr:
            return dep, arr

    # "flights to Y"
    m = re.search(rf"\bto\s+(.+?){_END}", q_lower)
    if m:
        arr = resolve_location_to_iata(m.group(1))
        if arr:
            return DEFAULT_ORIGIN_IATA, arr

    # "pune delhi" / "Japan trip" fallback
    mentions = find_location_mentions(q)
    if len(mentions) >= 2:
        return (
            resolve_location_to_iata(mentions[0]),
            resolve_location_to_iata(mentions[1]),
        )
    if len(mentions) == 1:
        return DEFAULT_ORIGIN_IATA, resolve_location_to_iata(mentions[0])

    return None, None


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------
def format_flight(flight: dict) -> str:
    airline = (flight.get("airline") or {}).get("name") or "Unknown airline"
    flight_number = (flight.get("flight") or {}).get("iata") or "Unknown flight number"
    status = flight.get("flight_status") or "Unknown"

    dep = flight.get("departure") or {}
    arr = flight.get("arrival") or {}

    dep_airport = dep.get("airport") or "Unknown departure airport"
    dep_iata = dep.get("iata") or "Unknown"
    dep_terminal = dep.get("terminal") or "N/A"
    dep_gate = dep.get("gate") or "N/A"
    dep_scheduled = dep.get("scheduled") or "Unknown"
    dep_delay = dep.get("delay")
    dep_delay_text = f"{dep_delay} minutes" if dep_delay is not None else "N/A"

    arr_airport = arr.get("airport") or "Unknown arrival airport"
    arr_iata = arr.get("iata") or "Unknown"
    arr_terminal = arr.get("terminal") or "N/A"
    arr_gate = arr.get("gate") or "N/A"
    arr_scheduled = arr.get("scheduled") or "Unknown"
    arr_delay = arr.get("delay")
    arr_delay_text = f"{arr_delay} minutes" if arr_delay is not None else "N/A"

    return f"""
Airline: {airline}
Flight: {flight_number}
Status: {status}

Departure:
- Airport: {dep_airport}
- IATA: {dep_iata}
- Terminal: {dep_terminal}
- Gate: {dep_gate}
- Scheduled: {dep_scheduled}
- Delay: {dep_delay_text}

Arrival:
- Airport: {arr_airport}
- IATA: {arr_iata}
- Terminal: {arr_terminal}
- Gate: {arr_gate}
- Scheduled: {arr_scheduled}
- Delay: {arr_delay_text}
""".strip()


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def search_flights(query: str, limit: int = 10) -> str:
    """Take a plain-English query and return flight info as text."""
    if not API_KEY:
        return (
            "Flight API error: AVIATION_API_KEY is missing.\n"
            "Add this to your .env file:\n"
            "AVIATION_API_KEY=your_api_key_here"
        )

    dep_iata, arr_iata = parse_route(query)

    params = {"access_key": API_KEY, "limit": min(limit, 100)}
    if dep_iata:
        params["dep_iata"] = dep_iata
    if arr_iata:
        params["arr_iata"] = arr_iata

    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        data = response.json()
    except requests.exceptions.RequestException as e:
        return f"Flight API request failed: {e}"
    except ValueError:
        return "Flight API returned invalid JSON."

    if "error" in data:
        err = data["error"]
        return (
            "Flight API error:\n"
            f"Code: {err.get('code', 'Unknown')}\n"
            f"Message: {err.get('message', 'Unknown error')}"
        )

    flights = data.get("data") or []

    if dep_iata and arr_iata:
        route_info = f"Live flights from {dep_iata} to {arr_iata}"
    elif dep_iata:
        route_info = f"Live flights from {dep_iata}"
    elif arr_iata:
        route_info = f"Live flights to {arr_iata}"
    else:
        route_info = "Global live flights"

    if not flights:
        return (
            f"No live flight data found. ({route_info})\n\n"
            "Note: Aviationstack provides live/scheduled flight status, not ticket prices. "
            "For fares, use a pricing API such as Amadeus."
        )

    formatted = [format_flight(f) for f in flights[:limit]]
    return f"{route_info}\n\n" + "\n\n---\n\n".join(formatted)


# Optional LangChain tool wrapper (uncomment if you use LangChain/LangGraph)
# from langchain_core.tools import tool
#
# @tool
# def flight_search(query: str) -> str:
#     """Find live flight info from a plain-English request,
#     e.g. 'flights from Pune to Delhi' or 'Japan trip from India'."""
#     return search_flights(query)


if __name__ == "__main__":
    # for q in [
    #     "flights from Pune to Delhi",
    #     "Plan a 7 days Japan trip from Bangladesh",
    #     "PNQ to DEL",
    #     "flights to Goa",
    # ]:
    #     print(q, "->", parse_route(q))

    if __name__ == "__main__":
        print(search_flights("flights from Pune to Delhi", limit=3))