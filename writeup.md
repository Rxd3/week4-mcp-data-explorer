
# Week 4 — Data Explorer MCP Server

## Overview

For this assignment, I built a Python MCP server using FastMCP and connected it to the Codex extension in VS Code. The server uses the REST Countries API and provides two tools: `search_countries` to look up countries and `get_country_details` to return more detailed information. I ran both tools through Codex using the MCP connection, rather than calling the Python functions manually.

## 1. Agent Tool-Call Transcript

### Tool 1 — `search_countries`

**My message to Codex:**

> Use the data-explorer MCP server's search_countries tool to search for countries with "Can" in their name. Set limit to 5. Show me the tool call arguments and the raw response. Do not use web search.

**Tool called by Codex:** `mcp__data_explorer__search_countries`

**Arguments:**

```json
{"query": "Can", "limit": 5}
```

**Returned structured result:**

```json
{
  "result": [
    {"name": "American Samoa", "capital": "Pago Pago", "region": "Oceania", "population": 43268},
    {"name": "Azerbaijan", "capital": "Baku", "region": "Asia", "population": 10273450},
    {"name": "Canada", "capital": "Ottawa", "region": "Americas", "population": 41798407},
    {"name": "Central African Republic", "capital": "Bangui", "region": "Africa", "population": 5513282},
    {"name": "Dominican Republic", "capital": "Santo Domingo", "region": "Americas", "population": 11532151}
  ]
}
```

**MCP status:** `isError: false`

Codex successfully called the tool and returned structured country data. I noticed that some names in the result do not actually contain "Can", so the search matching could still be improved even though the MCP call worked.

### Tool 2 — `get_country_details`

**My message to Codex:**

> Use the data-explorer MCP server's get_country_details tool with name="Canada". Show the tool call arguments and the raw response, including currencies, languages, borders, and flag_url. Do not use web search.

**Tool called by Codex:** `mcp__data_explorer__get_country_details`

**Arguments:**

```json
{"name": "Canada"}
```

**Returned data (main fields from the tool response):**

```json
{
  "name": "Canada",
  "currencies": [
    {"code": "CAD", "name": "Canadian dollar", "symbol": "$"}
  ],
  "languages": [
    {"name": "English", "native_name": "English"},
    {"name": "French", "native_name": "français"}
  ],
  "borders": ["USA"],
  "flag_url": "https://flags.restcountries.com/v5/w640/ca.png"
}
```

**MCP status:** `isError: false`

This call returned Canada's currency, languages, bordering country, and flag URL. I shortened the language objects above to the relevant fields; the actual response also included language codes.

## 2. Error Handling and Testing

I added input checks so an empty country name or search query returns a clear error. For `search_countries`, I also validate the `limit` parameter so it must be between 1 and 100. The server handles cases such as no results, HTTP errors, request timeouts, network failures, and unexpected API responses by returning structured error messages instead of crashing.

I asked Codex to create a `test_server.py` file using Python's `unittest` and mocked API calls, so the tests would not rely on a live internet connection. Codex reported **29 tests passed and 0 failed**, covering successful responses, invalid inputs, missing countries, HTTP errors, timeouts, network failures, and malformed data.

## 3. What I Learned

I learned that an MCP server lets an AI assistant use tools I build instead of only relying on what it already knows. By exposing just two country tools, I can control which external information Codex is able to request and how it receives the results. I also learned that validating inputs and handling API errors are important because the external service might fail or return unexpected data. The most interesting part was seeing Codex discover and call my tools directly from the chat in VS Code.
