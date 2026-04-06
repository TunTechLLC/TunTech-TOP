# TOP — TunTech Operations Platform

A locally hosted consulting diagnostic tool that automates the OPD (Operational Performance Diagnostic) workflow.

**Stack:** FastAPI (Python) · React/Vite · SQLite · Anthropic Claude API  
**Single user:** Victor Richardson, TunTech LLC

---

## Prerequisites

Install these before anything else.

### Python 3.14
Download the Windows installer from [python.org](https://www.python.org/downloads/).  
During installation, check **"Add Python to PATH"**.

Verify:
```powershell
python --version
# Python 3.14.x
```

### Node.js 24.x
Download the Windows installer from [nodejs.org](https://nodejs.org/).

Verify:
```powershell
node --version   # v24.x.x
npm --version    # 11.x.x
```

### Git
Download from [git-scm.com](https://git-scm.com/). Accept all defaults.

Verify:
```powershell
git --version
```

---

## Get the Code

```powershell
git clone https://github.com/TunTechLLC/TunTech-TOP.git
cd TunTech-TOP
```

---

## Install Dependencies

### Python packages
From the project root:
```powershell
pip install -r requirements.txt
```

### Frontend packages
```powershell
cd frontend
npm install
cd ..
```

---

## Environment Variables

The application reads configuration from Windows environment variables.  
The `.env` file in the project root is a reference only — it is not automatically
loaded by the application. Variables must be set in Windows.

**To set a permanent user environment variable in PowerShell:**
```powershell
[Environment]::SetEnvironmentVariable("VARIABLE_NAME", "value", "User")
```

After setting variables, restart any open terminals and VS Code for them to take effect.

### Required

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key — get one at console.anthropic.com |

```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
```

### Optional (override defaults from config.py)

| Variable | Default | Description |
|----------|---------|-------------|
| `TOP_DB_PATH` | `C:\Users\<you>\OneDrive\100_TunTech\TOP\TOP.db` | SQLite database path |
| `TOP_LOG_PATH` | `C:\Dev\TunTech\TOP\top.log` | Log file path |
| `TOP_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `TOP_MAX_TOKENS` | `8000` | Max tokens per Claude API call |

If your paths match the defaults, you do not need to set these.  
If your paths differ, set them the same way as the API key above.

---

## Database Setup

The database is a SQLite file (`TOP.db`) that contains the schema, the full pattern
library (P01–P60), and all engagement data. **It is not included in the repository.**
Choose the path that matches your setup.

---

### Option A — OneDrive (recommended)

If OneDrive is installed and signed in on the new machine, the database syncs automatically.

1. Sign in to OneDrive and wait for the sync to complete.
2. Confirm the file exists at:
   ```
   C:\Users\<you>\OneDrive\100_TunTech\TOP\TOP.db
   ```
3. If your Windows username differs from the source machine, set `TOP_DB_PATH`:
   ```powershell
   [Environment]::SetEnvironmentVariable("TOP_DB_PATH", "C:\Users\<newusername>\OneDrive\100_TunTech\TOP\TOP.db", "User")
   ```

That's it. The database is ready.

---

### Option B — No OneDrive

Copy the database file manually from the source machine.

1. On the **source machine**, locate `TOP.db`:
   ```
   C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db
   ```

2. Copy it to the new machine. Choose a permanent location — for example:
   ```
   C:\TunTech\TOP\TOP.db
   ```
   Create the folder first if it does not exist.

3. Set `TOP_DB_PATH` to point to the copied file:
   ```powershell
   [Environment]::SetEnvironmentVariable("TOP_DB_PATH", "C:\TunTech\TOP\TOP.db", "User")
   ```

4. Also copy the **reports folder** if you want existing generated reports available:
   ```
   C:\Users\varic\OneDrive\100_TunTech\TOP\reports\
   ```
   The reports folder path is set per-engagement inside the app — update it in
   engagement settings after the move if the path changes.

> **Important:** There is no script to recreate the database from scratch. The database
> contains the full pattern library (P01–P60) which is required for the diagnostic
> workflow. Always copy an existing `TOP.db` — do not create an empty SQLite file.

---

## Engagement File Folders

Each engagement stores interview transcripts and client documents in folders on the
local machine. These folder paths are set per-engagement inside the app (Engagement
Settings tab) and are stored in the database.

If folder paths change on the new machine (e.g. different drive letter or username),
update them in the app after setup. The files themselves are not in the repository.

---

## Start the Application

### Option A — VS Code (recommended)

Open the project in VS Code. Press **Ctrl+Shift+B** to run the default build task.  
This starts both the backend and frontend in parallel in dedicated terminal panels.

Tasks are defined in `.vscode/tasks.json`.

### Option B — Manual (two terminals)

**Terminal 1 — Backend** (from project root):
```powershell
uvicorn api.main:app --port 8000 --reload
```

**Terminal 2 — Frontend** (from project root):
```powershell
cd frontend
npm run dev
```

### Access the app
Open a browser and go to: **http://localhost:5173**

The backend API runs at: **http://localhost:8000**

---

## Run Tests

From the project root:
```powershell
pytest tests/ -v
```

Tests use a temporary database and do not touch `TOP.db`.

---

## Verify the Setup

After starting the app, confirm the following before doing any engagement work:

1. The dashboard loads at http://localhost:5173 with no errors
2. Existing engagements appear (if the database was copied correctly)
3. The backend terminal shows no startup errors
4. Create a test engagement and confirm it saves — this verifies the database is writable

---

## File Reference

```
TunTech-TOP/
├── api/                    # FastAPI backend
│   ├── db/repositories/    # All SQL (never put SQL anywhere else)
│   ├── models/             # Pydantic models
│   ├── routers/            # HTTP endpoints (thin wrappers only)
│   ├── services/           # Business logic, Claude API calls, report generation
│   └── utils/              # ID generation, domain lists, formatting
├── frontend/               # React/Vite frontend
│   └── src/
│       ├── api.js          # All API calls go through here
│       ├── constants.js    # Domain lists, confidence levels (keep in sync with domains.py)
│       └── components/     # One component per panel
├── tests/                  # pytest test suite
├── config.py               # Single source of truth for env-variable-backed config
├── .env                    # Reference only — not loaded automatically (gitignored)
├── .vscode/tasks.json      # VS Code start tasks
└── requirements.txt        # Python dependencies
```

---

## Troubleshooting

**"No module named 'api'"**  
Run uvicorn from the project root, not from inside the `api/` folder.

**"ANTHROPIC_API_KEY not set" or Claude calls failing**  
Confirm the variable is set and the terminal was restarted after setting it:
```powershell
echo $env:ANTHROPIC_API_KEY
```

**"No new files found to process"**  
Confirm the engagement's interviews/documents folder paths are set correctly in
Engagement Settings. Files do not need to be prefixed with the engagement ID.

**Database errors on startup**  
Confirm `TOP_DB_PATH` points to a valid `TOP.db` file and the path exists.
Check that the folder containing the DB is writable.

**Frontend loads but API calls fail**  
Confirm the backend is running on port 8000. Check the backend terminal for errors.
