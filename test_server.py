"""Offline unit tests for the REST Countries MCP tool functions.

Run with: python -m unittest -v test_server.py
"""

import json
import os
import unittest
from unittest.mock import patch

import httpx

import server


class CountryToolTests:
    """Shared cases, executed separately for each public tool."""

    def setUp(self):
        env_patch = patch.dict(os.environ, {"REST_COUNTRIES_API_KEY": "test-api-key"})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        request_patch = patch("server.httpx.get")
        self.mock_get = request_patch.start()
        self.addCleanup(request_patch.stop)
        self.request = httpx.Request("GET", server.BASE_URL)

    def respond_with(self, payload, status=200):
        self.mock_get.return_value = httpx.Response(
            status,
            content=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            request=self.request,
        )

    def assert_tool_error(self, result, code, status_code=None):
        if self.tool_name == "search_countries":
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            result = result[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), {"error"})
        error = result["error"]
        self.assertEqual(error["code"], code)
        self.assertIsInstance(error["message"], str)
        self.assertTrue(error["message"].strip())
        expected_keys = {"code", "message"}
        if status_code is not None:
            expected_keys.add("status_code")
            self.assertEqual(error["status_code"], status_code)
        self.assertEqual(set(error), expected_keys)
        self.assertNotIn("test-api-key", str(result))

    def test_empty_input(self):
        for value in ("", " ", "\t\n"):
            with self.subTest(value=value):
                self.assert_tool_error(self.invoke(value), "invalid_input")
        self.mock_get.assert_not_called()

    def test_non_string_input(self):
        for value in (None, 123, True, [], {}):
            with self.subTest(value=value):
                self.assert_tool_error(self.invoke(value), "invalid_input")
        self.mock_get.assert_not_called()

    def test_no_matching_country(self):
        self.respond_with({"data": {"objects": []}})
        self.assert_tool_error(self.invoke("Nonexistent country"), "no_results")
        self.mock_get.assert_called_once()

    def test_http_errors(self):
        for status in (400, 401, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                self.mock_get.reset_mock()
                self.respond_with({"message": "API error"}, status=status)
                self.assert_tool_error(self.invoke("Canada"), "http_error", status)
                self.mock_get.assert_called_once()

    def test_request_timeouts(self):
        for exception in (httpx.ConnectTimeout, httpx.ReadTimeout):
            with self.subTest(exception=exception.__name__):
                self.mock_get.reset_mock()
                self.mock_get.side_effect = exception(
                    "test-api-key must not leak", request=self.request
                )
                self.assert_tool_error(self.invoke("Canada"), "timeout")
                self.mock_get.assert_called_once()

    def test_network_failures(self):
        for exception in (httpx.ConnectError, httpx.ReadError):
            with self.subTest(exception=exception.__name__):
                self.mock_get.reset_mock()
                self.mock_get.side_effect = exception(
                    "test-api-key must not leak", request=self.request
                )
                self.assert_tool_error(self.invoke("Canada"), "network_error")
                self.mock_get.assert_called_once()

    def test_invalid_json(self):
        for content in (b"not JSON", b"<html>Service unavailable</html>", b""):
            with self.subTest(content=content):
                self.mock_get.reset_mock()
                self.mock_get.return_value = httpx.Response(
                    200, content=content, request=self.request
                )
                self.assert_tool_error(self.invoke("Canada"), "invalid_json")
                self.mock_get.assert_called_once()

    def test_malformed_response_envelope(self):
        payloads = (
            None,
            [],
            "unexpected string",
            42,
            {},
            {"data": None},
            {"data": []},
            {"data": {}},
            {"data": {"objects": None}},
            {"data": {"objects": {}}},
            {"data": {"objects": "countries"}},
            {"data": {"objects": [None]}},
            {"data": {"objects": ["Canada"]}},
            {"data": {"objects": [{"names": {"common": "Canada"}}, 42]}},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                self.mock_get.reset_mock()
                self.respond_with(payload)
                self.assert_tool_error(self.invoke("Canada"), "invalid_response")
                self.mock_get.assert_called_once()

    def test_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_tool_error(self.invoke("Canada"), "missing_api_key")
        self.mock_get.assert_not_called()

    def test_blank_api_key(self):
        with patch.dict(os.environ, {"REST_COUNTRIES_API_KEY": " \t "}):
            self.assert_tool_error(self.invoke("Canada"), "missing_api_key")
        self.mock_get.assert_not_called()


class TestSearchCountries(CountryToolTests, unittest.TestCase):
    tool_name = "search_countries"

    def invoke(self, value):
        return server.search_countries(value)

    def test_successful_response(self):
        self.respond_with({"data": {"objects": [
            {
                "names": {"common": "Canada"},
                "capitals": [{"name": "Ottawa"}, {"name": "Second capital"}],
                "region": "Americas",
                "population": 40000000,
                "unrequested_field": "ignored",
            },
            {
                "names": {"common": "Japan"},
                "capitals": [{"name": "Tokyo"}],
                "region": "Asia",
                "population": 125000000,
            },
        ]}})
        self.assertEqual(server.search_countries("  an  ", limit=2), [
            {"name": "Canada", "capital": "Ottawa", "region": "Americas",
             "population": 40000000},
            {"name": "Japan", "capital": "Tokyo", "region": "Asia",
             "population": 125000000},
        ])
        self.mock_get.assert_called_once_with(
            f"{server.BASE_URL}/name",
            params={"q": "an", "limit": 2,
                    "response_fields": "names.common,capitals,region,population"},
            headers={"Authorization": "Bearer test-api-key"},
            timeout=10,
        )

    def test_invalid_limits(self):
        for limit in (0, -1, 101, 1000, 1.5, "5", None, True, False, [], {}):
            with self.subTest(limit=limit):
                self.assert_tool_error(
                    server.search_countries("Canada", limit=limit), "invalid_limit"
                )
        self.mock_get.assert_not_called()

    def test_valid_limit_boundaries(self):
        for limit in (1, 100):
            with self.subTest(limit=limit):
                self.mock_get.reset_mock()
                self.respond_with({"data": {"objects": [
                    {"names": {"common": "Canada"}}
                ]}})
                result = server.search_countries("Canada", limit=limit)
                self.assertEqual(result[0]["name"], "Canada")
                self.mock_get.assert_called_once()
                self.assertEqual(self.mock_get.call_args.kwargs["params"]["limit"], limit)

    def test_default_limit_caps_results(self):
        self.respond_with({"data": {"objects": [
            {"names": {"common": f"Country {i}"}} for i in range(7)
        ]}})
        result = server.search_countries("Country")
        self.assertEqual([country["name"] for country in result], [
            f"Country {i}" for i in range(5)
        ])
        self.assertEqual(self.mock_get.call_args.kwargs["params"]["limit"], 5)

    def test_explicit_limit_caps_results(self):
        self.respond_with({"data": {"objects": [
            {"names": {"common": "Canada"}},
            {"names": {"common": "Japan"}},
        ]}})
        result = server.search_countries("a", limit=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Canada")

    def test_missing_optional_fields(self):
        for country in ({}, {"names": None, "capitals": None}, {"capitals": []}):
            with self.subTest(country=country):
                self.respond_with({"data": {"objects": [country]}})
                self.assertEqual(self.invoke("Canada"), [
                    {"name": None, "capital": None, "region": None, "population": None}
                ])

    def test_malformed_country_fields(self):
        for country in (
            {"names": "Canada"},
            {"names": ["Canada"]},
            {"capitals": ["Ottawa"]},
            {"capitals": [None]},
            {"capitals": {"name": "Ottawa"}},
            {"capitals": 42},
        ):
            with self.subTest(country=country):
                self.respond_with({"data": {"objects": [country]}})
                self.assert_tool_error(self.invoke("Canada"), "invalid_response")


class TestGetCountryDetails(CountryToolTests, unittest.TestCase):
    tool_name = "get_country_details"

    def invoke(self, value):
        return server.get_country_details(value)

    def test_successful_response(self):
        country = {
            "names": {"common": "Canada"},
            "currencies": [{"code": "CAD", "name": "Canadian dollar", "symbol": "$"}],
            "languages": [{"code": "eng", "name": "English"}],
            "borders": ["USA"],
            "flag": {"url_png": "https://example.test/ca.png",
                     "url_svg": "https://example.test/ca.svg"},
        }
        self.respond_with({"data": {"objects": [country]}})
        self.assertEqual(self.invoke("  cAnAdA  "), {
            "name": "Canada",
            "currencies": country["currencies"],
            "languages": country["languages"],
            "borders": ["USA"],
            "flag_url": "https://example.test/ca.png",
        })
        self.mock_get.assert_called_once_with(
            f"{server.BASE_URL}/names.common/cAnAdA",
            params={"limit": 1,
                    "response_fields": "names.common,currencies,languages,borders,flag"},
            headers={"Authorization": "Bearer test-api-key"},
            timeout=10,
        )

    def test_country_name_is_url_encoded(self):
        self.respond_with({"data": {"objects": [{"names": {"common": "Test"}}]}})
        self.invoke("  A/B & C?  ")
        self.assertEqual(self.mock_get.call_args.args[0],
                         f"{server.BASE_URL}/names.common/A%2FB%20%26%20C%3F")

    def test_svg_flag_fallback(self):
        self.respond_with({"data": {"objects": [
            {"flag": {"url_png": "", "url_svg": "https://example.test/ca.svg"}}
        ]}})
        self.assertEqual(self.invoke("Canada")["flag_url"], "https://example.test/ca.svg")

    def test_missing_optional_fields(self):
        for country in (
            {},
            {"names": None, "currencies": None, "languages": None,
             "borders": None, "flag": None},
        ):
            with self.subTest(country=country):
                self.respond_with({"data": {"objects": [country]}})
                self.assertEqual(self.invoke("Canada"), {
                    "name": None, "currencies": [], "languages": [],
                    "borders": [], "flag_url": None,
                })

    def test_malformed_country_fields(self):
        for country in (
            {"names": "Canada"},
            {"names": ["Canada"]},
            {"flag": "https://example.test/ca.png"},
            {"flag": ["https://example.test/ca.png"]},
            {"flag": 42},
        ):
            with self.subTest(country=country):
                self.respond_with({"data": {"objects": [country]}})
                self.assert_tool_error(self.invoke("Canada"), "invalid_response")


if __name__ == "__main__":
    unittest.main()
