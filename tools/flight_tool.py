import os
import re
import certifi
import airportsdata
import pycountry
import requests
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

DEFAULT_ORIGIN_DATA = os.getenv("DEFAULT_ORIGIN_DATA", "IND")

API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
BASE_URL = "http://api.aviationstack.com/v1/flights"

AIRPORTS = airportsdata.load('iata')

COUNTRY_ALIASES = {
  "us": "USA",
  "russia": "RUS",
  "usa": "USA",
  "united states": "USA",
  "united states of america": "USA",
  "states": "USA",
  "new york": "USA",
  "california": "USA",
  "los angeles": "USA",
  "chicago": "USA",
  "houston": "USA",
  "phoenix": "USA",
  "philadelphia": "USA",
  "san antonio": "USA",
  "san diego": "USA",
  "dallas": "USA",
  "san jose": "USA",
  "charlotte": "USA",
  "indianapolis": "USA",
  "san francisco": "USA",
  "cairo": "EGY",
  "egypt": "EGY",
  "great britain": "GBR",
  "england": "GBR",
  "scotland": "GBR",
  "wales": "GBR",
  "ireland": "IRL",
  "uk": "GBR",
  "uae": "ARE",
  "dubai": "ARE",
  "abu dhabi": "ARE",
  "oman": "OMN",
  "bahrain": "BHR",
  "saudi": "SAU",
  "saudi arabia": "SAU",
  "ksa": "SAU",
  "qatar": "QAT",
  "germany": "DEU",
  "france": "FRA",
  "spain": "ESP",
  "italy": "ITA",
  "switzerland": "CHE",
  "austria": "AUT",
  "netherlands": "NLD",
  "belgium": "BEL",
  "china": "CHN",
  "japan": "JPN",
  "singapore": "SGP",
  "malaysia": "MYS",
  "taiwan": "TWN",
  "hong kong": "HKG",
  "korea": "KOR",
  "indonesia": "IDN",
  "brazil": "BRA",
  "australia": "AUS",
  "new zealand": "NZL",
  "canada": "CAN",
  "mexico": "MEX",
  "india": "IND",
  "nepal": "NPL"
}

COUNTRY_MAIL_AIRPORT = {
  "IND": "DEL",
  "NPL": "KTM",
  "USA": "JFK",
  "ARE": "DXB",
  "SAU": "RUH",
  "QAT": "DOH",
  "DEU": "FRA",
  "FRA": "CDG",
  "ESP": "MAD",
  "ITA": "FCO",
  "CHE": "ZRH",
  "AUT": "VIE",
  "NLD": "AMS",
  "BEL": "BRU",
  "CHN": "PEK",
  "JPN": "NRT",
  "SGP": "SIN",
  "MYS": "KUL",
  "TWN": "TPE",
  "HKG": "HKG",
  "KOR": "ICN",
  "IDN": "CGK",
  "BRA": "GRU",
  "AUS": "SYD",
  "NZL": "AKL",
  "CAN": "YYZ",
  "MEX": "MEX"
}

COUNTRY_MAIN_AIRPORT = COUNTRY_MAIL_AIRPORT

