# Week 4: Data Explorer MCP Server

This Python project lets an MCP-compatible assistant search for countries and
look up country details. It uses `FastMCP` to expose two tools and `httpx` to call
the REST Countries v5 API at `https://api.restcountries.com/countries/v5`.

- `search_countries`: find countries by name and return their name, first capital,
  region, and population.
- `get_country_details`: look up an exact common country name and return its
  currencies, languages, borders, and flag URL.

The server communicates with its MCP client using **STDIO** (standard input and
standard output). The client starts Python and exchanges MCP messages with it.
There is no local web page or HTTP port to open. Live lookups require internet
access and a REST Countries API key; automated tests work offline.

## 1. Set up Python in Windows PowerShell

Install Python 3.10 or newer if needed. Open a separate PowerShell window and
check that the Python launcher is available:

```powershell
py -3 --version
```

If `py` is unavailable but Python is installed, use `python` instead of `py -3`
in the commands below. Confirm that it reports Python 3.10 or newer.

Go to the project folder and create a virtual environment. A virtual environment
keeps this project's Python packages separate from other projects.

```powershell
Set-Location "C:\Users\Rasheed\week4-mcp-data-explorer"
py -3 -m venv .venv
```

Replace the project path if you saved the folder somewhere else.

You can activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, continue with the explicit Python path used
below. These commands work without activation or execution-policy changes.

## 2. Install requirements

