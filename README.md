# AI Design Ops

Multi-agent AI orchestrator for design operations. Built by a designer, for designers.

Routes requests to specialized AI agents depending on the task — research, visual analysis, code generation, UX writing — and can save results directly to an Obsidian vault via GitHub API.

Exposes an OpenAI-compatible API, so it works with any chat client (Open WebUI, SillyTavern, etc.) or can be used as a provider in custom tools.

---

## How it works

```
Your request
    ↓
Orchestrator (YandexGPT Lite)
Analyzes the request, returns a JSON plan

  status: proposal             status: execution
  ↓                            ↓
Replies with a plan        Runs agents in sequence:
and asks for confirmation  → research_lead (Perplexity)
                           → tech_lead (Gemini)
                           → vault_writer (GitHub API)
                                ↓
                           Results → your chat
```

### Agents

| ID | Name | Provider | Role |
|---|---|---|---|
| `orchestrator` | Orchestrator | YandexGPT Lite | Plans tasks, routes to agents |
| `research_lead` | Researcher | Perplexity Sonar Pro | Web search, trends, facts |
| `visual_lead` | Visual Lead | Gemini 1.5 Pro | Image and UI analysis |
| `tech_lead` | Tech Lead | Gemini 1.5 Pro | Code (React, TypeScript, CSS) |
| `product_lead` | Product Lead | YandexGPT | UX writing, marketing copy |
| `logic_lead` | Logic Lead | YandexGPT | Structured text, translations |
| `vault_writer` | Vault Writer | GitHub API | Saves results to Obsidian vault |
| `figma_reader` | Figma Reader | Figma REST API | Reads component data from Figma |

---

## Slash commands

Skip the orchestrator and call agents directly:

```
/research topic              → Perplexity search
/r topic                     → same shorthand

/visual                      → Gemini image/UI analysis
/tech write a Button component in React
/product write onboarding copy
/logic translate to English

/save {title="Name" type=research tags=ux,mobile}
/figma {node=123:456}

/help                        → list all commands
```

**Pipe chaining:**
```
/research design tokens | save {title="Design Tokens" type=research}
/figma {node=123:456} | visual analyze the component
```

**Inline save flag:**
```
/research accessibility patterns {save title="A11y Patterns"}
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
# Required: Yandex Cloud (orchestrator + product/logic agents)
YANDEX_API_KEY=your_key
YANDEX_FOLDER_ID=your_folder_id

# Required for research
PERPLEXITY_API_KEY=your_key

# Required for visual/tech
GEMINI_API_KEY=your_key

# Optional: save results to Obsidian vault
GITHUB_TOKEN=your_pat          # Fine-grained, Contents: Read & Write
GITHUB_REPO=owner/repo-name
GITHUB_BRANCH=master

# Optional: read Figma components
FIGMA_ACCESS_TOKEN=your_pat
FIGMA_FILE_KEY=your_file_key
```

### 3. Run

```bash
uvicorn main:app --reload --port 8000
```

Server starts at `http://localhost:8000`.

### 4. Connect a chat client

In any OpenAI-compatible client (Open WebUI, etc.):

```
API URL:  http://localhost:8000/v1
API Key:  anything
Model:    modular
```

---

## Vault integration

`vault_writer` saves results as Markdown files to a GitHub repository with Obsidian-compatible frontmatter:

```yaml
---
title: "Result Title"
type: research        # research | pattern | clipping | guide | digest
status: seed
version: "0.1.0"
created: 2026-03-04
tags: ["type/research"]
---
```

File paths follow the vault routing table:

| type | destination |
|---|---|
| `research` | `03-research/articles/` |
| `pattern` | `02-patterns/` |
| `clipping` | `09-knowledge/clippings/` |
| `guide` | `01-design-system/guides/` |
| `digest` | `09-knowledge/digests/` |

---

## Project structure

```
main.py          FastAPI app, request handling, slash command intercept
config.py        Agent configuration, API keys
providers.py     Provider adapters (Yandex, Gemini, Perplexity, local)
executor.py      Shared action execution loop
commands.py      Slash command parser
schemas.py       Pydantic models
utils.py         System prompt generation, JSON parsing
vault.py         GitHub API client for vault writes
tools.py         Tool dispatcher (vault_write, figma_get_node)
```

---

## AHK integration

If you use AutoHotkey for desktop automation, you can add smart routing to send complex queries automatically to this server when it's running:

```ahk
; In your TryRequest() function — check for research keywords
; and route to http://localhost:8000/v1/chat/completions if server is up
```

See `Runtime.ahk` in [DesignOps Assistant](https://github.com/uixray) for a full example.

---

## Stack

Python · FastAPI · Pydantic · Yandex Cloud ML SDK · Google Generative AI · OpenAI SDK (Perplexity/local) · GitHub REST API · Figma REST API
