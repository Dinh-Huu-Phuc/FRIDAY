# FRIDAY AI

FRIDAY là trợ lý AI chạy trên Windows, kết hợp:

- Native desktop UI viết bằng Python và PySide6.
- FastAPI REST backend chạy local.
- PostgreSQL/Supabase để lưu dữ liệu bền vững.
- Ollama + Gemma 3 để hiểu hình ảnh và màn hình ở local.
- OpenAI-compatible LLM/STT, Sarvam/OpenAI TTS, Groq refiner và Google Search tùy cấu hình.
- Chrome automation, sleep display đa màn hình, Live Search, Code Map và LiveKit voice agent.

Source chính nằm trong:

```text
FRIDAY/
└── friday-tony-stark-demo/
```

<<<<<<< HEAD
http://127.0.0.1:8001/

Developer: Dinh Huu Phuc

# BANNER FIRDAY

![Banner FIRDAY]([friday/assets/img/tanthuyhoangdev.png](https://github.com/Dinh-Huu-Phuc/FRIDAY/blob/master/img/Friday.jpg))



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
=======
Tài liệu này hướng dẫn chuyển dự án sang một máy Windows mới từ đầu. Các lệnh bên dưới dùng PowerShell.

## Mục lục

1. [Kiến trúc và cổng mạng](#kiến-trúc-và-cổng-mạng)
2. [Yêu cầu phần cứng và hệ điều hành](#yêu-cầu-phần-cứng-và-hệ-điều-hành)
3. [Những phần mềm phải cài](#những-phần-mềm-phải-cài)
4. [Dữ liệu phải sao lưu từ máy cũ](#dữ-liệu-phải-sao-lưu-từ-máy-cũ)
5. [Cài đặt trên máy mới](#cài-đặt-trên-máy-mới)
6. [Cấu hình biến môi trường](#cấu-hình-biến-môi-trường)
7. [Kết nối Supabase và chạy migration](#kết-nối-supabase-và-chạy-migration)
8. [Cấu hình microphone, loa và Chrome](#cấu-hình-microphone-loa-và-chrome)
9. [Khởi động FRIDAY](#khởi-động-friday)
10. [Kiểm tra sau cài đặt](#kiểm-tra-sau-cài-đặt)
11. [Tính năng và công cụ tùy chọn](#tính-năng-và-công-cụ-tùy-chọn)
12. [Xử lý lỗi thường gặp](#xử-lý-lỗi-thường-gặp)

## Kiến trúc và cổng mạng

| Thành phần | Lệnh | Cổng | Mục đích |
|---|---|---:|---|
| Native UI + FastAPI | `uv run friday-api` | `8001` | Giao diện desktop, chat, STT/TTS, browser bridge, Swagger |
| MCP server | `uv run friday` | `8000` | MCP tools qua SSE |
| LiveKit voice agent | `uv run friday_voice` | Không cố định | Voice pipeline cho LiveKit Agents Playground |
| Ollama | Tự chạy cùng Windows hoặc `ollama serve` | `11434` | Gemma 3 local vision |
| Supabase PostgreSQL | Kết nối Internet | `5432` thường dùng | Database và migration |

Với nhu cầu dùng ứng dụng desktop thông thường, chỉ cần:

```powershell
uv run friday-api
```

Không cần chạy MCP server và LiveKit voice agent nếu không dùng Agents Playground.

## Yêu cầu phần cứng và hệ điều hành

### Bắt buộc

| Hạng mục | Yêu cầu |
|---|---|
| Hệ điều hành | Windows 10/11 64-bit; Windows 11 được khuyến nghị |
| CPU | x64 hiện đại; ARM Windows chưa phải cấu hình đã kiểm thử của dự án |
| RAM | 8 GB tối thiểu; 16 GB trở lên được khuyến nghị |
| Ổ đĩa trống | Tối thiểu 12 GB; 20 GB trở lên nếu giữ `trainModel`, cache và Playwright Chromium |
| Internet | Cần cho Supabase và các API cloud |
| Âm thanh | Microphone và loa/tai nghe hoạt động |
| Trình duyệt | Google Chrome |

Dung lượng tham khảo trên máy phát triển hiện tại:

| Thành phần | Dung lượng gần đúng |
|---|---:|
| Python `.venv` | 1.5 GB |
| Ollama `gemma3:4b` Q4 | 3.3 GB |
| `friday/trainModel` local | 1.4 GB |
| Video và asset giao diện | 100 MB trở lên |
| Playwright Chromium tùy chọn | Vài trăm MB |

GPU không bắt buộc. Ollama có thể chạy bằng CPU nhưng phản hồi vision sẽ chậm hơn. NVIDIA/AMD GPU tương thích sẽ cải thiện tốc độ.

## Những phần mềm phải cài

### 1. Git

Git chỉ bắt buộc nếu lấy source từ GitHub. Nếu chuyển nguyên thư mục bằng ổ cứng thì có thể bỏ qua.

```powershell
winget install --id Git.Git -e --source winget
```

Đóng và mở lại PowerShell rồi kiểm tra:

```powershell
git --version
```

Tài liệu chính thức: [Git for Windows](https://git-scm.com/install/windows.html).

### 2. uv

`uv` quản lý Python 3.11, virtual environment và toàn bộ dependency Python của dự án. Không cần tự cài Python riêng nếu dùng `uv`.

Cài bằng WinGet:

```powershell
winget install --id astral-sh.uv -e
```

Hoặc dùng installer chính thức:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Mở PowerShell mới rồi kiểm tra:

```powershell
uv --version
```

Tài liệu chính thức: [Installing uv](https://docs.astral.sh/uv/getting-started/installation/).

### 3. Google Chrome

Chrome được dùng cho visible browser search, YouTube, TikTok, Binance, Messenger và các lệnh mở tab.

```powershell
winget install --id Google.Chrome -e --source winget
```

Hoặc cài từ [Google Chrome Help](https://support.google.com/chrome/answer/95346).

Sau khi cài, mở Chrome ít nhất một lần và hoàn thành đăng nhập các nền tảng cần dùng.

### 4. Ollama

Cài Ollama bằng installer Windows từ [Ollama for Windows](https://docs.ollama.com/windows).

Có thể thử cài bằng WinGet:

```powershell
winget install --id Ollama.Ollama -e
```

Mở PowerShell mới rồi kiểm tra:

```powershell
ollama --version
```

Tải model vision của FRIDAY:

```powershell
ollama pull gemma3:4b
```

Kiểm tra metadata:

```powershell
ollama list
ollama show gemma3:4b
```

Model hiện dùng khoảng 3.3 GB trên ổ đĩa và được cấu hình tại `http://127.0.0.1:11434`.

### 5. Microsoft Visual C++ Redistributable

Phần lớn máy Windows 10/11 đã có runtime này. Nếu PySide6, OpenCV, MediaPipe hoặc ONNX báo thiếu DLL, cài bản **Microsoft Visual C++ 2015-2022 Redistributable x64** từ Microsoft rồi khởi động lại máy.

### Không bắt buộc cài riêng

- Python: `uv` sẽ cài Python 3.11.
- PostgreSQL local: dự án dùng Supabase PostgreSQL.
- Node.js: chỉ cần cho Grapuco CLI.
- Docker Desktop: không cần cho native desktop UI.
- FFmpeg system: Qt Multimedia đã mang backend cần thiết qua wheel PySide6.

## Dữ liệu phải sao lưu từ máy cũ

### GitHub không chứa toàn bộ trạng thái local

Những mục sau đang bị `.gitignore` bỏ qua hoặc chứa secret. Clone GitHub trên máy mới sẽ không tự có chúng:

| Mục | Có cần chuyển không? | Ghi chú |
|---|---|---|
| `friday-tony-stark-demo/.env` | Bắt buộc | API key, database URL và runtime settings |
| `friday-tony-stark-demo/friday/app/.env` | Nên chuyển | URL mạng xã hội và Binance |
| `friday-tony-stark-demo/friday/assets/` | Bắt buộc để đủ giao diện | Video `FRIDAY.mp4`, icon, ảnh và asset local |
| `friday-tony-stark-demo/friday/prompts/` | Nên chuyển | Prompt local của dự án |
| `friday-tony-stark-demo/friday/docs/` | Tùy nhu cầu | Tài liệu và câu lệnh mẫu |
| `friday-tony-stark-demo/friday/trainModel/` | Tùy nhu cầu | Kho dữ liệu/skill local, khoảng 1.4 GB |
| Google service-account JSON | Chỉ khi dùng Google Cloud STT/TTS | Không commit file JSON này |
| `friday/log/saveLog/` | Tùy nhu cầu | Lịch sử local |
| Browser/Code Map profiles | Không khuyến nghị chuyển | Cookie có thể gắn với Windows account cũ; nên đăng nhập lại |

### Không sao chép các mục có thể tạo lại

- `.venv/`
- `.uv-cache/`
- `.uv-python/`
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `friday-api.out.log`
- `friday-api.err.log`
- `friday/log/runtime/`

Virtual environment của máy cũ có đường dẫn tuyệt đối và binary phụ thuộc máy. Luôn tạo `.venv` mới bằng `uv sync`.

### Cách chuyển secret an toàn

Không gửi `.env`, service-role key hoặc service-account JSON qua GitHub, chat công khai hay email không mã hóa. Dùng một trong các cách:

- Password manager có secure file.
- USB/ổ cứng mã hóa.
- File archive được mã hóa bằng mật khẩu mạnh.
- Tạo API key mới trên máy mới rồi thu hồi key cũ.

Supabase database nằm trên cloud nên dữ liệu và core password hash vẫn còn nếu máy mới dùng lại cùng project và `DATABASE_URL`.

## Cài đặt trên máy mới

### Bước 1. Lấy source

```powershell
Set-Location C:\
New-Item -ItemType Directory -Force C:\AI | Out-Null
Set-Location C:\AI
git clone https://github.com/Dinh-Huu-Phuc/FRIDAY.git
Set-Location C:\AI\FRIDAY\friday-tony-stark-demo
```

Không bắt buộc dùng `C:\AI`. Có thể đặt dự án ở ổ khác, nhưng nên tránh:

- Thư mục được OneDrive đồng bộ liên tục.
- Đường dẫn quá dài.
- Thư mục yêu cầu quyền Administrator.
- Đường dẫn chứa ký tự lạ nếu công cụ bên thứ ba không hỗ trợ tốt.

### Bước 2. Khôi phục dữ liệu local

Chép các mục đã sao lưu về đúng vị trí:

```text
C:\AI\FRIDAY\friday-tony-stark-demo\.env
C:\AI\FRIDAY\friday-tony-stark-demo\friday\app\.env
C:\AI\FRIDAY\friday-tony-stark-demo\friday\assets\
C:\AI\FRIDAY\friday-tony-stark-demo\friday\prompts\
C:\AI\FRIDAY\friday-tony-stark-demo\friday\docs\
C:\AI\FRIDAY\friday-tony-stark-demo\friday\trainModel\
```

Nếu `.env` cũ chứa đường dẫn tuyệt đối như `G:\...`, sửa thành đường dẫn mới.

Tìm nhanh các đường dẫn Windows cũ:

```powershell
Select-String -Path .env,friday\app\.env -Pattern '[A-Za-z]:\\'
```

### Bước 3. Cài Python 3.11 và dependency

Tại thư mục `friday-tony-stark-demo`:

```powershell
uv python install 3.11
uv sync --frozen
```

`uv sync --frozen` đọc `uv.lock`, tạo `.venv` mới và cài đúng dependency đã khóa, gồm FastAPI, PySide6, SQLAlchemy, Psycopg 3, LiveKit, OpenCV, MediaPipe và Playwright.

Kiểm tra Python:

```powershell
uv run python --version
```

Kết quả phải là Python `3.11.x`.

Kiểm tra import quan trọng:

```powershell
uv run python -c "import fastapi, sqlalchemy, psycopg, cv2, mediapipe, playwright, PySide6; print('Core imports: OK')"
```

Nếu ổ chứa cache và project khác filesystem, `uv` có thể cảnh báo không hardlink được. Đây không phải lỗi. Có thể dùng:

```powershell
$env:UV_LINK_MODE="copy"
uv sync --frozen
```

Nếu cache mặc định bị từ chối truy cập:

```powershell
$env:UV_CACHE_DIR=(Resolve-Path ..\..\.uv-cache)
uv sync --frozen
```

## Cấu hình biến môi trường

### Cách được khuyến nghị khi chuyển cùng một dự án

Khôi phục `.env` riêng tư từ máy cũ, sau đó cập nhật:

- Các đường dẫn tuyệt đối.
- API key đã hết hạn.
- Supabase connection string nếu đổi project.
- Google service-account path.
- Chrome/profile path.

### Cách tạo cấu hình mới

`.env.example` là danh sách tên biến, nhưng nhiều giá trị đang để trống. Không nên chạy ứng dụng với toàn bộ biến số bị để trống vì các trường `int`/`float` như port, timeout hoặc microphone threshold cần giá trị hợp lệ.

Tạo `.env` mới:

```powershell
New-Item -ItemType File .env
notepad .env
```

Baseline cho native desktop app:

```dotenv
# FastAPI and native desktop UI
FRIDAY_API_HOST=127.0.0.1
FRIDAY_API_PORT=8001
FRIDAY_LOCAL_ONLY=true
FRIDAY_EXPOSE_API_DOCS=true
FRIDAY_DESKTOP_UI_ENABLED=true
FRIDAY_DESKTOP_STARTUP_BRIEFING=false
FRIDAY_AUTO_OPEN_BROWSER=false
FRIDAY_ACCESS_LOG=false
FRIDAY_VERBOSE_PROVIDER_LOGS=false

# Database: replace every placeholder
DATABASE_URL="postgresql+psycopg://postgres.PROJECT_REF:PERCENT_ENCODED_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require&application_name=FRIDAY"

# Desktop chat and speech
OPENAI_API_KEY=
FRIDAY_AGENT_MODEL=gpt-4o-mini
FRIDAY_STT_MODEL=gpt-4o-mini-transcribe
FRIDAY_STT_TIMEOUT=45
PAGECLIENT_TTS_PROVIDER=openai
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=nova
PAGECLIENT_TTS_SPEED=1.15

# Optional STT correction
STT_REFINER_ENABLED=true
STT_REFINER_PROVIDER=groq
STT_REFINER_TIMEOUT=4.0
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant

# Live Search and current information
GOOGLE_API_KEY=
GOOGLE_SEARCH_MODEL=gemini-2.5-flash
WEATHERMAP_API_KEY=
NEWSDATA_API_KEY=
WORLD_NEWS=
NEWS_DEFAULT_LANGUAGE=en
NEWS_DEFAULT_COUNTRY=vn
NEWS_DEFAULT_LIMIT=6
NEWS_REQUEST_TIMEOUT=8.0

# Local Ollama vision
FRIDAY_VISION_MODEL=gemma3:4b
FRIDAY_VISION_BASE_URL=http://127.0.0.1:11434
FRIDAY_OLLAMA_PRELOAD=true
FRIDAY_BACKGROUND_WARMUP=true

# Power and sleep display
FRIDAY_INITIAL_STATE=active
FRIDAY_LOCAL_WAKE_WORD=true
FRIDAY_AUTO_SLEEP_ENABLED=true
FRIDAY_AUTO_SLEEP_MINUTES=5
FRIDAY_AUTO_SLEEP_POLL_SECONDS=5
FRIDAY_WINDOW_SLEEP_ENABLED=true
FRIDAY_WINDOW_RESTORE_ON_STARTUP=true
FRIDAY_WINDOW_TRANSITION_DELAY_MS=140
FRIDAY_SLEEP_DISPLAY_ENABLED=true
FRIDAY_SLEEP_DISPLAY_STARTUP_TIMEOUT=4
FRIDAY_SLEEP_WEATHER_REFRESH_MINUTES=10
FRIDAY_SLEEP_BRIGHTNESS_ENABLED=true
FRIDAY_SLEEP_BRIGHTNESS=30
FRIDAY_WAKE_BRIGHTNESS=100
FRIDAY_SLEEP_VIDEO_BACKGROUND_ENABLED=false

# Hands-free microphone
FRIDAY_DESKTOP_MIC_RMS_THRESHOLD=250
FRIDAY_DESKTOP_MIC_MIN_VOICE_MS=240
FRIDAY_DESKTOP_SLEEP_MIC_RMS_THRESHOLD=500
FRIDAY_DESKTOP_SLEEP_MIC_MIN_VOICE_MS=500
FRIDAY_DESKTOP_MIC_SILENCE_MS=850
FRIDAY_DESKTOP_MIC_MAX_UTTERANCE_MS=15000

# Visible Chrome automation
FRIDAY_BROWSER_TYPE_INTERVAL=0.035
FRIDAY_BROWSER_STEP_DELAY=0.2
FRIDAY_BROWSER_PAGE_DELAY=1.2
FRIDAY_PLATFORM_LOAD_DELAY=4.0
FRIDAY_PLATFORM_RESULT_DELAY=3.0
FRIDAY_BROWSER_HTTP_TIMEOUT=8
FRIDAY_LIVE_SEARCH_MAX_SOURCES=3

# Code Map
FRIDAY_CODE_MAP_ENABLED=true
FRIDAY_CODE_MAP_URL=https://grapuco.com/dashboard
FRIDAY_CODE_MAP_PROFILE_PATH=friday/log/runtime/code_map_profile
FRIDAY_CODE_MAP_JS_CONSOLE=false

# Screenshot archive is off until Supabase Storage is configured
FRIDAY_SCREENSHOT_CLOUD_ENABLED=false
SUPABASE_SCREENSHOT_BUCKET=friday-screen-captures
```

### API key theo tính năng

| Biến | Khi nào cần |
|---|---|
| `OPENAI_API_KEY` | Desktop chat, desktop STT và OpenAI TTS mặc định |
| `GOOGLE_API_KEY` | Google Live Search và Gemini cho LiveKit voice agent |
| `GROQ_API_KEY` | STT refiner khi `STT_REFINER_ENABLED=true` |
| `SARVAM_API_KEY` | Sarvam STT/TTS cho LiveKit hoặc khi chọn Sarvam cho desktop TTS |
| `DEEPGRAM_API_KEY` | Chỉ khi chọn Deepgram |
| `WEATHERMAP_API_KEY` | Weather, startup briefing và sleep weather panel |
| `NEWSDATA_API_KEY` | NewsData feed |
| `WORLD_NEWS` | NewsAPI world news feed |
| `LIVEKIT_URL` | Chỉ khi chạy `friday_voice` |
| `LIVEKIT_API_KEY` | Chỉ khi chạy `friday_voice` |
| `LIVEKIT_API_SECRET` | Chỉ khi chạy `friday_voice` |
| `SUPABASE_URL` | Screenshot Storage API |
| `SUPABASE_SERVICE_ROLE_KEY` | Upload screenshot lên private bucket; tuyệt đối không đưa ra frontend |

Nếu không có Groq key, tắt refiner để tránh lỗi chờ timeout:

```dotenv
STT_REFINER_ENABLED=false
```

### Google Cloud service-account tùy chọn

`GOOGLE_API_KEY` và `GOOGLE_APPLICATION_CREDENTIALS` là hai loại credential khác nhau.

- `GOOGLE_API_KEY`: Gemini/Google GenAI.
- `GOOGLE_APPLICATION_CREDENTIALS`: đường dẫn tới service-account JSON cho Google Cloud STT/TTS.

Ví dụ:

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=C:\FRIDAY-secrets\google-service-account.json
GOOGLE_STT_LANGUAGE=en-US
GOOGLE_TTS_LANGUAGE=en-US
GOOGLE_TTS_VOICE_NAME=en-US-Wavenet-F
```

Không commit file JSON.

### URL mạng xã hội và Binance

Tạo file:

```powershell
New-Item -ItemType File friday\app\.env
notepad friday\app\.env
```

Ví dụ:

```dotenv
FACEBOOK_URL=https://www.facebook.com/
YOUTUBE_URL=https://www.youtube.com/
INSTAGRAM_URL=https://www.instagram.com/
TIKTOK_URL=https://www.tiktok.com/
X_URL=https://x.com/
TWITTER_URL=https://x.com/
LINKEDIN_URL=https://www.linkedin.com/
PINTEREST_URL=https://www.pinterest.com/
REDDIT_URL=https://www.reddit.com/
TELEGRAM_URL=https://web.telegram.org/
DISCORD_URL=https://discord.com/app

# Copy the exact overview URL from the old private config.
BINANCE_URL_VI_MARKET_OVERVIEW=
BINANCE_URL=https://www.binance.com/vi/trade/BTC_USDT?_from=markets
```

## Kết nối Supabase và chạy migration

### 1. Chọn connection string

Trong Supabase Dashboard:

1. Mở project.
2. Chọn **Connect**.
3. Chọn **Session pooler** nếu mạng máy mới là IPv4 thông thường.
4. Dùng port `5432`.
5. Sao chép connection string.

Supabase mô tả Session pooler là lựa chọn phù hợp cho backend chạy lâu trên mạng IPv4: [Connect to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres).

### 2. Percent-encode mật khẩu

Nếu password chứa `@`, `&`, `/`, `!`, `%`, `#` hoặc ký tự đặc biệt khác, chỉ encode phần password.

Lệnh an toàn, không ghi password vào shell history:

```powershell
uv run python -c "import getpass; from urllib.parse import quote; print(quote(getpass.getpass('Supabase DB password: '), safe=''))"
```

Đưa kết quả encode vào `DATABASE_URL`:

```dotenv
DATABASE_URL="postgresql+psycopg://postgres.PROJECT_REF:PERCENT_ENCODED_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require&application_name=FRIDAY"
```

Không encode toàn bộ URL. Không giữ dấu `[` `]` hoặc placeholder trong URL thật.

### 3. Kiểm tra database

```powershell
uv run python -c "from sqlalchemy import text; from friday.src.db.database import get_engine; engine=get_engine(); c=engine.connect(); print(c.execute(text('select current_database(), current_user')).one()); c.close()"
```

Kết quả mong đợi:

```text
('postgres', 'postgres')
```

### 4. Tạo hoặc cập nhật bảng

```powershell
uv run alembic upgrade head
```

Kiểm tra revision:

```powershell
uv run alembic current
uv run alembic heads
```

Hai lệnh phải chỉ về revision head mới nhất của thư mục `migrations/versions`.

### 5. Core password

- Nếu dùng lại Supabase project cũ, hash password vẫn còn. Máy mới sẽ yêu cầu password cũ.
- Nếu dùng Supabase project mới, lần đầu mở FRIDAY sẽ yêu cầu tạo password và nhập lại để xác nhận.
- Password dài từ 8 đến 128 ký tự.
- FRIDAY không lưu plaintext password và không có luồng lấy lại password trong UI.
- Lưu password trong password manager trước khi xác nhận.
- Sau khi unlock, không cần nhập lại cho tới khi process `friday-api` tắt hẳn.

### 6. Screenshot cloud tùy chọn

Trong Supabase Dashboard:

1. Mở **Storage**.
2. Tạo private bucket tên `friday-screen-captures`.
3. Lấy Project URL và `service_role` key ở API settings.
4. Thêm:

```dotenv
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_SCREENSHOT_BUCKET=friday-screen-captures
FRIDAY_SCREENSHOT_CLOUD_ENABLED=true
```

`service_role` key có quyền cao và chỉ được dùng ở backend local. Không đưa key này vào browser JavaScript, ảnh chụp, tài liệu hoặc Git.

Supabase cho phép tạo bucket từ Dashboard: [Storage Quickstart](https://supabase.com/docs/guides/storage/quickstart).

## Cấu hình microphone, loa và Chrome

### Microphone

1. Mở **Settings > Privacy & security > Microphone**.
2. Bật **Microphone access**.
3. Bật **Let desktop apps access your microphone**.
4. Mở **Settings > System > Sound > Input** và chọn đúng microphone mặc định.
5. Nói thử và xem input level của Windows có chuyển động.

FRIDAY dùng Qt Multimedia trực tiếp, không cần cài PyAudio.

Khi chạy app:

- Trạng thái phải chuyển thành `MIC LISTENING`.
- Waveform phải chuyển động khi nói.
- Microphone tự tạm dừng khi FRIDAY đang suy nghĩ hoặc đang đọc câu trả lời.
- Trong sleep mode, threshold cao hơn để tránh tự thức vì tiếng ồn.

Nếu waveform quá yếu:

```dotenv
FRIDAY_DESKTOP_MIC_RMS_THRESHOLD=180
FRIDAY_DESKTOP_SLEEP_MIC_RMS_THRESHOLD=400
```

Nếu FRIDAY tự nhận tiếng ồn:

```dotenv
FRIDAY_DESKTOP_MIC_RMS_THRESHOLD=350
FRIDAY_DESKTOP_SLEEP_MIC_RMS_THRESHOLD=650
```

### Loa

Chọn output mặc định tại **Settings > System > Sound > Output**. Desktop voice reply phát PCM WAV qua `QAudioSink`.

### Chrome automation

- Chrome và FRIDAY phải chạy cùng mức quyền. Không chạy một ứng dụng bằng Administrator trong khi ứng dụng kia chạy thường.
- Visible automation cần desktop đang mở khóa.
- Không gõ phím hoặc đổi cửa sổ trong lúc FRIDAY đang tự thao tác Chrome.
- Đăng nhập YouTube, TikTok, Binance, Facebook và các nền tảng bằng chính Chrome trên máy mới.
- Có thể đặt đường dẫn Chrome thủ công:

```dotenv
FRIDAY_BROWSER_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

## Khởi động FRIDAY

### Native desktop app

```powershell
Set-Location C:\AI\FRIDAY\friday-tony-stark-demo
uv run friday-api
```

Luồng khởi động:

1. FastAPI chạy tại `127.0.0.1:8001`.
2. Ollama được preload ở background nếu bật.
3. Unlock dialog xuất hiện.
4. Sau khi password đúng, native desktop window mở.
5. Microphone hands-free tự khởi động.

Đóng cửa sổ desktop sẽ yêu cầu FastAPI server trong process đó dừng theo.

### Compatibility web UI

Tắt native UI:

```dotenv
FRIDAY_DESKTOP_UI_ENABLED=false
FRIDAY_AUTO_OPEN_BROWSER=true
```

Chạy:

```powershell
uv run friday-api
```

Mở:

```text
http://127.0.0.1:8001/ui
```

### Swagger

Đảm bảo:

```dotenv
FRIDAY_EXPOSE_API_DOCS=true
```

Mở:
>>>>>>> 31c599a (update)

```text
http://127.0.0.1:8001/docs
```

<<<<<<< HEAD
Set `FRIDAY_DESKTOP_UI_ENABLED=false` to use the compatibility browser UI as the launcher again. Set `FRIDAY_DESKTOP_STARTUP_BRIEFING=true` only when you want the slower live weather/news briefing at desktop startup.

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
=======
### LiveKit voice agent đầy đủ

Thêm vào `.env`:

```dotenv
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

STT_PROVIDER=sarvam
LLM_PROVIDER=gemini
TTS_PROVIDER=sarvam
SARVAM_API_KEY=
GOOGLE_API_KEY=
```

Chạy ba terminal:

```powershell
# Terminal 1: MCP/SSE
uv run friday
```

```powershell
# Terminal 2: LiveKit agent
uv run friday_voice
```

```powershell
# Terminal 3: Native UI/FastAPI
uv run friday-api
```

MCP endpoint:

```text
http://127.0.0.1:8000/sse
```

## Kiểm tra sau cài đặt

### 1. Kiểm tra dependency

```powershell
uv run python -c "import fastapi, sqlalchemy, psycopg, cv2, mediapipe, playwright, PySide6; print('Dependencies: OK')"
```

### 2. Kiểm tra Ollama

```powershell
ollama show gemma3:4b
```

Test API:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

### 3. Kiểm tra Supabase

```powershell
uv run python -c "from sqlalchemy import text; from friday.src.db.database import get_engine; c=get_engine().connect(); print(c.execute(text('select current_database(), current_user')).one()); c.close()"
```

### 4. Kiểm tra migration

```powershell
uv run alembic current
uv run alembic heads
```

### 5. Kiểm tra FastAPI

Trong khi `uv run friday-api` đang chạy:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health/live
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health/ready
```

Kết quả phải có `ok: true`.

### 6. Chạy test local

`pytest` hiện là công cụ kiểm thử dành cho developer và không nằm trong runtime dependency. Dùng `--with pytest` để tạo môi trường chạy tạm mà không sửa `pyproject.toml`:

```powershell
uv run --with pytest pytest -q
```

### 7. Checklist chức năng

- Unlock được bằng core password.
- Desktop UI mở và không bị màn hình đen.
- `FRIDAY.mp4` tồn tại nếu chọn giao diện video.
- Mic waveform phản ứng với giọng nói.
- FRIDAY nhận lệnh text.
- FRIDAY nhận lệnh giọng nói.
- Voice reply đọc hết câu.
- `FRIDAY sleep` phủ đủ mọi màn hình.
- `FRIDAY wake up` đóng mọi sleep overlay.
- `FRIDAY open Neural network` mở visual neural.
- `FRIDAY close Neural network` đóng visual neural.
- YouTube/TikTok/Binance mở trong Chrome.
- Live Search trả lời và đính kèm nguồn.
- Code Map mở và đóng đúng lệnh.

## Tính năng và công cụ tùy chọn

### Playwright Chromium

Default Messenger mode dùng Chrome profile và thường không cần tải Chromium riêng. Chỉ cài browser binary khi dùng:

```dotenv
FRIDAY_MESSENGER_MODE=playwright
```

Lệnh cài:

```powershell
uv run playwright install chromium
```

Playwright yêu cầu browser binary khớp với version package: [Playwright Browsers](https://playwright.dev/python/docs/browsers).

### Grapuco Code Map

Grapuco CLI cần Node.js:

```powershell
winget install --id OpenJS.NodeJS.LTS -e
```

Mở PowerShell mới:

```powershell
npm.cmd install -g @bitsness/grapuco-cli
grapuco.cmd --version
```

Tại project:

```powershell
grapuco.cmd login
grapuco.cmd init --name FRIDAY
grapuco.cmd ingest
```

Sau đó nói:

```text
FRIDAY open code map
FRIDAY close code map
```

Nếu đã ingest repository cũ, có thể chỉ cần đăng nhập lại và mở repository trên dashboard.

### CodeGraph cho Codex

CodeGraph không cần cho FRIDAY runtime. Nó chỉ hỗ trợ Codex hiểu source nhanh hơn.

Cài standalone trên Windows:

```powershell
irm https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.ps1 | iex
```

Mở terminal mới:

```powershell
codegraph install
Set-Location C:\AI\FRIDAY\friday-tony-stark-demo
codegraph init
```

Kiểm tra:

```powershell
codegraph explore "FRIDAY startup flow"
```

`.codegraph/` là index local và có thể tạo lại, không cần sao lưu.

### Chrome extension cho Messenger bridge

Xem hướng dẫn tại:

```text
friday-tony-stark-demo/friday/browser_extension/facebook_messenger/README.md
```

Khi load unpacked extension, chỉ cấp quyền cho extension do chính bạn kiểm tra source.

### Docker

Docker Compose trong repository phù hợp hơn với API/MCP headless. Native PySide6 UI, microphone, multi-monitor sleep overlay, local Chrome automation và Windows Launcher không phù hợp chạy trong Linux container.

Nếu chạy API bằng Docker:

```dotenv
FRIDAY_DESKTOP_UI_ENABLED=false
FRIDAY_AUTO_OPEN_BROWSER=false
```

Sau đó:

```powershell
docker compose up --build friday-api friday-mcp
```

Để trải nghiệm đầy đủ trên Windows, dùng `uv run friday-api` trực tiếp.

## Xử lý lỗi thường gặp

### `uv` không được nhận diện

Đóng PowerShell, mở lại rồi chạy:

```powershell
uv --version
```

Nếu vẫn lỗi, chạy lại installer uv hoặc kiểm tra `%USERPROFILE%\.local\bin` trong `PATH`.

### `Failed to initialize cache` hoặc `Access is denied`

```powershell
$env:UV_CACHE_DIR="C:\AI\FRIDAY\.uv-cache"
$env:UV_LINK_MODE="copy"
uv sync --frozen
```

### Cảnh báo `Failed to hardlink files`

Đây là cảnh báo hiệu năng, không phải cài đặt thất bại:

```powershell
$env:UV_LINK_MODE="copy"
```

### `PostgreSQL DATABASE_URL is not configured`

Kiểm tra `.env` nằm đúng tại:

```text
friday-tony-stark-demo/.env
```

Không đặt nó ở `FRIDAY/.env`.

### Supabase báo password authentication failed

- Lấy connection string mới từ nút **Connect**.
- Kiểm tra đúng project reference.
- Percent-encode riêng password.
- Dùng Session pooler port `5432` nếu mạng chỉ có IPv4.
- Giữ `sslmode=require`.

### `uv run alembic upgrade head` lỗi import

```powershell
uv sync --frozen
uv run python -c "import friday.src.models; print('Models import: OK')"
uv run alembic upgrade head
```

Đảm bảo đang đứng trong thư mục có `alembic.ini`.

### `/docs` trả 404

```dotenv
FRIDAY_EXPOSE_API_DOCS=true
```

Tắt process rồi chạy lại `uv run friday-api`.

### Swagger trả 200 nhưng màn hình trắng

- Hard refresh bằng `Ctrl+F5`.
- Mở DevTools và kiểm tra asset CDN bị chặn.
- Thử Chrome profile thường, không dùng extension chặn script.
- Kiểm tra `http://127.0.0.1:8001/openapi.json`.

### Desktop video bị đen

Kiểm tra:

```powershell
Test-Path friday\assets\videos\FRIDAY.mp4
```

Nếu `False`, phục hồi toàn bộ `friday/assets/` từ backup local.

### Microphone có icon nhưng không nhận tiếng

- Kiểm tra Windows microphone privacy.
- Chọn đúng default input.
- Đóng ứng dụng khác đang độc quyền microphone.
- Xem waveform trong FRIDAY.
- Giảm `FRIDAY_DESKTOP_MIC_RMS_THRESHOLD`.
- Tắt rồi mở lại FRIDAY sau khi đổi thiết bị.

### FRIDAY chỉ nghe nhưng không transcribe

Desktop STT cần:

```dotenv
OPENAI_API_KEY=
FRIDAY_STT_MODEL=gpt-4o-mini-transcribe
```

Nếu dùng OpenAI-compatible endpoint khác, endpoint đó phải hỗ trợ `/audio/transcriptions`.

### FRIDAY không đọc voice reply

Kiểm tra:

- Nút **Voice reply** trong Settings đang bật.
- Default output device của Windows.
- API key đúng với `PAGECLIENT_TTS_PROVIDER`.
- Nếu dùng OpenAI: `OPENAI_API_KEY`.
- Nếu dùng Sarvam: `SARVAM_API_KEY`.

### Ollama không kết nối

```powershell
ollama serve
```

Mở terminal khác:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
ollama show gemma3:4b
```

### Chrome mở nhưng automation gõ sai chỗ

- Không chạm chuột/bàn phím trong lúc automation chạy.
- Đưa Chrome lên foreground.
- Không chạy Chrome và FRIDAY ở hai mức quyền khác nhau.
- Tăng `FRIDAY_PLATFORM_LOAD_DELAY` nếu Internet chậm.
- Đặt đúng `FRIDAY_BROWSER_PATH`.

### Code Map mở nhưng không có node

```powershell
grapuco.cmd status
grapuco.cmd ingest
```

Trong Grapuco Dashboard, mở **Repositories**, chọn `FRIDAY`, rồi chọn **Analyze**.

Nếu PowerShell chặn `grapuco.ps1`, dùng `grapuco.cmd` như các lệnh trong README.

### Port 8000 hoặc 8001 đã được dùng

```powershell
Get-NetTCPConnection -LocalPort 8000,8001 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,State,OwningProcess
```

Đóng process cũ hoặc đổi:

```dotenv
FRIDAY_API_PORT=8002
```

Nếu đổi port, cập nhật CORS và URL bridge liên quan.

## Lệnh vận hành nhanh

```powershell
# Native desktop app + FastAPI
uv run friday-api

# MCP/SSE server
uv run friday

# LiveKit voice agent
uv run friday_voice

# Database migrations
uv run alembic upgrade head

# Full local test suite
uv run --with pytest pytest -q

# Ollama model
ollama show gemma3:4b
```

## Tài liệu nội bộ

- [README của source](friday-tony-stark-demo/README.md)
- [Báo cáo model và parameter](friday-tony-stark-demo/md/FRIDAY_model_parameter_report.md)
- [Câu lệnh mẫu](friday-tony-stark-demo/friday/docs/Question/friday_command_questions.md)
- [Messenger extension](friday-tony-stark-demo/friday/browser_extension/facebook_messenger/README.md)

## Bảo mật

- Không commit `.env`.
- Không commit Google service-account JSON.
- Không commit Supabase `service_role` key.
- Không chụp màn hình API key hoặc database URL.
- Không chuyển browser profile qua máy khác nếu không cần thiết.
- Thu hồi key cũ khi nghi ngờ đã lộ.
- Giữ `FRIDAY_LOCAL_ONLY=true` nếu chỉ dùng trên máy cá nhân.
- Không đổi `FRIDAY_API_HOST` thành `0.0.0.0` trừ khi đã cấu hình firewall và authentication phù hợp.

## Liên hệ

Developer: **Dinh Huu Phuc**

- GitHub: [Dinh-Huu-Phuc/FRIDAY](https://github.com/Dinh-Huu-Phuc/FRIDAY)
- Facebook: [A.I.2302](https://www.facebook.com/A.I.2302)
>>>>>>> 31c599a (update)

## License

MIT
<<<<<<< HEAD

=======
>>>>>>> 31c599a (update)
