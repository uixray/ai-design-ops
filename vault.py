"""
GitHub API client for writing files to the Obsidian vault.
Uses stdlib only (no extra deps) — urllib.request + base64 + json.
"""

import base64
import json
import re
import urllib.request
import urllib.error
from datetime import date


# ── Routing: content_type → vault path ───────────────────────────────────────
CONTENT_TYPE_PATHS = {
    "research": "03-research/articles",
    "pattern":  "02-patterns",
    "clipping": "09-knowledge/clippings",
    "guide":    "01-design-system/guides",
    "digest":   "09-knowledge/digests",
}


def slugify(text: str) -> str:
    """Convert arbitrary text to kebab-case filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text[:80].strip("-")


def build_frontmatter(
    title: str,
    content_type: str,
    tags: list,
    description: str,
) -> str:
    today = date.today().isoformat()
    tag_list = json.dumps(tags, ensure_ascii=False)
    return (
        "---\n"
        f'title: "{title}"\n'
        f"type: {content_type}\n"
        "status: seed\n"
        'version: "0.1.0"\n'
        f"created: {today}\n"
        f"updated: {today}\n"
        "freshness: current\n"
        f"freshness_checked: {today}\n"
        f"tags: {tag_list}\n"
        "related_components: []\n"
        "related_tokens: []\n"
        "related_patterns: []\n"
        "platforms: [web, iOS, Android]\n"
        f'description: "{description}"\n'
        "---"
    )


def vault_put_file(
    token: str,
    repo: str,
    branch: str,
    path: str,
    content: str,
    message: str,
) -> dict:
    """Create or update a file in a GitHub repo via REST API v3."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    # Fetch existing SHA (required for updates, omit for create)
    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            existing = json.loads(resp.read())
            sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    body: dict = {"message": message, "content": encoded, "branch": branch}
    if sha:
        body["sha"] = sha

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="PUT")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return {
                "path": path,
                "github_url": f"https://github.com/{repo}/blob/{branch}/{path}",
                "commit_sha": result.get("commit", {}).get("sha", ""),
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"GitHub API {e.code}: {err_body}")
