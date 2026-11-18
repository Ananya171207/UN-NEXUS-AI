import json
import os
import sys
import tempfile
import types
import unittest
from dataclasses import replace
from unittest import mock

from app.services import country_data as cd
from app.services import country_profile as cp
from app.services import worldbank as wb


def rest(
    cca2,
    cca3,
    name,
    region,
    subregion,
    capital,
    latlng,
    independent=True,
):
    return {
        "cca2": cca2,
        "cca3": cca3,
        "name": {"common": name},
        "region": region,
        "subregion": subregion,
        "capital": [capital] if capital else [],
        "latlng": latlng,
        "flags": {"svg": f"https://flags/{cca2}.svg"},
        "flag": "x",
        "independent": independent,
    }


RAW = [
    rest("IN", "IND", "India", "Asia", "Southern Asia", "New Delhi", [20.0, 77.0]),
    rest("BR", "BRA", "Brazil", "Americas", "South America", "BrasÃlia", [-10.0, -55.0]),
    rest("MX", "MEX", "Mexico", "Americas", "Central America", "Mexico City", [23.0, -102.0]),
    rest("SA", "SAU", "Saudi Arabia", "Asia", "Western Asia", "Riyadh", [25.0, 45.0]),
    rest("EG", "EGY", "Egypt", "Africa", "Northern Africa", "Cairo", [27.0, 30.0]),
    rest("AQ", "ATA", "Antarctica", "Antarctic", None, None, [-90.0, 0.0], independent=False),
]


def metadata(n_filler=0):
    return [
        cd.normalize_rest_country(r)
        for r in RAW
        if r["independent"]
    ]


class RegionTests(unittest.TestCase):

    def test_mapping_to_the_six_frontend_regions(self):
        self.assertEqual(
            cd.to_frontend_region("Asia", "Southern Asia"),
            "Asia",
        )
        self.assertEqual(
            cd.to_frontend_region("Americas", "South America"),
            "South America",
        )
        self.assertEqual(
            cd.to_frontend_region("Americas", "Central America"),
            "North America",
        )
        self.assertEqual(
            cd.to_frontend_region("Americas", "Caribbean"),
            "North America",
        )
        self.assertEqual(
            cd.to_frontend_region("Americas", "Northern America"),
            "North America",
        )
        self.assertEqual(
            cd.to_frontend_region("Oceania", "Polynesia"),
            "Oceania",
        )

    def test_unknown_or_antarctic_gets_no_region_rather_than_a_wrong_one(self):
        self.assertIsNone(
            cd.to_frontend_region("Antarctic", None)
        )
        self.assertIsNone(
            cd.to_frontend_region(None, None)
        )

    def test_all_regions_are_in_the_frontend_vocabulary(self):
        for r in map(cd.normalize_rest_country, RAW):
            self.assertIn(
                r["region"],
                cd.FRONTEND_REGIONS + (None,),
            )

    def test_middle_east_countries_sit_under_asia_with_subregion_preserved(self):
        saudi = cd.normalize_rest_country(RAW[3])

        self.assertEqual(
            (saudi["region"], saudi["subregion"]),
            ("Asia", "Western Asia"),
        )

        self.assertEqual(
            cd.normalize_rest_country(RAW[4])["region"],
            "Africa",
        )


class NormalizeTests(unittest.TestCase):

    def test_fields(self):
        c = cd.normalize_rest_country(RAW[0])

        self.assertEqual(
            (c["id"], c["code"], c["name"], c["capital"]),
            ("IN", "IND", "India", "New Delhi"),
        )

        self.assertEqual(c["position"], [20.0, 77.0])
        self.assertEqual(c["flag"], "https://flags/IN.svg")

    def test_missing_coordinates_give_null_position_not_zero(self):
        raw = rest(
            "XX", "XXX", "Nowhere",
            "Asia", "Southern Asia", None, [],
        )

        c = cd.normalize_rest_country(raw)

        self.assertIsNone(c["position"])
        self.assertIsNone(c["latitude"])
        self.assertIsNone(c["capital"])

    def test_incomplete_records_are_dropped(self):
        self.assertIsNone(
            cd.normalize_rest_country({"cca2": "IN"})
        )

    def test_flag_emoji(self):
        self.assertEqual(
            cd.flag_emoji("IN"),
            "\U0001F1EE\U0001F1F3",
        )
        self.assertIsNone(cd.flag_emoji("India"))
        self.assertIsNone(cd.flag_emoji(None))