CITY_MAIN_AIRPORT = {
  "india": ["newdelhi"],
  "nepal": ["kathmandu"],
  "usa": ["newyork", "losangeles", "chicago", "houston", "phoenix", "philadelphia", "sanantonio", "sandiego", "dallas", "sanjose", "charlotte", "indianapolis", "sanfrancisco"],
  "uae": ["dubai", "abudhabi"],
  "saudi": ["riyadh", "jeddah", "mecca", "medina"],
  "qatar": ["doha"],
  "germany": ["berlin", "munich", "frankfurt", "hamburg", "stuttgart", "dusseldorf", "leipzig", "dresden", "hanover", "essen"],
  "france": ["paris", "lyon", "marseille", "toulouse", "nice", "strasbourg", "bordeaux", "lille", "rennes", "reims"],
  "spain": ["madrid", "barcelona", "valencia", "seville", "bilbao", "malaga", "alicante", "palma", "zaragoza", "murcia"],
  "italy": ["rome", "milan", "naples", "turin", "palermo", "genoa", "bologna", "florence", "bari", "catania"],
  "switzerland": ["zurich", "geneva", "basel", "bern", "lucerne", "lausanne", "winterthur", "st gallen", "lugano", "fribourg"],
  "austria": ["vienna", "salzburg", "graz", "linz", "innsbruck", "klagenfurt", "villach", "st.polten", "wels", "bregenz"],
  "netherlands": ["amsterdam", "rotterdam", "the hague", "utrecht", "eindhoven", "haarlem", "leiden", "maastricht", "delft", "nijmegen"],
  "belgium": ["brussels", "antwerp", "ghent", "charleroi", "liege", "bruges", "namur", "leuven", "mons", "aalst"],
  "china": ["beijing", "shanghai", "guangzhou", "shenzhen", "chengdu", "wuhan", "chongqing", "tianjin", "hangzhou", "nanjing"],
  "japan": ["tokyo", "osaka", "kyoto", "nagoya", "sapporo", "yokohama", "kobe", "fukuoka", "hiroshima", "sendai"],
  "singapore": ["singapore"],
  "malaysia": ["kuala lumpur", "penang", "johor bahru", "ipoh", "melaka", "kotakinabalu", "shah alam", "kuching", "alor setar", "kuala terengganu"],
  "taiwan": ["taipei", "kaohsiung", "taichung", "tainan", "hsinchu", "keelung", "taoyuan", "chiayi", "hualien", "yilan"],
  "hong kong": ["hong kong"],
  "korea": ["seoul", "busan", "incheon", "daegu", "daejeon", "ulsan", "gwangju", "suwon", "goyang", "yongin"],
  "indonesia": ["jakarta", "surabaya", "bandung", "medan", "semarang", "makassar", "palembang", "bogor", "depok", "tangerang"],
  "brazil": ["saopaulo", "riodejaneiro", "brasilia", "salvador", "fortaleza", "belohorizonte", "curitiba", "manaus", "recife", "portoalegre"],
  "australia": ["sydney", "melbourne", "brisbane", "perth", "adelaide", "goldcoast", "newcastle", "canberra", "woollongong", "cairns"],
  "new zealand": ["auckland", "wellington", "christchurch", "hamilton", "tauranga", "dunedin", "lowerhutt", "palmerston", "rotorua", "newplymouth"],
  "canada": ["toronto", "vancouver", "montreal", "calgary", "ottawa", "edmonton", "mississauga", "winnipeg", "brampton", "hamilton"],
  "mexico": ["mexicocity", "guadalajara", "monterrey", "puebla", "tijuana", "leon", "juarez", "toluca", "tlanepantladdebaz"]
}

def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    stop_words = [
        "and", "or", "but", "not", "the", "a", "an", "in", "on", "at", "to", "from",
        "by", "for", "with", "about", "as", "of", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "should", "could", "may", "might", "must", "shall", "can", "flights", "flight",
        "trip", "fly", "travel", "ticket", "tickets", "book", "booking", "find",
        "budget", "roundtrip", "oneway"
    ]
    tokens = text.split()
    tokens = [word for word in tokens if word not in stop_words]
    return " ".join(tokens)

