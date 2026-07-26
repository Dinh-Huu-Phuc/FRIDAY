Developer: Dinh Huu Phuc

# BANNER FIRDAY

![Banner FIRDAY](friday/assets/img/tanthuyhoangdev.png)



# F.R.I.D.A.Y. — Tony Stark Demo

> *"Fully Responsive Intelligent Digital Assistant for You"*

A Tony Stark-inspired AI assistant split into two cooperating pieces:

| Component | What it is |
|-----------|-----------|
| **MCP Server** (`uv run friday`) | A [FastMCP](https://github.com/jlowin/fastmcp) server that exposes tools (news, web search, system info, …) over SSE. Think of it as the Stark Industries backend — it does the actual work. |
| **Voice Agent** (`uv run friday_voice`) | A [LiveKit Agents](https://github.com/livekit/agents) voice pipeline that listens to your microphone, reasons with an LLM (Gemini 2.5 Flash by default), and speaks back with OpenAI TTS — all while pulling tools from the MCP server in real time. |

---
Contact: [Facebook real](https://www.facebook.com/A.I.2302)


## How it works

```
Microphone ──► STT (Sarvam Saaras v3)
                    │
                    ▼
             LLM (Gemini 2.5 Flash)  ◄──────► MCP Server (FastMCP / SSE)
                    │                              ├─ get_world_news
                    ▼                              ├─ open_world_monitor
             TTS (OpenAI nova)                     ├─ search_web
                    │                              └─ …more tools
                    ▼
             Speaker / LiveKit room
```

$env:UV_CACHE_DIR='g:\data\FRIDAY\.uv-cache'
$env:UV_PYTHON_INSTALL_DIR='g:\data\FRIDAY\.uv-python'
uv run friday

$env:UV_CACHE_DIR='g:\data\FRIDAY\.uv-cache'
$env:UV_PYTHON_INSTALL_DIR='g:\data\FRIDAY\.uv-python'
uv run friday_voice

The voice agent connects to the MCP server via SSE at `http://127.0.0.1:8000/sse` (auto-resolved to the Windows host IP when running inside WSL).

---

## Project structure

```
friday-tony-stark-demo/
├── server/
│   ├── server.py       # uv run friday  → starts the MCP server (SSE on :8000)
│   ├── agent_friday.py # uv run friday_voice → starts the LiveKit voice agent
│   └── main.py
├── pyproject.toml
├── .env.example        # copy → .env and fill in your keys
│
└── friday/             # MCP server package
    ├── config.py       # env-var loading & app-wide settings
    ├── tools/          # MCP tools (callable by the LLM)
    │   ├── web.py      # search_web, fetch_url, get_world_news, open_world_monitor
    │   ├── system.py   # get_current_time, get_system_info
    │   └── utils.py    # format_json, word_count
    ├── prompts/        # MCP prompt templates (summarize, explain_code, …)
    └── resources/      # MCP resources exposed to clients (friday://info)
```

---

## Quick start

### 1. Prerequisites

- Python ≥ 3.11
- [`uv`](https://github.com/astral-sh/uv) — `pip install uv` or `curl -Lsf https://astral.sh/uv/install.sh | sh`
- A [LiveKit Cloud](https://cloud.livekit.io) project (free tier works)

### 2. Clone & install

```bash
git clone https://github.com/Dinh-Huu-Phuc/FRIDAY_Ai
cd friday-tony-stark-demo
uv sync          # creates .venv and installs all dependencies
```

### 3. Set up environment

```bash
cp .env.example .env
# Open .env and fill in your API keys (see the section below)
```

### 4. Run — two terminals

**Terminal 1 — MCP server** (must start first)

```bash
uv run friday
```

Starts the FastMCP server on `http://127.0.0.1:8000/sse`. The voice agent connects here to fetch its tools.

**Terminal 2 — Voice agent**

```bash
uv run friday_voice
```

Starts the LiveKit voice agent in **dev mode** — it joins a LiveKit room and begins listening. Open the [LiveKit Agents Playground](https://agents-playground.livekit.io) and connect to your room to talk to FRIDAY.

---

## `uv run friday` vs `uv run friday_voice`

| Command | Entry point | What it does |
|---------|------------|--------------|
| `uv run friday` | `server/server.py → main()` | Launches the **FastMCP server** over SSE transport on port 8000. This is the "brain backend" — it registers all tools, prompts, and resources that the LLM can call. |
| `uv run friday_voice` | `server/agent_friday.py → dev()` | Launches the **LiveKit voice agent**. It builds the STT / LLM / TTS pipeline, connects to your LiveKit room, and wires up the MCP server as a tool source. The `dev()` wrapper auto-injects the `dev` CLI flag so you don't have to type it manually. |

> Both processes must run **simultaneously**. The voice agent calls the MCP server in real time whenever it needs a tool (e.g. fetching news).

---

## Environment variables

Copy `.env.example` → `.env` and fill in the values below.

| Variable | Required | Where to get it |
|----------|----------|----------------|
| `LIVEKIT_URL` | ✅ | [LiveKit Cloud dashboard](https://cloud.livekit.io) → your project URL |
| `LIVEKIT_API_KEY` | ✅ | LiveKit Cloud → API Keys |
| `LIVEKIT_API_SECRET` | ✅ | LiveKit Cloud → API Keys |
| `GROQ_API_KEY` | optional | [console.groq.com](https://console.groq.com) — only needed if you switch `LLM_PROVIDER` to `"groq"` |
| `SARVAM_API_KEY` | ✅ (default STT) | [dashboard.sarvam.ai](https://dashboard.sarvam.ai) |
| `OPENAI_API_KEY` | ✅ (default TTS) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `DEEPGRAM_API_KEY` | optional | [console.deepgram.com](https://console.deepgram.com) |
| `GOOGLE_APPLICATION_CREDENTIALS` | optional | GCP service-account JSON path — only for `STT_PROVIDER = "google"` |
| `GOOGLE_API_KEY` | ✅ (default LLM) | [aistudio.google.com](https://aistudio.google.com/projects) |
| `SUPABASE_URL` | optional | [supabase.com](https://supabase.com) — for the ticketing tool |
| `SUPABASE_API_KEY` | optional | Supabase project → API settings |

---

## Switching providers

Open `server/agent_friday.py` and change the provider constants at the top:

```python
STT_PROVIDER = "google"   # "google" | "deepgram" | "sarvam" | "whisper"
LLM_PROVIDER = "gemini"   # "gemini" | "openai"
TTS_PROVIDER = "openai"   # "openai" | "sarvam"
```

---

## Adding a new tool

1. Create or open a file in `friday/tools/`
2. Define a `register(mcp)` function and decorate tools with `@mcp.tool()`
3. Import and call `register(mcp)` inside `friday/tools/__init__.py`

The MCP server will pick it up on next start.

---

## Tech stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP server framework
- **[LiveKit Agents](https://github.com/livekit/agents)** — real-time voice pipeline
- **Sarvam Saaras v3** — STT (Indian-English optimised)
- **Google Gemini 2.5 Flash** — LLM
- **OpenAI TTS** (`nova` voice) — TTS
- **[uv](https://github.com/astral-sh/uv)** — fast Python package manager

---

## Native Desktop UI

The main FRIDAY interface is a native PySide6 desktop window. FastAPI still runs locally on port `8001` for Swagger, extensions, browser automation bridges, and compatibility routes.
There is no separate `pageClient`, `keyApis`, login flow, or platform API-key quota layer for local solo use.

The desktop microphone runs in hands-free mode: it starts with the window, displays a live input waveform, detects a spoken turn, sends it after a short silence, pauses while FRIDAY is thinking or speaking, and resumes automatically. It remains available while the sleep display is active so wake commands can still be heard. The compatibility browser UI uses the same backend STT endpoint and includes its own live waveform.

| Command | Entry point | What it does |
|---------|------------|--------------|
| `uv run friday-api` | `friday/src/main.py -> main()` | Launches the FastAPI backend and native Windows UI. |
| `uv run friday_api` | `friday/src/main.py -> main()` | Alias for `friday-api`. |

Run it in a separate terminal:

```powershell
cd G:\data\AI_FRIDAY\v3\FRIDAY\friday-tony-stark-demo
uv run friday-api
```

The native window opens automatically. The compatibility browser UI remains available at:

```text
http://127.0.0.1:8001/
```

FastAPI docs remain available at:

```text
http://127.0.0.1:8001/docs
```

Set `FRIDAY_DESKTOP_UI_ENABLED=false` to use the compatibility browser UI as the launcher again. Set `FRIDAY_DESKTOP_STARTUP_BRIEFING=true` only when you want the slower live weather/news briefing at desktop startup.

### Code Map window

The desktop UI can open Grapuco in a separate native PySide6 window while keeping its browser session in a local persistent profile. Use one of these exact commands:

```text
FRIDAY open code map
FRIDAY close code map
```

The window includes back, forward, reload, dashboard, full-screen, and close controls. Opening it again focuses the existing window instead of creating a duplicate. It also closes automatically when FRIDAY enters sleep mode.

Configuration:

```dotenv
FRIDAY_CODE_MAP_ENABLED=true
FRIDAY_CODE_MAP_URL=https://grapuco.com/dashboard
FRIDAY_CODE_MAP_PROFILE_PATH=friday/log/runtime/code_map_profile
```

After signing in and opening a repository once, FRIDAY remembers the latest Grapuco repository URL for the next launch. The profile stays under the ignored runtime log directory and is not committed.

The graph appears only after Grapuco has indexed a repository. From the dashboard, use **Upload Repository** for a ZIP of the project, or initialize and ingest from the project root with the Grapuco CLI. When indexing finishes, open **Repositories**, select the repository, and choose **Analyze** to display its nodes and edges.

Provider retry details are written to `friday/log/runtime/friday-warnings.log` instead of flooding the terminal. Set `FRIDAY_VERBOSE_PROVIDER_LOGS=true`, `FRIDAY_CODE_MAP_JS_CONSOLE=true`, or `FRIDAY_ACCESS_LOG=true` only while debugging.

Recommended local process layout:

| Terminal | Command | Used by |
|----------|---------|---------|
| 1 | `uv run friday` | MCP tools for LiveKit / Agents Playground |
| 2 | `uv run friday_voice` | LiveKit voice agent |
| 3 | `uv run friday-api` | Native UI / REST API / docs |

---

## MCP vs FastAPI usage

FRIDAY currently has two separate server surfaces:

| Surface | Port | Consumer | Purpose |
|---------|------|----------|---------|
| MCP / SSE | `8000` | `https://agents-playground.livekit.io` through `friday_voice` | Voice agent tool calls, LiveKit agent tools, MCP resources/prompts. |
| FastAPI REST/UI | `8001` | Native UI, Swagger, extensions | Agent chat, TTS/STT, automation bridges, dashboard state, and compatibility WebSocket UI. |

Shared business logic should live under `friday/app/...`.

Adapters should stay thin:

- MCP tools live in `friday/tools/...`
- FastAPI routes live in `friday/src/router/v1/...`
- The native Windows UI lives in `friday/src/UI/static/desktop_ui/...`; the compatibility browser UI remains under `friday/src/UI/static/...`.

This keeps LiveKit, the native desktop app, and the compatibility browser UI on the same backend logic.

---

## Windows Launcher

The Windows Launcher lets FRIDAY search and open local Windows apps such as Notepad, Chrome, Calculator, or VS Code.

Shared service:

```text
friday/app/windows_launcher/
```

MCP tool adapter:

```text
friday/tools/windows_launcher.py
```

FastAPI REST adapter:

```text
friday/src/router/v1/launcher/routes.py
```

Available MCP tools:

| Tool | What it does |
|------|--------------|
| `search_windows_apps` | Searches installed Windows apps by name, similar to Start Menu search. |
| `open_windows_app` | Opens the best matching Windows app. |

Available FastAPI endpoints:

| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/api/v1/launcher/apps/search` | Search installed Windows apps. |
| `POST` | `/api/v1/launcher/apps/open` | Open the best matching app. |

Search test:

```powershell
cd G:\data\AI_FRIDAY\v3\FRIDAY\friday-tony-stark-demo
$env:UV_CACHE_DIR="G:\data\AI_FRIDAY\v3\FRIDAY\.uv-cache"
uv run python -c "from friday.app.windows_launcher.service import search_apps; print(search_apps('chrome', limit=5).model_dump(mode='json'))"
```

Open app test:

```powershell
cd G:\data\AI_FRIDAY\v3\FRIDAY\friday-tony-stark-demo
$env:UV_CACHE_DIR="G:\data\AI_FRIDAY\v3\FRIDAY\.uv-cache"
uv run python -c "from friday.app.windows_launcher.service import open_app; print(open_app(query='notepad').model_dump(mode='json'))"
```

The open test launches a real Windows app on the machine.

FastAPI test body for `/api/v1/launcher/apps/search`:

```json
{
  "query": "chrome",
  "limit": 5
}
```

FastAPI test body for `/api/v1/launcher/apps/open`:

```json
{
  "query": "notepad",
  "min_score": 0.55
}
```

---

## Testing Windows Launcher in LiveKit Agents Playground

1. Start the MCP server:

```powershell
cd G:\data\AI_FRIDAY\v3\FRIDAY\friday-tony-stark-demo
uv run friday
```

2. Start the LiveKit voice agent:

```powershell
cd G:\data\AI_FRIDAY\v3\FRIDAY\friday-tony-stark-demo
uv run friday_voice
```

3. Open:

```text
https://agents-playground.livekit.io
```

4. Say or type commands such as:

```text
Open Notepad
```

```text
FRIDAY, open Chrome for me
```

```text
Open Visual Studio Code
```

```text
Find the Calculator application on this computer
```

Expected behavior:

- The agent extracts the app name.
- It calls the shared Windows Launcher service.
- If the app launches successfully, FRIDAY can say it opened the app.
- If launching fails, FRIDAY should report the failure instead of claiming success.

If FRIDAY says the app opened but nothing appears:

1. Restart `uv run friday_voice` so the latest runtime code is loaded.
2. Confirm `uv run friday` is also running.
3. Test the service directly with the Python command above.
4. If direct Python opens the app but Playground does not, the Playground session is likely connected to an old or different voice-agent process.

---

## License

MIT
