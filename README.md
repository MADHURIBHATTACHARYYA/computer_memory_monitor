# 🚀 RAMPulse — Real-Time Memory Dashboard & Process Monitor

A modern, high-performance Python web dashboard to monitor your computer's memory in real-time. Instantly see **which memory is occupied, what is free**, and **which programs (and PIDs) are consuming your RAM**.

![RAMPulse Dashboard](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Chart.js](https://img.shields.io/badge/Charts-Chart.js_4.4-FF6384?logo=chartdotjs&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## ✨ Features

- 📊 **Real-Time Memory Telemetry**:
  - **Physical RAM Breakdown**: Total, Occupied/Used, Free, and Available RAM with percentage bars.
  - **Swap / Windows Pagefile**: Total, Used, and Free virtual memory.
  - **Memory Health Analysis**: Real-time pressure grading (*Optimal*, *Moderate*, *High Pressure*, *Critical*) with actionable optimization tips.

- 🔍 **Program & Process-Level Memory Inspection**:
  - **Application Grouping Mode**: Merges multi-process applications (e.g. Chrome, VS Code, Slack, Node) into a single unified row showing total combined memory and instance count.
  - **Flat Individual Process Mode**: View every running process with its individual PID, threads count, and exact memory usage.
  - **Metrics per Process**: Resident Set Size (Physical RAM occupied), Virtual Memory Size (VMS), % of System RAM, CPU %, Status, and User.
  - **Search & Filters**: Instant search by process name, PID, or user; quick filters for `> 500 MB`, `> 100 MB`, `> 50 MB`.
  - **Detailed Process Inspector**: Click any row to inspect its executable path, full launch command line arguments, uptime, and thread count.

- 📈 **Interactive Visual Charts**:
  - **Live Timeline Trend**: Dual-line time-series chart of RAM % and Swap % over time.
  - **RAM Distribution Donut**: Visual proportion of Occupied RAM vs Available RAM.
  - **Top Memory Consumers Bar Chart**: Horizontal bar comparison of the top 8 memory-occupying programs.

- 🛡️ **Safety-Guarded Process Termination**:
  - "End Task" action with confirmation modal displaying the exact memory that will be freed.
  - Built-in OS protection guard preventing accidental termination of critical Windows system processes (e.g., `System`, `csrss.exe`, `lsass.exe`, `services.exe`).

- ⚡ **Bi-Directional WebSocket & Fallback Polling**:
  - Pushes live updates at configurable frequencies (1s Fast, 2s Balanced, 5s Eco).
  - Pause/Resume controls.
  - Automatic graceful fallback to HTTP polling if WebSocket is unavailable.

---

## 🛠️ Project Structure

```
python_memory_dashboard_monitor/
├── .venv/                   # Python virtual environment
├── src/
│   ├── __init__.py
│   ├── monitor.py          # Core psutil memory & process inspection engine
│   ├── app.py              # FastAPI backend REST API & WebSocket endpoints
│   └── static/
│       ├── index.html      # Glassmorphic single-page dashboard UI
│       ├── style.css       # Sleek responsive dark-theme stylesheet
│       └── app.js          # Live frontend controller & Chart.js logic
├── tests/
│   ├── __init__.py
│   ├── test_monitor.py     # Unit tests for monitoring calculations & safety guards
│   └── test_api.py         # Integration tests for FastAPI endpoints
├── requirements.txt         # Pinned Python dependencies
├── run.py                  # One-click CLI & browser launcher
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+ (Python 3.11 recommended)
- Windows 10/11, macOS, or Linux

### 2. Setup Virtual Environment & Dependencies
```powershell
# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Launch the Dashboard
Run the launcher script:
```powershell
python run.py
```

The script will automatically start the server and open your default browser to:
👉 **`http://127.0.0.1:8000`**

#### Command-Line Options:
```powershell
# Run on a custom port
python run.py --port 8080

# Run without automatically launching a browser window
python run.py --no-browser

# Enable hot reload during development
python run.py --reload
```

---

## 📡 API Reference

Interactive Swagger documentation is available at **`http://127.0.0.1:8000/docs`**.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web dashboard single-page interface |
| `GET` | `/api/system` | Real-time RAM and Swap metrics, hardware specs |
| `GET` | `/api/processes` | Filterable, sortable process list (`grouped`, `search`, `min_mb`, `sort_by`) |
| `GET` | `/api/processes/{pid}` | Full metadata, path, command line for a specific process |
| `POST`| `/api/processes/{pid}/kill`| Terminate or kill a process (with safety check) |
| `GET` | `/api/history` | Rolling time-series history of memory usage |
| `GET` | `/api/recommendations`| System memory health score and top memory consumers |
| `WS`  | `/ws/live` | Live WebSocket streaming telemetry |

---

## 🧪 Running Tests

Run the full test suite with Python's built-in `unittest` runner:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

All tests will verify:
- Accurate RAM/Swap calculations and byte unit formatting.
- Process iteration, application grouping, and instance counts.
- Safety protection guards for core Windows kernel processes.
- All FastAPI REST endpoints and status codes.

---

## 🛡️ Security & OS Safety

Critical operating system processes (`System`, `System Idle Process`, `csrss.exe`, `lsass.exe`, `wininit.exe`, `services.exe`, `dwm.exe`, `svchost.exe`) are explicitly marked as protected. The dashboard locks these processes with a 🔒 badge and blocks termination requests both at the UI and backend levels.
