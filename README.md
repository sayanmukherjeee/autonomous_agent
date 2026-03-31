# 🤖 Autonomous Code Agent (Free LLM Edition)

An autonomous software-engineering agent that reads/writes files, runs terminal commands, and interacts with GitHub — all with **human approval** before any destructive action. Uses **Ollama + gemma3:4b** (local, free) or **Google Gemini** (free API tier) as the LLM backend.

---

## 📁 Project Structure

```
autonomous_agent/
├── .env                    ← your secrets (API keys, paths) — EDIT THIS
├── config.yaml             ← defaults / safety settings
├── requirements.txt
├── run_cli.py              ← ▶ start the CLI
├── run_api.py              ← ▶ start the REST API server
│
├── config/
│   └── settings.py         ← loads .env + config.yaml into a Settings object
│
├── agent/
│   ├── state.py            ← AgentState TypedDict
│   ├── prompts.py          ← system prompt
│   ├── llm_factory.py      ← returns ChatOllama or ChatGoogleGenerativeAI
│   ├── nodes.py            ← agent_node, tools_node, human_approval_node
│   └── graph.py            ← LangGraph StateGraph wiring
│
├── tools/
│   ├── file_tools.py       ← read_file, write_file, list_directory, search_files
│   ├── terminal_tools.py   ← run_command (whitelist-restricted)
│   └── github_tools.py     ← create_branch, commit_and_push, create_pr, get_issue
│
├── api/
│   ├── main.py             ← FastAPI app
│   ├── models.py           ← Pydantic request/response schemas
│   └── session_manager.py  ← in-memory session store
│
├── cli/
│   └── console.py          ← interactive CLI loop
│
├── sample_repo/
│   ├── calculator.py       ← buggy file for demo
│   └── test_calculator.py  ← pytest tests
│
└── tests/                  ← unit tests for tools + graph
```

---

## ⚙️ Setup Guide (Windows 10 + Python 3.11)

### Step 1 — Open the project in VS Code

1. Extract the zip file to any folder, e.g. `C:\Projects\autonomous_agent`
2. Open VS Code → **File → Open Folder** → select `autonomous_agent`
3. Open the integrated terminal: **Terminal → New Terminal** (this opens PowerShell)

### Step 2 — Create a virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

This takes 1–3 minutes. All packages are free.

### Step 4 — Configure `.env`

Open `.env` in VS Code and set:

```env
# ── Choose your LLM ──────────────────────────
LLM_PROVIDER=ollama          # you already have gemma3:4b installed ✅

# ── Ollama (already installed on your machine) ──
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b

# ── Point to a repo you want the agent to work on ──
# Use the sample_repo inside this project to start:
REPO_PATH=./sample_repo

# ── GitHub token (only needed for branch/PR features) ──
# Leave as-is if you just want to test file/terminal tools
GITHUB_TOKEN=your_personal_access_token_here
```

> **Gemini instead of Ollama?**  
> Change `LLM_PROVIDER=gemini`, then add your `GEMINI_API_KEY` from  
> https://aistudio.google.com/app/apikey (free, no credit card needed).

### Step 5 — Make sure Ollama is running

Open a **separate** PowerShell window and run:

```powershell
ollama serve
```

Keep this window open while using the agent. If Ollama is already running as a background service, you can skip this.

---

## 🚀 Running the Agent

### Option A — Interactive CLI (recommended to start)

```powershell
# Make sure venv is activated and ollama is running
python run_cli.py
```

You'll see:

```
╔══════════════════════════════════════════════╗
║    Autonomous Code Agent  (free LLM edition) ║
╚══════════════════════════════════════════════╝
LLM provider : ollama  (gemma3:4b)
Repo path    : C:\Projects\autonomous_agent\sample_repo
```

#### Demo task — fix the division-by-zero bug

```
You: Fix the division-by-zero bug in calculator.py
```

The agent will:
1. Read `calculator.py` automatically (no approval needed for reads)
2. Propose a fix
3. Pause and ask:
   ```
   ⚠️  APPROVAL REQUIRED
       Tool  : write_file
       Args  :
         path: calculator.py
         content: ...
   Approve? [y/n]:
   ```
