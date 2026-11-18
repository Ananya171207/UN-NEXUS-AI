"""HTTP-level tests for the country endpoints. Need fastapi + httpx."""
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE_FASTAPI = True
except Exception:  # pragma: no cover
    HAVE_FASTAPI = False

from app.services import country_data as cd
from app.services import worldbank as wb
from tests.test_country_data import metadata, result  # noqa: E402


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class CountriesApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        for p in (mock.patch.object(cd, "load_metadata", return_value=metadata()),
                  mock.patch.object(wb, "fetch_bulk_many", return_value=({}, {}))):
            p.start(); self.addCleanup(p.stop)

    def test_list_has_frontend_shape(self):
        r = self.client.get("/api/countries")
        self.assertEqual(r.status_code, 200)
        india = next(c for c in r.json() if c["id"] == "IN")
        for key in ("id", "code", "name", "region", "position", "populationM", "gdpB", "indicators", "dataYears", "flag"):
            self.assertIn(key, india)
        self.assertEqual(india["code"], "IND")
        self.assertIsNone(india["populationM"])  # null, not 0

    def test_search_by_name_and_codes(self):
        self.assertEqual([c["id"] for c in self.client.get("/api/countries?q=india").json()], ["IN"])
        self.assertEqual([c["id"] for c in self.client.get("/api/countries?q=BRA").json()], ["BR"])
        self.assertEqual(self.client.get("/api/countries?q=zzzz").json(), [])

    def test_region_filter_and_validation(self):
        self.assertEqual({c["id"] for c in self.client.get("/api/countries?region=Africa").json()}, {"EG"})
        self.assertEqual(self.client.get("/api/countries?region=Atlantis").status_code, 422)

    def test_warning_header_when_data_is_incomplete(self):
        with mock.patch.object(wb, "fetch_bulk_many", return_value=({}, {"population": "HTTP 503"})):
            r = self.client.get("/api/countries")
        self.assertEqual(r.status_code, 200)
        self.assertIn("population", r.headers["X-Data-Warnings"])

    def test_single_country_and_404(self):
        self.assertEqual(self.client.get("/api/countries/IND").json()["name"], "India")
        self.assertEqual(self.client.get("/api/countries/in").json()["code"], "IND")
        r = self.client.get("/api/countries/ZZZ")
        self.assertEqual(r.status_code, 404)

    def test_profile_ok_and_partial_failure_is_still_200(self):
        results = {i.key: result(i.key) for i in wb.INDICATORS}
        results["school_enrollment"] = result("school_enrollment", "error", error="ReadTimeout")
        with mock.patch.object(wb, "fetch_country_indicators", return_value=results):
            r = self.client.get("/api/countries/IND/profile")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["country"], "IND")
        self.assertEqual(body["indicators"]["school_enrollment"]["status"], "error")
        self.assertEqual(body["missing"][0]["key"], "school_enrollment")

    def test_profile_502_only_when_everything_failed(self):
        results = {i.key: result(i.key, "error", error="down") for i in wb.INDICATORS}
        with mock.patch.object(wb, "fetch_country_indicators", return_value=results):
            self.assertEqual(self.client.get("/api/countries/IND/profile").status_code, 502)

    def test_profile_invalid_code_is_404(self):
        self.assertEqual(self.client.get("/api/countries/XXX/profile").status_code, 404)
        self.assertEqual(self.client.get("/api/countries/12/profile").status_code, 404)

    def test_compare_and_indicator_endpoints_still_registered(self):
        paths = set(app.openapi()["paths"])  # route objects differ between FastAPI versions; OpenAPI does not
        self.assertIn("/api/compare", paths)
        self.assertIn("/api/countries/{country_code}/indicators/{indicator_code}", paths)
        self.assertIn("/api/countries/{country_code}/profile", paths)

    def test_search_ranks_exact_match_first(self):
        extra = metadata() + [cd.normalize_rest_country({
            "cca2": "IO", "cca3": "IOT", "name": {"common": "British Indian Ocean Territory"},
            "region": "Africa", "subregion": "Eastern Africa", "capital": [], "latlng": [-6.0, 71.5],
            "flags": {}, "flag": "x", "independent": True})]
        with mock.patch.object(cd, "load_metadata", return_value=extra):
            ids = [c["id"] for c in self.client.get("/api/countries?q=india").json()]
        self.assertEqual(ids, ["IN", "IO"])

    def test_pending_indicators_are_reported_not_hidden(self):
        results = {i.key: result(i.key) for i in wb.INDICATORS}
        results["pm25"] = dict(result("pm25", "pending"), error="Still loading")
        with mock.patch.object(wb, "fetch_country_indicators", return_value=results):
            body = self.client.get("/api/countries/IND/profile").json()
        self.assertEqual(body["indicators"]["pm25"]["status"], "pending")
        self.assertEqual(body["missing"][0]["status"], "pending")

if __name__ == "__main__":
    unittest.main()