class V5NormalizeTests(unittest.TestCase):

    def _india(self):
        return {
            "names": {"common": "India"},
            "codes": {
                "alpha_2": "IN",
                "alpha_3": "IND",
            },
            "region": "Asia",
            "subregion": "Southern Asia",
            "capitals": [
                {
                    "name": "New Delhi",
                    "attributes": {"primary": True},
                    "coordinates": {
                        "lat": 28.6139,
                        "lng": 77.2090,
                    },
                }
            ],
            "coordinates": {
                "lat": 20.0,
                "lng": 77.0,
            },
            "flag": {
                "emoji": "🇮🇳",
                "url_svg": "https://flags/in.svg",
                "url_png": "https://flags/in.png",
            },
            "classification": {
                "sovereign": True,
                "dependency": False,
                "disputed": False,
            },
        }

    def test_v5_india_normalization(self):
        country = cd.normalize_rest_country(self._india())

        self.assertEqual(country["id"], "IN")
        self.assertEqual(country["code"], "IND")
        self.assertEqual(country["name"], "India")
        self.assertEqual(country["region"], "Asia")
        self.assertEqual(country["subregion"], "Southern Asia")
        self.assertEqual(country["capital"], "New Delhi")
        self.assertEqual(country["position"], [20.0, 77.0])
        self.assertEqual(country["flag"], "https://flags/in.svg")
        self.assertEqual(country["flagEmoji"], "🇮🇳")
        self.assertTrue(country["independent"])

    def test_v5_primary_capital_is_selected(self):
        raw = self._india()

        raw["capitals"] = [
            {
                "name": "Other City",
                "attributes": {"primary": False},
            },
            {
                "name": "New Delhi",
                "attributes": {"primary": True},
            },
        ]

        country = cd.normalize_rest_country(raw)

        self.assertEqual(
            country["capital"],
            "New Delhi",
        )

    def test_v5_dependency_is_not_independent(self):
        raw = self._india()
        raw["classification"]["dependency"] = True

        country = cd.normalize_rest_country(raw)

        self.assertFalse(country["independent"])

    def test_v5_missing_iso_codes_is_rejected(self):
        raw = self._india()
        raw["codes"] = {
            "alpha_2": "",
            "alpha_3": "",
        }

        self.assertIsNone(
            cd.normalize_rest_country(raw)
        )

    def test_v5_missing_coordinates_gives_null_position(self):
        raw = self._india()
        raw["coordinates"] = {}

        country = cd.normalize_rest_country(raw)

        self.assertIsNone(country["position"])
        self.assertIsNone(country["latitude"])
        self.assertIsNone(country["longitude"])


class TolerantParsingTests(unittest.TestCase):

    def test_name_and_flags_given_as_plain_strings(self):
        raw = {
            "cca2": "IN",
            "cca3": "IND",
            "name": "India",
            "region": "Asia",
            "subregion": "Southern Asia",
            "capital": "New Delhi",
            "latlng": [20, 77],
            "flags": "https://flags/in.svg",
            "independent": True,
        }

        c = cd.normalize_rest_country(raw)

        self.assertEqual(
            (c["name"], c["capital"], c["flag"]),
            ("India", "New Delhi", "https://flags/in.svg"),
        )

    def test_garbage_items_are_skipped_not_fatal(self):
        for junk in (
            "India",
            None,
            5,
            [],
            {"cca2": 7, "cca3": "X", "name": {"common": "X"}},
        ):
            self.assertIsNone(
                cd.normalize_rest_country(junk)
            )

    def test_wrongly_typed_fields_degrade_to_null(self):
        raw = {
            "cca2": "IN",
            "cca3": "IND",
            "name": {"common": "India"},
            "region": 5,
            "latlng": "20,77",
            "capital": 3,
            "flags": 9,
            "flag": ["x"],
        }

        c = cd.normalize_rest_country(raw)

        self.assertIsNone(c["region"])
        self.assertIsNone(c["position"])
        self.assertIsNone(c["capital"])

        self.assertEqual(
            c["flagEmoji"],
            cd.flag_emoji("IN"),
        )