4. Type `y` → file is written
5. Optionally run `pytest test_calculator.py`

#### CLI commands

| Command | Description |
|---|---|
| `/status` | Show LLM provider, repo path, GitHub token status |
| `/repo C:/path/to/repo` | Switch to a different repository |
| `/help` | Show all commands |
| `/exit` | Quit |

---

### Option B — REST API + Postman

```powershell
python run_api.py
```

Open `http://localhost:8000/docs` in your browser — you get a full Swagger UI.

#### Quick Postman workflow

1. **Start a task**
   ```
   POST http://localhost:8000/run
   Body (JSON): { "query": "List all Python files in the repo" }
   ```
   → Returns `{ "session_id": "abc-123", "status": "running" }`

2. **Poll for status**
   ```
   GET http://localhost:8000/status/abc-123
   ```
   → When a tool needs approval, `status` becomes `"waiting_approval"` and you see `pending_tool` + `pending_args`

3. **Approve or reject**
   ```
   POST http://localhost:8000/approve/abc-123
   Body (JSON): { "approved": true }
   ```

4. **Keep polling** until `status == "finished"`

---

## 🧪 Running Tests

```powershell
python -m pytest tests/ -v
```

Tests do **not** need Ollama or a GitHub token — they mock the LLM and use temp directories.

---

## 🔧 Tools the Agent Can Use

| Tool | Approval? | Description |
|---|---|---|
| `read_file` | ✅ No | Read any file inside the repo |
| `list_directory` | ✅ No | List files/folders |
| `search_files` | ✅ No | Glob search (e.g. `**/*.py`) |
| `write_file` | ⚠️ Yes | Write/overwrite a file |
| `run_command` | ⚠️ Yes | Run a shell command (whitelist-restricted) |
| `create_branch` | ⚠️ Yes | Create a new git branch |
| `commit_and_push` | ⚠️ Yes | Stage, commit, push to GitHub |
| `create_pr` | ⚠️ Yes | Open a GitHub Pull Request |
| `get_issue` | ✅ No | Fetch a GitHub issue's details |

---

## 🛡️ Safety Features

- **Human approval** is required for every file write, terminal command, and git operation — the agent cannot change anything without your `y`.
- **Path sandboxing** — file tools refuse to access paths outside `REPO_PATH`.
- **Command whitelist** — only commands starting with allowed prefixes run. Add more in `.env`:
  ```env
  ALLOWED_COMMANDS=git,python,pytest,pip,dir,echo,type,npm,node
  ```

---

## 💡 Example Tasks to Try

```
Read the file calculator.py and explain what it does
List all Python files in this project
Fix the division-by-zero bug in calculator.py
Run the tests with pytest
Search for all TODO comments in the codebase
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `ollama: command not found` | Make sure Ollama is installed and `ollama serve` is running |
| `Connection refused` on Ollama | Start Ollama: open a new terminal and run `ollama serve` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` with venv activated |
| `GEMINI_API_KEY not set` | Either set the key or switch `LLM_PROVIDER=ollama` |
| Agent loops without answering | gemma3:4b may struggle with complex tool-calling; try a simpler task first |
| GitHub tools fail | Set a valid `GITHUB_TOKEN` in `.env` (needs `repo` scope) |

---

## 🔑 Getting a Free GitHub Token (optional)

1. GitHub → your profile picture → **Settings**
2. **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
3. Click **Generate new token**
4. Set expiry, select your repo under *Repository access*
5. Permissions: **Contents** (Read & Write), **Pull requests** (Read & Write)
6. Copy the token → paste into `.env` as `GITHUB_TOKEN`

---

## 🆓 Getting a Free Gemini API Key (optional)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with a Google account
3. Click **Create API key**
4. Copy the key → paste into `.env` as `GEMINI_API_KEY`
5. Change `LLM_PROVIDER=gemini` in `.env`

---

*Built with LangChain · LangGraph · FastAPI · Ollama · PyGithub*
