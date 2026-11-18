"""A small fixed country list so location tests never touch the network."""
from app.services import country_data as cd


def _raw(cca2, cca3, name, region, subregion, capital=None, latlng=(0.0, 0.0)):
    return {
        "cca2": cca2, "cca3": cca3, "name": {"common": name}, "region": region, "subregion": subregion,
        "capital": [capital] if capital else [], "latlng": list(latlng),
        "flags": {"svg": f"https://flags.test/{cca2.lower()}.svg"}, "independent": True,
    }


RAW = [
    _raw("SD", "SDN", "Sudan", "Africa", "Northern Africa", "Khartoum", (15.0, 30.0)),
    _raw("SS", "SSD", "South Sudan", "Africa", "Middle Africa", "Juba", (7.0, 30.0)),
    _raw("NG", "NGA", "Nigeria", "Africa", "Western Africa", "Abuja", (10.0, 8.0)),
    _raw("NE", "NER", "Niger", "Africa", "Western Africa", "Niamey", (16.0, 8.0)),
    _raw("GN", "GIN", "Guinea", "Africa", "Western Africa", "Conakry", (11.0, -10.0)),
    _raw("GQ", "GNQ", "Equatorial Guinea", "Africa", "Middle Africa", "Malabo", (2.0, 10.0)),
    _raw("PG", "PNG", "Papua New Guinea", "Oceania", "Melanesia", "Port Moresby", (-6.0, 147.0)),
    _raw("CD", "COD", "DR Congo", "Africa", "Middle Africa", "Kinshasa", (0.0, 25.0)),
    _raw("CG", "COG", "Republic of the Congo", "Africa", "Middle Africa", "Brazzaville", (-1.0, 15.0)),
    _raw("TD", "TCD", "Chad", "Africa", "Middle Africa", "N'Djamena", (15.0, 19.0)),
    _raw("EG", "EGY", "Egypt", "Africa", "Northern Africa", "Cairo", (27.0, 30.0)),
    _raw("UA", "UKR", "Ukraine", "Europe", "Eastern Europe", "Kyiv", (49.0, 32.0)),
    _raw("RU", "RUS", "Russia", "Europe", "Eastern Europe", "Moscow", (60.0, 100.0)),
    _raw("FR", "FRA", "France", "Europe", "Western Europe", "Paris", (46.0, 2.0)),
    _raw("DE", "DEU", "Germany", "Europe", "Western Europe", "Berlin", (51.0, 9.0)),
    _raw("GB", "GBR", "United Kingdom", "Europe", "Northern Europe", "London", (54.0, -2.0)),
    _raw("GE", "GEO", "Georgia", "Asia", "Western Asia", "Tbilisi", (42.0, 43.5)),
    _raw("TR", "TUR", "Turkey", "Asia", "Western Asia", "Ankara", (39.0, 35.0)),
    _raw("JO", "JOR", "Jordan", "Asia", "Western Asia", "Amman", (31.0, 36.0)),
    _raw("IR", "IRN", "Iran", "Asia", "Southern Asia", "Tehran", (32.0, 53.0)),
    _raw("IL", "ISR", "Israel", "Asia", "Western Asia", "Jerusalem", (31.5, 34.75)),
    _raw("PS", "PSE", "Palestine", "Asia", "Western Asia", "Ramallah", (31.9, 35.2)),
    _raw("IN", "IND", "India", "Asia", "Southern Asia", "New Delhi", (20.0, 77.0)),
    _raw("KR", "KOR", "South Korea", "Asia", "Eastern Asia", "Seoul", (37.0, 127.5)),
    _raw("KP", "PRK", "North Korea", "Asia", "Eastern Asia", "Pyongyang", (40.0, 127.0)),
    _raw("US", "USA", "United States", "Americas", "Northern America", "Washington, D.C.", (38.0, -97.0)),
    _raw("MX", "MEX", "Mexico", "Americas", "Central America", "Mexico City", (23.0, -102.0)),
    _raw("BR", "BRA", "Brazil", "Americas", "South America", "Brasilia", (-10.0, -55.0)),
    _raw("DM", "DMA", "Dominica", "Americas", "Caribbean", "Roseau", (15.4, -61.3)),
    _raw("DO", "DOM", "Dominican Republic", "Americas", "Caribbean", "Santo Domingo", (19.0, -70.7)),
    _raw("AU", "AUS", "Australia", "Oceania", "Australia and New Zealand", "Canberra", (-27.0, 133.0)),
]

COUNTRIES = [cd.normalize_rest_country(r) for r in RAW]


def provider():
    return COUNTRIES