Run these commands from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt "mcp<2"
```

`requirements.txt` lists `mcp` and `httpx`. The additional `mcp<2` constraint
matches the SDK v1 requirement documented in `server.py`, which imports
`FastMCP` from `mcp.server.fastmcp`.

## 3. Set the API key securely

Obtain your key from your REST Countries account. This server reads the
`REST_COUNTRIES_API_KEY` environment variable and sends it as a Bearer token
in the API request's `Authorization` header.

In the same PowerShell window, use a hidden prompt so the key is not typed into
a saved command or displayed on screen:

```powershell
$secureApiKey = Read-Host "Enter your REST Countries API key" -AsSecureString
try {
    $env:REST_COUNTRIES_API_KEY = [System.Net.NetworkCredential]::new("", $secureApiKey).Password
}
finally {
    $secureApiKey.Dispose()
    Remove-Variable secureApiKey
}
```

Check that a non-blank value is set without printing it:

```powershell
-not [string]::IsNullOrWhiteSpace($env:REST_COUNTRIES_API_KEY)
```

The result should be `True`. The environment variable is available to this
PowerShell process and programs launched from it. It is temporary and must be
set again in a new PowerShell session. Like other environment variables, its
value is readable by programs that inherit it; the hidden prompt does not
encrypt the environment variable.

Keep the key out of source files, README examples, chat messages, screenshots,
and committed configuration. `server.py` does not load `.env` files automatically.
To remove the key from this PowerShell session when finished:

```powershell
Remove-Item Env:REST_COUNTRIES_API_KEY
```

Already-running child processes keep their own environment copy until they exit.

## 4. Run the server using STDIO

After setting the key, run:

```powershell
.\.venv\Scripts\python.exe server.py
```

This executes `mcp.run(transport="stdio")`. The process waits for MCP messages;
it is not an interactive country-search prompt. Use `Ctrl+C` to stop a manual
run. When configured in Codex, Codex starts and manages the server for you.

## 5. Register the server in the VS Code Codex extension

Install the OpenAI Codex extension in VS Code and sign in. Codex reads MCP
settings from your user configuration file, normally
`C:\Users\<your-username>\.codex\config.toml`; the CLI and extension share it.
See the [official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Open that file (create it if needed) and add the following table, preserving
existing settings. If `mcp_servers.data-explorer` already exists, edit it instead
of adding a duplicate.

```toml
[mcp_servers.data-explorer]
command = "C:/Users/Rasheed/week4-mcp-data-explorer/.venv/Scripts/python.exe"
args = ["C:/Users/Rasheed/week4-mcp-data-explorer/server.py"]
cwd = "C:/Users/Rasheed/week4-mcp-data-explorer"
env_vars = ["REST_COUNTRIES_API_KEY"]
```

Replace all three absolute paths if your project is elsewhere. Forward slashes
work in these Windows paths and avoid TOML backslash escaping. `env_vars`
forwards the named variable from Codex's environment; it does not store the key.
See the [official STDIO configuration reference](https://learn.chatgpt.com/docs/extend/mcp?surface=cli#stdio-servers).

Save your work and fully exit all VS Code windows. In the separate PowerShell
window where you set the key, launch VS Code again:

```powershell
code .
```

If `code` is unavailable, add VS Code's command-line launcher to PATH and reopen
PowerShell, then set the key again. Fully exiting VS Code first ensures the new
process can inherit the environment from this PowerShell window. Setting the key
only inside an existing VS Code terminal does not update the extension's parent
environment.

Open Codex's gear menu, select **MCP servers**, and check for `data-explorer`.
Use **Restart extension** if needed after changing configuration. These controls
are described in the [official IDE setup instructions](https://learn.chatgpt.com/docs/extend/mcp?surface=cli#configure-in-the-ide-extension).

Start a new Codex conversation and try:

> Use data-explorer to search for countries matching "Canada", with a limit of 1.

> Use data-explorer to get country details for Canada.

## 6. Tool reference

The JSON below shows the Python functions' input and return values. An MCP
client may wrap or display them differently. Outputs are illustrative fixtures,
not live API results; population values, URLs, and returned records can vary.

### `search_countries(query: str, limit: int = 5)`

Searches country names through `/name`. Leading and trailing whitespace is
removed from the query. Returns at most `limit` country objects in a list.

| Parameter | Type | Required | Rules |
| --- | --- | --- | --- |
| `query` | string | Yes | Must contain non-whitespace characters. |
| `limit` | integer | No | Defaults to `5`; must be from `1` to `100` inclusive. Booleans, strings, and floats are rejected by the function. |

Example input:

```json
{
  "query": "Canada",
  "limit": 1
}
```

Example output:

```json
[
  {
    "name": "Canada",
    "capital": "Ottawa",
    "region": "Americas",
    "population": 40000000
  }
]
```

`capital` is the name of the first capital in the API response. Missing name,
capital, region, or population values are returned as `null`.

### `get_country_details(name: str)`

Looks up an exact common country name, case-insensitively, through
`/names.common/{name}`. The name is trimmed and URL-encoded. The API request
always uses a limit of `1`; this tool has no caller-supplied `limit` parameter.

| Parameter | Type | Required | Rules |
| --- | --- | --- | --- |
| `name` | string | Yes | Must contain non-whitespace characters. Use the country's exact common name. |

Example input:

```json
{
  "name": "Canada"
}
```

Example output:

```json
{
  "name": "Canada",
  "currencies": [
    {"code": "CAD", "name": "Canadian dollar", "symbol": "$"}
  ],
  "languages": [
    {"code": "eng", "name": "English"}
  ],
  "borders": ["USA"],
  "flag_url": "https://example.test/ca.png"
}
```

Currency and language records and border ISO codes are passed through from the
API. The example flag URL is a placeholder. `flag_url` prefers `flag.url_png`,
then falls back to `flag.url_svg`, then `null`. Missing currencies, languages,
or borders become empty lists; a missing name becomes `null`.

### Errors

Both tools return structured errors. Search returns a one-item **list**
containing the error; details returns the error **object** directly.

For example, `search_countries` with `{"query": "Canada", "limit": 0}` returns:

```json
[
  {
    "error": {
      "code": "invalid_limit",
      "message": "limit must be an integer from 1 to 100."
    }
  }
]
```

`get_country_details` with `{"name": " "}` returns:

```json
{
  "error": {
    "code": "invalid_input",
    "message": "name must be a non-blank string."
  }
}
```

| Error code | Meaning |
| --- | --- |
| `invalid_input` | Query or name is blank or is not a string. |
| `invalid_limit` | Search limit is not an integer from 1 to 100. |
| `missing_api_key` | `REST_COUNTRIES_API_KEY` is missing or blank. |
| `no_results` | The API returned an empty `data.objects` array. |
| `http_error` | The API returned an HTTP error; the error also includes `status_code`. |
| `timeout` | The API request timed out; requests use `timeout=10`. |
| `network_error` | A network request failed. |
| `invalid_json` | The response could not be parsed as JSON. |
| `invalid_response` | The response envelope or country fields processed by the tool are malformed. |

An HTTP 404 is reported as `http_error` with `status_code: 404`; `no_results`
specifically represents a successful response containing an empty country list.

## 7. Run the automated tests

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_server.py
```

The tests use Python's built-in `unittest` and `unittest.mock`. They mock
`server.httpx.get`, so no live API requests or real API key are needed. They set
temporary dummy credentials and restore the environment afterward.

The suite covers both tools' successful responses, empty and invalid inputs,
no matches, HTTP errors, timeouts, network failures, invalid JSON, malformed
responses, and missing API keys. It also checks search limits and result caps,
request arguments, URL encoding, missing optional fields, and flag fallback.

A successful run ends with:

```text
Ran 32 tests in ...s

OK
```

`ok` means a test passed; `FAIL` means an assertion failed; `ERROR` means an
unexpected exception occurred. The verbose output identifies the affected test.
