from tools.flight_tool import AIRPORTS, airport_country_matches, country_name_to_code
from tools.travily_tool import tavilySearch


def test_tavily():
    query = "Top attractions in Tokyo for travelers"
    print("--- Testing Tavily Search Tool ---")
    print(f"Query: {query}\n")
    results = tavilySearch(query)
    print("--- Search Results ---")
    print(results)
    print("\n" + "=" * 50 + "\n")


def test_country_name_to_code():
    print("--- Testing country_name_to_code ---")
    test_cases = [
        "India",
        "USA",
        "United States",
        "uk",
        "Germany",
        "France",
        "Japan",
        "tokyo",
        "Dubai",
        "Sydney",
        "Toronto",
        "Kathmandu",
        "flight to Paris",
        "trip to Canada",
        "invalid_country_xyz",
    ]

    for item in test_cases:
        code = country_name_to_code(item)
        print(f"{item:<25} -> {code or '(Not Found)'}")
    print("\n" + "=" * 50 + "\n")


def test_airport_country_matches():
    print("--- Testing airport_country_matches ---")
    delhi = AIRPORTS.get("DEL")
    jfk = AIRPORTS.get("JFK")
    nrt = AIRPORTS.get("NRT")

    tests = [
        ("DEL (dict)", delhi, "IND", True),
        ("DEL (dict)", delhi, "IN", True),
        ("DEL (dict)", delhi, "India", True),
        ("DEL (dict)", delhi, "USA", False),
        ("JFK (dict)", jfk, "USA", True),
        ("JFK (dict)", jfk, "US", True),
        ("JFK (dict)", jfk, "United States", True),
        ("JFK (dict)", jfk, "IND", False),
        ("NRT (code string)", "NRT", "JPN", True),
        ("NRT (code string)", "NRT", "Japan", True),
        ("NRT (code string)", "NRT", "FRA", False),
    ]

    for desc, airport_obj, country, expected in tests:
        result = airport_country_matches(airport_obj, country)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] {desc} vs '{country}': result={result} (expected={expected})")


def main():
    test_country_name_to_code()
    test_airport_country_matches()
    # Uncomment to run Tavily search test:
    # test_tavily()


if __name__ == "__main__":
    main()
