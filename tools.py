"""
Tool executor for AI Design Ops agents.

Each tool is a Python function: (args: dict) -> str (human-readable result).
The ToolExecutor.run() method dispatches by tool name.

Tools:
  vault_write    — save content to Obsidian vault via GitHub API
  figma_get_node — fetch a node from a Figma file
"""

import json
import os
import urllib.request
import urllib.error

from vault import (
    vault_put_file,
    build_frontmatter,
    slugify,
    CONTENT_TYPE_PATHS,
)


# ── vault_write ───────────────────────────────────────────────────────────────

def tool_vault_write(args: dict) -> str:
    """
    Save AI-generated content to the Obsidian vault.

    args:
      title        (str)      — document title (used as filename)
      content      (str)      — markdown body (without frontmatter)
      content_type (str)      — research | pattern | clipping | guide | digest
      tags         (list[str])— vault tags
      description  (str)      — one-sentence description for frontmatter
    """
    token  = os.getenv("GITHUB_TOKEN", "")
    repo   = os.getenv("GITHUB_REPO", "")
    branch = os.getenv("GITHUB_BRANCH", "master")

    if not token or not repo:
        return (
            "⚠️ vault_write: GITHUB_TOKEN или GITHUB_REPO не настроены в .env. "
            "Добавь их и перезапусти сервис."
        )

    title        = args.get("title", "Untitled")
    content      = args.get("content", "")
    content_type = args.get("content_type", "research")
    tags         = args.get("tags") or [f"type/{content_type}", "source/ai-design-ops"]
    description  = args.get("description") or title

    folder   = CONTENT_TYPE_PATHS.get(content_type, "03-research/articles")
    filename = f"{slugify(title)}.md"
    path     = f"{folder}/{filename}"

    frontmatter  = build_frontmatter(title, content_type, tags, description)
    full_content = f"{frontmatter}\n\n# {title}\n\n{content}"
    commit_msg   = f"feat({content_type}): add {filename} via AI Design Ops"

    try:
        result = vault_put_file(
            token=token,
            repo=repo,
            branch=branch,
            path=path,
            content=full_content,
            message=commit_msg,
        )
        return (
            f"✅ Сохранено в vault!\n"
            f"📄 Путь: `{result['path']}`\n"
            f"🔗 {result['github_url']}"
        )
    except Exception as e:
        return f"⚠️ vault_write ошибка: {e}"


# ── figma_get_node ────────────────────────────────────────────────────────────

def tool_figma_get_node(args: dict) -> str:
    """
    Fetch node data from a Figma file.

    args:
      node_id  (str) — Figma node ID, e.g. "123:456"
      file_key (str) — Figma file key (falls back to FIGMA_FILE_KEY env var)
    """
    token = os.getenv("FIGMA_ACCESS_TOKEN", "")
    if not token:
        return "⚠️ figma_get_node: FIGMA_ACCESS_TOKEN не настроен в .env"

    file_key = args.get("file_key") or os.getenv("FIGMA_FILE_KEY", "").strip()
    node_id  = args.get("node_id", "")

    if not file_key:
        return "⚠️ figma_get_node: FIGMA_FILE_KEY не задан"
    if not node_id:
        return "⚠️ figma_get_node: нужен node_id (например '123:456')"

    url = f"https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})

    try:
        with urllib.request.urlopen(req) as resp:
            data  = json.loads(resp.read())
            nodes = data.get("nodes", {})

        if not nodes:
            return f"⚠️ Узел '{node_id}' не найден в файле '{file_key}'"

        doc = next(iter(nodes.values()), {}).get("document", {})
        summary = {
            "name":           doc.get("name"),
            "type":           doc.get("type"),
            "fills":          doc.get("fills", [])[:3],
            "children_count": len(doc.get("children", [])),
            "children": [
                {"name": c.get("name"), "type": c.get("type")}
                for c in doc.get("children", [])[:10]
            ],
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

    except urllib.error.HTTPError as e:
        return f"⚠️ Figma API {e.code}: {e.read().decode('utf-8', errors='replace')}"
    except Exception as e:
        return f"⚠️ figma_get_node ошибка: {e}"


# ── Registry + dispatcher ─────────────────────────────────────────────────────

TOOLS: dict = {
    "vault_write":    tool_vault_write,
    "figma_get_node": tool_figma_get_node,
}

# Human-readable descriptions (used in orchestrator system prompt)
TOOLS_DESCRIPTIONS: dict = {
    "vault_write": (
        "Сохраняет контент в Obsidian vault. "
        "tool_args: title (str), content_type (research|pattern|clipping|guide), "
        "tags (list), description (str). "
        "Поле content заполняется автоматически из результатов предыдущих агентов."
    ),
    "figma_get_node": (
        "Читает данные узла из Figma. "
        "tool_args: node_id (str, обязательно), file_key (str, опционально)."
    ),
}


def run_tool(tool_name: str, args: dict) -> str:
    """Dispatch a tool call by name. Returns human-readable result string."""
    fn = TOOLS.get(tool_name)
    if not fn:
        return f"⚠️ Неизвестный инструмент: '{tool_name}'. Доступные: {list(TOOLS.keys())}"
    try:
        print(f"🔧 [TOOL] {tool_name}({list(args.keys())})", flush=True)
        return fn(args)
    except Exception as e:
        return f"⚠️ Инструмент '{tool_name}' упал с ошибкой: {e}"