def country_name_to_code(text: str) -> str:
    """
    Converts a country name, ISO code, alias, city, or flight search query
    into an ISO 3166-1 alpha-3 country code (e.g., 'IND', 'USA', 'JPN').

    Resolution steps:
    1. Validation & normalization
    2. Direct ISO 3166-1 alpha-3 / alpha-2 lookup via pycountry
    3. Direct lookup in predefined COUNTRY_ALIASES
    4. Exact name / official name lookup via pycountry
    5. Fuzzy matching via pycountry
    6. City mapping lookup via CITY_MAIN_AIRPORT
    7. Natural language query resolution (cleaned query and token matching)

    Args:
        text (str): Input text containing country, code, city, or query.

    Returns:
        str: ISO 3166-1 alpha-3 country code, or empty string if not resolved.
    """
    if not text or not isinstance(text, str):
        return ""

    raw_query = text.strip()
    if not raw_query:
        return ""

    # 1. Direct ISO code check (Alpha-3 or Alpha-2)
    upper_query = raw_query.upper()
    if len(upper_query) == 3:
        country = pycountry.countries.get(alpha_3=upper_query)
        if country:
            return country.alpha_3
    elif len(upper_query) == 2:
        country = pycountry.countries.get(alpha_2=upper_query)
        if country:
            return country.alpha_3

    # 2. Direct lookup in COUNTRY_ALIASES
    lower_query = raw_query.lower()
    if lower_query in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[lower_query]

    # 3. Exact name lookup in pycountry (name, common_name, official_name)
    try:
        country = (
            pycountry.countries.get(name=raw_query)
            or pycountry.countries.get(common_name=raw_query)
            or pycountry.countries.get(official_name=raw_query)
        )
        if country:
            return country.alpha_3
    except Exception:
        pass

    # 4. Fuzzy search in pycountry
    try:
        fuzzy_matches = pycountry.countries.search_fuzzy(raw_query)
        if fuzzy_matches:
            return fuzzy_matches[0].alpha_3
    except (LookupError, AttributeError):
        pass

    # 5. City-level resolution using CITY_MAIN_AIRPORT
    normalized_city = re.sub(r"[^\w]", "", lower_query)
    for country_key, cities in CITY_MAIN_AIRPORT.items():
        if normalized_city in cities or lower_query in cities:
            if country_key in COUNTRY_ALIASES:
                return COUNTRY_ALIASES[country_key]
            try:
                c = pycountry.countries.search_fuzzy(country_key)
                if c:
                    return c[0].alpha_3
            except (LookupError, AttributeError):
                pass

    # 6. Fallback for natural language phrases (e.g. 'flight to Paris', 'trip to Canada')
    cleaned = clean_text(raw_query)
    if cleaned and cleaned != lower_query:
        if cleaned in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[cleaned]

        try:
            fuzzy_matches = pycountry.countries.search_fuzzy(cleaned)
            if fuzzy_matches:
                return fuzzy_matches[0].alpha_3
        except (LookupError, AttributeError):
            pass

        # Inspect individual tokens and city names within the cleaned string
        for token in cleaned.split():
            if token in COUNTRY_ALIASES:
                return COUNTRY_ALIASES[token]

            norm_token = re.sub(r"[^\w]", "", token)
            for country_key, cities in CITY_MAIN_AIRPORT.items():
                if norm_token in cities or token in cities:
                    if country_key in COUNTRY_ALIASES:
                        return COUNTRY_ALIASES[country_key]

            try:
                fuzzy_token = pycountry.countries.search_fuzzy(token)
                if fuzzy_token:
                    return fuzzy_token[0].alpha_3
            except (LookupError, AttributeError):
                continue

    return ""


def airport_country_matches(airport: dict | str, country_code: str) -> bool:
    """
    Checks if an airport belongs to a target country.

    Handles:
    - airportsdata dicts (where 'country' is an ISO 2-letter alpha-2 code, e.g. 'IN', 'US')
    - 3-letter ISO alpha-3 country codes (e.g. 'IND', 'USA') from country_name_to_code
    - 2-letter ISO alpha-2 country codes (e.g. 'IN', 'US')
    - Full country names or aliases (e.g. 'India', 'United States')
    - Airport IATA string codes passed directly (e.g. 'DEL', 'JFK')
    """
    if isinstance(airport, str):
        airport = AIRPORTS.get(airport.upper())

    if not airport or not isinstance(airport, dict):
        return False

    if not country_code or not isinstance(country_code, str):
        return False

    airport_country = airport.get("country", "").strip().upper()
    target = country_code.strip()

    if not airport_country or not target:
        return False

    target_upper = target.upper()

    # Exact match (e.g. both are 'IN' or both are 'IND')
    if airport_country == target_upper:
        return True

    # Check 2-letter to 3-letter match (airportsdata uses 2-letter; system uses 3-letter)
    if len(airport_country) == 2 and len(target_upper) == 3:
        c = pycountry.countries.get(alpha_2=airport_country)
        if c and c.alpha_3 == target_upper:
            return True
    elif len(airport_country) == 3 and len(target_upper) == 2:
        c = pycountry.countries.get(alpha_3=airport_country)
        if c and c.alpha_2 == target_upper:
            return True

    # Fallback: resolve target if it is a full country name or alias
    resolved_alpha3 = country_name_to_code(target)
    if resolved_alpha3:
        if airport_country == resolved_alpha3:
            return True
        c = (
            pycountry.countries.get(alpha_2=airport_country)
            if len(airport_country) == 2
            else pycountry.countries.get(alpha_3=airport_country)
        )
        if c and c.alpha_3 == resolved_alpha3:
            return True

    return False