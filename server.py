"""Data Explorer — REST Countries v5 tools over MCP STDIO for Assignment 4.

Setup:
    pip install -r requirements.txt "mcp<2"
    FastMCP is provided by MCP SDK v1; SDK v2 removed this class.
    Set REST_COUNTRIES_API_KEY in the environment before starting the server.
Run (STDIO) — register this command in your MCP client (e.g. Claude Desktop / an IDE):
    python server.py
"""
import os
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.restcountries.com/countries/v5"
mcp = FastMCP("data-explorer")


def _error(code: str, message: str, **details) -> dict:
    """Use the same error structure in both tools without exposing credentials."""
    return {"error": {"code": code, "message": message, **details}}


def _request_countries(path: str, params: dict) -> list[dict] | dict:
    """Fetch and validate the v5 response envelope, or return a structured error."""
    api_key = os.environ.get("REST_COUNTRIES_API_KEY", "").strip()
    if not api_key:
        return _error(
            "missing_api_key", "Set the REST_COUNTRIES_API_KEY environment variable."
        )

    try:
        resp = httpx.get(
            f"{BASE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.TimeoutException:
        return _error("timeout", "The REST Countries request timed out.")
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        return _error(
            "http_error",
            f"REST Countries returned HTTP {status}.",
            status_code=status,
        )
    except httpx.RequestError:
        return _error("network_error", "Unable to connect to REST Countries.")

    try:
        payload = resp.json()
    except ValueError:
        return _error("invalid_json", "REST Countries returned invalid JSON.")

    data = payload.get("data") if isinstance(payload, dict) else None
    objects = data.get("objects") if isinstance(data, dict) else None
    if not isinstance(objects, list) or any(
        not isinstance(country, dict) for country in objects
    ):
        return _error("invalid_response", "Expected a data.objects array of countries.")
    if not objects:
        return _error("no_results", "No countries matched the supplied input.")
    return objects


@mcp.tool()
def search_countries(query: str, limit: int = 5) -> list[dict]:
    """Search country names; return name, first capital, region, and population.

    limit must be an integer from 1 to 100. Failures return a one-item list
    containing {error: {code, message}} (and status_code for HTTP errors).
    """
    if not isinstance(query, str) or not query.strip():
        return [_error("invalid_input", "query must be a non-blank string.")]
    if type(limit) is not int or not 1 <= limit <= 100:
        return [_error("invalid_limit", "limit must be an integer from 1 to 100.")]

    countries = _request_countries(
        "/name",
        {
            "q": query.strip(),
            "limit": limit,
            "response_fields": "names.common,capitals,region,population",
        },
    )
    if isinstance(countries, dict):
        return [countries]

    try:
        return [
            {
                "name": (c.get("names") or {}).get("common"),
                "capital": ((c.get("capitals") or [{}])[0]).get("name"),
                "region": c.get("region"),
                "population": c.get("population"),
            }
            for c in countries[:limit]
        ]
    except (AttributeError, TypeError, KeyError):
        return [_error("invalid_response", "Country names or capitals are malformed.")]


@mcp.tool()
def get_country_details(name: str) -> dict:
    """Look up an exact common country name (case-insensitive).

    Return name, v5 currency and language records, border ISO codes, and flag_url.
    Failures return {error: {code, message}} and status_code for HTTP errors.
    """
    if not isinstance(name, str) or not name.strip():
        return _error("invalid_input", "name must be a non-blank string.")

    countries = _request_countries(
        f"/names.common/{quote(name.strip(), safe='')}",
        {
            "limit": 1,
            "response_fields": "names.common,currencies,languages,borders,flag",
        },
    )
    if isinstance(countries, dict):
        return countries

    country = countries[0]
    try:
        flag = country.get("flag") or {}
        return {
            "name": (country.get("names") or {}).get("common"),
            "currencies": country.get("currencies") or [],
            "languages": country.get("languages") or [],
            "borders": country.get("borders") or [],
            "flag_url": flag.get("url_png") or flag.get("url_svg"),
        }
    except (AttributeError, TypeError):
        return _error("invalid_response", "Country names or flag data are malformed.")


if __name__ == "__main__":
    mcp.run(transport="stdio")
