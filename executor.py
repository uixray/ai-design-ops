"""
Shared action execution loop.

Used by:
  - main.py  (orchestrator execution phase)
  - commands.py (slash command direct execution)

This keeps the execution logic in one place.
"""

from config import AGENTS_CONFIG
from providers import unified_completion
from tools import run_tool


def execute_actions(actions: list) -> tuple[list[str], str]:
    """
    Execute a list of action dicts sequentially.

    Each action dict:
        { "agent": str, "instruction": str,
          "tool": str | None, "tool_args": dict | None }

    Returns:
        (results_list, combined_output_string)
        - results_list : one string per action (for chaining context)
        - combined_output_string : all results joined
    """
    results: list[str] = []

    for action in actions:
        agent_id = action.get("agent", "")

        if agent_id not in AGENTS_CONFIG:
            print(f"⚠️ [Executor] Неизвестный агент: {agent_id}", flush=True)
            continue

        agent_cfg  = AGENTS_CONFIG[agent_id]
        agent_name = agent_cfg.get("name", agent_id)

        # ── Tool-based agent ──────────────────────────────────────────────────
        if agent_cfg.get("provider") == "tool":
            tool_name = action.get("tool") or agent_cfg.get("default_tool", "")
            tool_args = dict(action.get("tool_args") or {})

            # Auto-inject accumulated content for vault_write when content absent
            if tool_name == "vault_write" and "content" not in tool_args:
                tool_args["content"] = "\n\n".join(
                    r.strip() for r in results if r.strip()
                )

            res = run_tool(tool_name, tool_args)

        # ── LLM agent ─────────────────────────────────────────────────────────
        else:
            sys_prompt  = agent_cfg.get("system_prompt", "")
            instruction = action.get("instruction", "")
            agent_msgs  = [
                {"role": "system", "content": sys_prompt, "text": sys_prompt},
                {"role": "user",   "content": instruction, "text": instruction},
            ]
            res = unified_completion(agent_id, agent_msgs)

        results.append(f"\n🔹 **{agent_name}**: {res}\n")

    return results, "".join(results)