class LoadingTests(unittest.TestCase):

    def setUp(self):
        cd.reset_state()

        self.tmp = tempfile.mkdtemp()
        self.snapshot = os.path.join(
            self.tmp,
            "snap.json",
        )

        patcher = mock.patch.object(
            cd,
            "settings",
            replace(
                cd.settings,
                countries_snapshot_path=self.snapshot,
            ),
        )

        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(cd.reset_state)

        big = [
            cd.normalize_rest_country(
                rest(
                    f"{a}{b}",
                    f"{a}{b}X",
                    f"Country {a}{b}",
                    "Africa",
                    "Eastern Africa",
                    None,
                    [1.0, 2.0],
                )
            )
            for a in "ABCDEFGHIJKLMNOP"
            for b in "ABCDEFGHIJ"
        ]

        self.big = big

        self.raw_big = [
            rest(
                f"{a}{b}",
                f"{a}{b}X",
                f"Country {a}{b}",
                "Africa",
                "Eastern Africa",
                None,
                [1.0, 2.0],
            )
            for a in "ABCDEFGHIJKLMNOP"
            for b in "ABCDEFGHIJ"
        ]

    def _ok(self):
        resp = mock.Mock()

        resp.json.return_value = {
            "data": {
                "objects": self.raw_big,
                "meta": {
                    "total": len(self.raw_big),
                    "count": len(self.raw_big),
                    "limit": 100,
                    "offset": 0,
                    "more": False,
                },
            }
        }

        resp.raise_for_status.return_value = None

        return resp

    def test_success_is_cached_and_written_to_snapshot(self):
        with mock.patch.object(
            cd.requests,
            "get",
            return_value=self._ok(),
        ) as get:
            cd.load_metadata()
            cd.load_metadata()

        self.assertEqual(get.call_count, 1)
        self.assertTrue(os.path.exists(self.snapshot))

    def test_non_independent_territories_are_excluded(self):
        raw = self.raw_big + [
            rest(
                "PR",
                "PRI",
                "Puerto Rico",
                "Americas",
                "Caribbean",
                "San Juan",
                [1.0, 1.0],
                independent=False,
            )
        ]

        resp = self._ok()

        resp.json.return_value = {
            "data": {
                "objects": raw,
                "meta": {
                    "total": len(raw),
                    "count": len(raw),
                    "limit": 100,
                    "offset": 0,
                    "more": False,
                },
            }
        }

        with mock.patch.object(
            cd.requests,
            "get",
            return_value=resp,
        ):
            self.assertNotIn(
                "PRI",
                {
                    c["code"]
                    for c in cd.load_metadata()
                },
            )

    def test_suspiciously_small_response_is_rejected(self):
        resp = self._ok()

        resp.json.return_value = {
            "data": {
                "objects": self.raw_big[:10],
                "meta": {
                    "total": 10,
                    "count": 10,
                    "limit": 100,
                    "offset": 0,
                    "more": False,
                },
            }
        }

        with mock.patch.object(
            cd.requests,
            "get",
            return_value=resp,
        ), mock.patch.object(
            cd,
            "_pycountry_fallback",
            return_value=[{
                "id": "ZZ",
                "code": "ZZZ",
                "name": "Z",
                "metadataSource": cd.SOURCE_FALLBACK,
            }],
        ):
            self.assertEqual(
                cd.load_metadata()[0]["metadataSource"],
                cd.SOURCE_FALLBACK,
            )

    def test_non_list_payload_is_rejected_with_a_helpful_error(self):
        resp = self._ok()

        resp.json.return_value = {
            "status": 400,
            "message": "Bad Request",
        }

        with mock.patch.object(
            cd.requests,
            "get",
            return_value=resp,
        ):
            with self.assertRaises(ValueError) as ctx:
                cd._fetch_rest_countries()

        self.assertIn(
            "Bad Request",
            str(ctx.exception),
        )

    def test_failure_uses_snapshot_file(self):
        with open(
            self.snapshot,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(self.big, f)

        with mock.patch.object(
            cd.requests,
            "get",
            side_effect=OSError("down"),
        ):
            result = cd.load_metadata()

        self.assertEqual(len(result), 160)

        self.assertEqual(
            result[0]["metadataSource"],
            cd.SOURCE_REST,
        )

    def test_no_snapshot_falls_back_to_pycountry_and_says_so(self):
        fake = types.SimpleNamespace(
            countries=[
                types.SimpleNamespace(
                    alpha_2="IN",
                    alpha_3="IND",
                    name="India",
                )
            ]
        )

        with mock.patch.dict(
            sys.modules,
            {"pycountry": fake},
        ), mock.patch.object(
            cd.requests,
            "get",
            side_effect=OSError("down"),
        ):
            result = cd.load_metadata()

        self.assertEqual(result[0]["code"], "IND")
        self.assertIsNone(result[0]["region"])
        self.assertIsNone(result[0]["position"])

        self.assertEqual(
            result[0]["metadataSource"],
            cd.SOURCE_FALLBACK,
        )

    def test_failed_fetch_is_not_retried_during_cooldown(self):
        fake = types.SimpleNamespace(countries=[])

        with mock.patch.dict(
            sys.modules,
            {"pycountry": fake},
        ), mock.patch.object(
            cd.requests,
            "get",
            side_effect=OSError("down"),
        ) as get:
            cd.load_metadata()
            cd.load_metadata()
            cd.load_metadata()

        self.assertEqual(get.call_count, 1)

    def test_v5_pagination_fetches_all_pages(self):
        pages = []

        for offset, count, more in (
            (0, 100, True),
            (100, 100, True),
            (200, 54, False),
        ):
            objects = []

            for index in range(count):
                number = offset + index

                objects.append({
                    "names": {
                        "common": f"Country {number:03d}",
                    },
                    "codes": {
                        "alpha_2": f"A{chr(65 + number % 26)}",
                        "alpha_3": f"{number:03d}",
                    },
                    "region": "Africa",
                    "subregion": "Eastern Africa",
                    "capitals": [],
                    "coordinates": {
                        "lat": 1.0,
                        "lng": 2.0,
                    },
                    "flag": {
                        "emoji": "🌍",
                        "url_svg": "https://flags/example.svg",
                    },
                    "classification": {
                        "sovereign": True,
                        "dependency": False,
                    },
                })

            pages.append({
                "data": {
                    "objects": objects,
                    "meta": {
                        "total": 254,
                        "count": count,
                        "limit": 100,
                        "offset": offset,
                        "more": more,
                    },
                }
            })

        responses = []

        for page in pages:
            resp = mock.Mock()
            resp.json.return_value = page
            resp.raise_for_status.return_value = None
            responses.append(resp)

        with mock.patch.object(
            cd.requests,
            "get",
            side_effect=responses,
        ) as get:
            countries = cd._fetch_rest_countries()

        self.assertEqual(len(countries), 254)
        self.assertEqual(get.call_count, 3)

        offsets = [
            call.kwargs["params"]["offset"]
            for call in get.call_args_list
        ]

        self.assertEqual(offsets, [0, 100, 200])

    def test_v5_request_uses_bearer_authentication(self):
        with mock.patch.object(
            cd,
            "settings",
            replace(
                cd.settings,
                rest_countries_api_key="test-key",
            ),
        ), mock.patch.object(
            cd.requests,
            "get",
            return_value=self._ok(),
        ) as get:
            cd._fetch_rest_countries()

        headers = get.call_args.kwargs["headers"]

        self.assertEqual(
            headers["Authorization"],
            "Bearer test-key",
        )


class FindAndListTests(unittest.TestCase):

    def setUp(self):
        wb.reset_cache()
        self.addCleanup(wb.reset_cache)

        p = mock.patch.object(
            cd,
            "load_metadata",
            return_value=metadata(),
        )

        p.start()
        self.addCleanup(p.stop)

    def test_find_by_alpha2_alpha3_any_case(self):
        for code in ("IN", "in", "IND", "ind", " Ind "):
            self.assertEqual(
                cd.find_country(code)["name"],
                "India",
            )

        for bad in ("", "XX", "INDIA", "1N", None):
            self.assertIsNone(
                cd.find_country(bad)
            )

    def _bulk(self, values):
        return mock.patch.object(
            wb,
            "fetch_bulk_many",
            return_value=(values, {}),
        )

    def test_list_shape_matches_frontend_contract(self):
        bulk = {
            "population": {
                "IND": {
                    "value": 1_428_000_000,
                    "year": "2023",
                }
            },
            "gdp": {
                "IND": {
                    "value": 3.55e12,
                    "year": "2023",
                }
            },
            "life_expectancy": {
                "IND": {
                    "value": 67.74,
                    "year": "2023",
                }
            },
            "renewable_electricity": {
                "IND": {
                    "value": 21.04,
                    "year": "2022",
                }
            },
            "internet_use": {
                "IND": {
                    "value": 46.3,
                    "year": "2023",
                }
            },
        }

        with self._bulk(bulk):
            items, warnings = cd.list_countries()

        india = next(
            c for c in items
            if c["id"] == "IN"
        )

        self.assertEqual(india["populationM"], 1428.0)
        self.assertEqual(india["gdpB"], 3550.0)

        self.assertEqual(
            india["indicators"],
            {
                "lifeExpectancy": 67.7,
                "renewableShare": 21.0,
                "internetUse": 46.3,
            },
        )

        self.assertEqual(
            india["position"],
            [20.0, 77.0],
        )

        self.assertEqual(
            india["dataYears"]["renewableShare"],
            "2022",
        )

        self.assertEqual(warnings, [])

        for key in (
            "id",
            "name",
            "region",
            "position",
            "populationM",
            "gdpB",
            "indicators",
        ):
            self.assertIn(key, india)

    def test_missing_world_bank_values_are_null_not_zero(self):
        with self._bulk({
            k: {}
            for k in (
                "population",
                "gdp",
                "life_expectancy",
                "renewable_electricity",
                "internet_use",
            )
        }):
            items, _ = cd.list_countries()

        brazil = next(
            c for c in items
            if c["id"] == "BR"
        )

        self.assertIsNone(brazil["populationM"])
        self.assertIsNone(brazil["gdpB"])

        self.assertEqual(
            brazil["indicators"],
            {
                "lifeExpectancy": None,
                "renewableShare": None,
                "internetUse": None,
            },
        )

    def test_world_bank_aggregates_never_appear_as_countries(self):
        bulk = {
            "population": {
                "WLD": {
                    "value": 8e9,
                    "year": "2023",
                }
            }
        }

        with self._bulk(bulk):
            items, _ = cd.list_countries()

        self.assertNotIn(
            "WLD",
            {c["code"] for c in items},
        )

    def test_search_and_region_filter(self):
        with self._bulk({}):
            self.assertEqual(
                [c["id"] for c in cd.list_countries("ind")[0]],
                ["IN"],
            )

            self.assertEqual(
                [c["id"] for c in cd.list_countries("br")[0]],
                ["BR"],
            )

            self.assertEqual(
                [c["id"] for c in cd.list_countries("BRA")[0]],
                ["BR"],
            )

            self.assertEqual(
                {
                    c["id"]
                    for c in cd.list_countries(region="Asia")[0]
                },
                {"IN", "SA"},
            )

            self.assertEqual(
                cd.list_countries("nowhere")[0],
                [],
            )

    def test_search_ranks_exact_then_prefix_then_contains(self):
        extra = [
            cd.normalize_rest_country(
                rest(
                    "IO",
                    "IOT",
                    "British Indian Ocean Territory",
                    "Africa",
                    "Eastern Africa",
                    None,
                    [1.0, 2.0],
                )
            ),
            cd.normalize_rest_country(
                rest(
                    "ID",
                    "IDN",
                    "Indonesia",
                    "Asia",
                    "South-Eastern Asia",
                    "Jakarta",
                    [1.0, 2.0],
                )
            ),
        ]

        with mock.patch.object(
            cd,
            "load_metadata",
            return_value=metadata() + extra,
        ), self._bulk({}):
            ids = [
                c["id"]
                for c in cd.list_countries("ind")[0]
            ]

            self.assertEqual(ids[:2], ["IN", "ID"])
            self.assertEqual(ids[-1], "IO")

            self.assertEqual(
                cd.list_countries("india")[0][0]["id"],
                "IN",
            )

    def test_bulk_failure_gives_warning_and_still_returns_countries(self):
        with mock.patch.object(
            wb,
            "fetch_bulk_many",
            return_value=({}, {"population": "HTTP 503"}),
        ):
            items, warnings = cd.list_countries()

        self.assertEqual(len(items), 5)
        self.assertEqual(
            warnings,
            ["population: HTTP 503"],
        )

    def test_fallback_metadata_adds_a_warning(self):
        fallback = [
            dict(c, metadataSource=cd.SOURCE_FALLBACK)
            for c in metadata()
        ]

        with mock.patch.object(
            cd,
            "load_metadata",
            return_value=fallback,
        ), self._bulk({}):
            _, warnings = cd.list_countries()

        self.assertTrue(
            any("limited" in w for w in warnings)
        )


def result(
    key,
    status="available",
    value=1.0,
    year="2024",
    error=None,
):
    i = wb.BY_KEY[key]

    return {
        "key": key,
        "label": i.label,
        "unit": i.unit,
        "group": i.group,
        "value": value if status == "available" else None,
        "year": year if status == "available" else None,
        "source": wb.SOURCE_NAME,
        "sourceCode": i.code,
        "indicatorName": "n",
        "status": status,
        "stale": False,
        "error": error,
        "sourceLastUpdated": "2026-10-08",
        "fetchedAt": "2026-11-10T10:00:00Z",
    }


class ProfileTests(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(
            cd,
            "load_metadata",
            return_value=metadata(),
        )

        p.start()
        self.addCleanup(p.stop)

    def _profile(self, results):
        with mock.patch.object(
            wb,
            "fetch_country_indicators",
            return_value=results,
        ):
            return cp.get_profile("IND")

    def test_structure(self):
        keys = [i.key for i in wb.INDICATORS]

        profile = self._profile({
            k: result(k)
            for k in keys
        })

        self.assertEqual(profile["country"], "IND")
        self.assertEqual(
            profile["source"],
            "World Bank Open Data",
        )
        self.assertEqual(
            profile["identity"]["id"],
            "IN",
        )
        self.assertEqual(
            profile["identity"]["capital"],
            "New Delhi",
        )
        self.assertEqual(
            profile["indicators"]["gdp_per_capita"]["year"],
            "2024",
        )
        self.assertEqual(
            profile["indicators"]["gdp_per_capita"]["value"],
            1.0,
        )
        self.assertEqual(profile["missing"], [])
        self.assertEqual(
            profile["lastUpdated"],
            "2026-11-10T10:00:00Z",
        )

        for group in (
            "economic",
            "social",
            "environmental",
        ):
            self.assertTrue(profile["groups"][group])

        self.assertEqual(
            sum(
                len(v)
                for v in profile["groups"].values()
            ),
            len(keys),
        )

    def test_missing_indicators_are_listed_with_reason(self):
        keys = [i.key for i in wb.INDICATORS]

        results = {
            k: result(k)
            for k in keys
        }

        results["school_enrollment"] = result(
            "school_enrollment",
            "error",
            error="ReadTimeout: slow",
        )

        results["poverty_rate"] = result(
            "poverty_rate",
            "no_data",
        )

        profile = self._profile(results)

        missing = {
            m["key"]: m
            for m in profile["missing"]
        }

        self.assertEqual(
            missing["school_enrollment"]["status"],
            "error",
        )
        self.assertEqual(
            missing["school_enrollment"]["reason"],
            "ReadTimeout: slow",
        )
        self.assertEqual(
            missing["poverty_rate"]["status"],
            "no_data",
        )
        self.assertIsNone(
            profile["indicators"]["school_enrollment"]["value"]
        )

    def test_one_failed_indicator_still_returns_a_profile(self):
        keys = [i.key for i in wb.INDICATORS]

        results = {
            k: result(k)
            for k in keys
        }

        results["school_enrollment"] = result(
            "school_enrollment",
            "error",
            error="timeout",
        )

        self.assertEqual(
            self._profile(results)["country"],
            "IND",
        )

    def test_all_failed_raises(self):
        results = {
            i.key: result(
                i.key,
                "error",
                error="down",
            )
            for i in wb.INDICATORS
        }

        with self.assertRaises(cp.NoDataAvailable):
            self._profile(results)

    def test_all_no_data_is_still_a_valid_profile(self):
        results = {
            i.key: result(i.key, "no_data")
            for i in wb.INDICATORS
        }

        self.assertEqual(
            len(self._profile(results)["missing"]),
            len(wb.INDICATORS),
        )

    def test_unknown_country_raises(self):
        with self.assertRaises(cp.CountryNotFound):
            cp.get_profile("XXX")

    def test_alpha2_and_alpha3_both_work(self):
        keys = [i.key for i in wb.INDICATORS]

        with mock.patch.object(
            wb,
            "fetch_country_indicators",
            return_value={
                k: result(k)
                for k in keys
            },
        ) as f:
            cp.get_profile("in")

        f.assert_called_once_with("IND")


if __name__ == "__main__":
    unittest.main()
