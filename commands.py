"""
Slash command parser and executor for AI Design Ops.

Syntax:
    /command [instruction] {key=value} {key="multi word value"}
    /command query | save {title="Name" type=research}
    /command query {save title="Name"}    ← inline save flag

Agent shortcuts → agent IDs:
    /research (/r)  → research_lead
    /visual   (/v)  → visual_lead
    /tech     (/t)  → tech_lead
    /product  (/p)  → product_lead
    /logic    (/l)  → logic_lead
    /save     (/s)  → vault_writer (tool)
    /figma    (/fig)→ figma_reader (tool)

Pipe chaining:
    /research topic | save {title="Topic Research"}
    Steps execute sequentially; each step's output is injected
    into the next step's instruction as context if needed.

Brace variables:
    {key=value}          — simple value
    {key="long value"}   — quoted value (spaces allowed)
    {save}               — shorthand: append vault_writer at end
    {save title="X" type=research tags=ux,mobile}
"""

import re
from executor import execute_actions

# ── Agent / tool aliases ──────────────────────────────────────────────────────

AGENT_COMMANDS: dict[str, str] = {
    "research": "research_lead",
    "r":        "research_lead",
    "visual":   "visual_lead",
    "v":        "visual_lead",
    "tech":     "tech_lead",
    "t":        "tech_lead",
    "product":  "product_lead",
    "p":        "product_lead",
    "logic":    "logic_lead",
    "l":        "logic_lead",
}

TOOL_COMMANDS: dict[str, tuple[str, str]] = {
    # alias → (agent_id, tool_name)
    "save":   ("vault_writer", "vault_write"),
    "s":      ("vault_writer", "vault_write"),
    "figma":  ("figma_reader", "figma_get_node"),
    "fig":    ("figma_reader", "figma_get_node"),
}

HELP_TEXT = """\
🛠️ **Slash Commands**

**Агенты (LLM):**
`/research` `/r`  — поиск в интернете, тренды, факты
`/visual`   `/v`  — анализ изображений, UI
`/tech`     `/t`  — код (React, TypeScript, CSS)
`/product`  `/p`  — тексты, UX writing, маркетинг
`/logic`    `/l`  — структура, переводы, таблицы

**Инструменты:**
`/save` `/s`  — сохранить в Obsidian vault
`/figma` `/fig`  — прочитать компонент из Figma

**Переменные в `{}`:**
```
/save {title="Название" type=research tags=ux,mobile description="Краткое описание"}
```
Типы: `research` | `pattern` | `clipping` | `guide` | `digest`

**Pipe (цепочки):**
```
/research тема | save {title="Тема" type=research}
/figma {node=123:456} | visual
```

**Инлайн-флаг сохранения:**
```
/research токенизация в дизайн-системах {save title="Токены DS"}
```
"""


# ── Brace variable parser ─────────────────────────────────────────────────────

_BRACE_RE = re.compile(r'\{([^}]*)\}')
_KV_QUOTED = re.compile(r'(\w+)="([^"]*)"')
_KV_PLAIN  = re.compile(r'(\w+)=([^\s}]+)')


def parse_braces(text: str) -> tuple[str, dict]:
    """
    Extract all {key=value} blocks from text.
    Returns (cleaned_text_without_braces, params_dict).
    Quoted values: {key="long value"}.
    Tags: {tags=a,b,c} → params["tags"] = ["a", "b", "c"].
    Bare flag: {save} → params["__save__"] = True.
    """
    params: dict = {}
    brace_matches = _BRACE_RE.findall(text)

    for block in brace_matches:
        block = block.strip()
        if not block:
            continue

        # Bare save flag: {save ...}  or  {save}
        first_word = block.split()[0] if block.split() else ""
        if first_word in ("save", "s"):
            params["__save__"] = True
            block = block[len(first_word):].strip()  # strip "save" prefix

        # Quoted pairs first
        for m in _KV_QUOTED.finditer(block):
            k, v = m.group(1), m.group(2)
            params[k] = v

        # Then plain pairs (skip already-matched ranges)
        already_keys = set(m.group(1) for m in _KV_QUOTED.finditer(block))
        for m in _KV_PLAIN.finditer(block):
            k, v = m.group(1), m.group(2)
            if k in already_keys:
                continue
            if k == "tags":
                params["tags"] = [t.strip() for t in v.split(",") if t.strip()]
            else:
                params[k] = v

    # Remove all brace blocks from text
    clean = _BRACE_RE.sub("", text).strip()
    return clean, params


# ── Segment parser ────────────────────────────────────────────────────────────

def _build_agent_action(agent_id: str, instruction: str) -> dict:
    return {"agent": agent_id, "instruction": instruction}


def _build_tool_action(agent_id: str, tool_name: str, instruction: str, params: dict) -> dict:
    tool_args: dict = {}

    # Map known params to tool_args
    for key in ("title", "content_type", "type", "tags", "description",
                "node", "node_id", "file_key"):
        if key in params:
            # Normalize: "type" → "content_type"
            dest = "content_type" if key == "type" else key
            dest = "node_id" if key == "node" else dest
            tool_args[dest] = params[key]

    # Instruction as description fallback
    if instruction and "description" not in tool_args:
        tool_args["description"] = instruction

    return {
        "agent":     agent_id,
        "instruction": instruction or "выполни",
        "tool":      tool_name,
        "tool_args": tool_args,
    }


def parse_segment(raw: str) -> dict | None:
    """
    Parse one pipe segment like '/research topic {save title="X"}'.
    Returns an action dict or None if segment is blank/unknown.
    """
    raw = raw.strip()
    if not raw:
        return None

    # Must start with /
    if not raw.startswith("/"):
        # Treat as bare instruction for orchestrator — not a slash command
        return None

    # Strip leading /
    rest = raw[1:].strip()

    # Extract command word
    parts = rest.split(None, 1)  # split on first whitespace
    cmd   = parts[0].lower()
    tail  = parts[1] if len(parts) > 1 else ""

    # Parse braces from tail
    instruction, params = parse_braces(tail)

    if cmd in AGENT_COMMANDS:
        agent_id = AGENT_COMMANDS[cmd]
        return _build_agent_action(agent_id, instruction)

    if cmd in TOOL_COMMANDS:
        agent_id, tool_name = TOOL_COMMANDS[cmd]
        return _build_tool_action(agent_id, tool_name, instruction, params)

    if cmd in ("help", "h"):
        return {"__help__": True}

    return None  # unknown command


# ── Full pipeline parser ──────────────────────────────────────────────────────

def parse_slash_command(text: str) -> list[dict] | None:
    """
    Parse a full slash command string (potentially with pipe chaining).
    Returns list of action dicts, or None if text is not a slash command.
    """
    text = text.strip()
    if not text.startswith("/"):
        return None

    segments = [s.strip() for s in text.split("|")]
    actions: list[dict] = []

    # Parse all segments; only first must have /command prefix
    for i, seg in enumerate(segments):
        if i > 0 and not seg.startswith("/"):
            # Shorthand: bare command word after pipe, e.g.  "| save {title=X}"
            seg = "/" + seg

        action = parse_segment(seg)
        if action is None:
            continue

        if action.get("__help__"):
            return [{"__help__": True}]

        actions.append(action)

    if not actions:
        return None

    # Handle {save} inline flag: if any action has params with __save__
    # We need to re-parse with brace-level save detection
    # Check last segment's raw tail for {save ...} flag
    last_seg_raw = segments[-1]
    _, last_params = parse_braces(last_seg_raw[1:] if last_seg_raw.startswith("/") else last_seg_raw)

    if last_params.get("__save__"):
        # Append vault_writer at end
        vault_args: dict = {}
        for k in ("title", "type", "tags", "description"):
            if k in last_params:
                dest = "content_type" if k == "type" else k
                vault_args[dest] = last_params[k]
        actions.append({
            "agent":       "vault_writer",
            "instruction": "сохрани результаты",
            "tool":        "vault_write",
            "tool_args":   vault_args,
        })

    return actions


# ── Public entry point ────────────────────────────────────────────────────────

def execute_slash_command(text: str) -> str | None:
    """
    Parse and execute slash command.
    Returns output string, or None if text is not a slash command.
    Returns HELP_TEXT for /help.
    """
    actions = parse_slash_command(text)
    if actions is None:
        return None

    if actions and actions[0].get("__help__"):
        return HELP_TEXT

    print(f"⚡ [Slash] {len(actions)} action(s)", flush=True)
    _, combined = execute_actions(actions)
    return combined if combined.strip() else "✅ Выполнено."
