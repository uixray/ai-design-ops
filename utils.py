import json
import re
from typing import Union, List, Any
from config import AGENTS_CONFIG

def generate_system_prompt():
    """Генерирует инструкцию для Дирижера на основе конфига"""
    # AI-агенты (LLM)
    llm_agents = "\n".join([
        f"{k} — {v['description']}"
        for k, v in AGENTS_CONFIG.items()
        if k != "orchestrator" and v.get("provider") != "tool"
    ])
    # Tool-агенты (действия, не LLM)
    tool_agents = "\n".join([
        f"{k} — {v['description']}"
        for k, v in AGENTS_CONFIG.items()
        if v.get("provider") == "tool"
    ])

    return f"""
Ты — Design Ops Director. Твоя задача — управлять агентами.
ТЫ САМ НЕ ВЫПОЛНЯЕШЬ РАБОТУ. ТЫ ТОЛЬКО ПЛАНИРУЕШЬ.

Твоя команда — AI агенты (Используй эти ID в JSON):
{llm_agents}

Инструменты — выполняют действия, не генерируют текст:
{tool_agents}

АЛГОРИТМ:
1. Новый запрос -> Статус "proposal". Предложи план действий пользователю (используй красивые имена).
2. Согласие ("Ок", "Да") -> Статус "execution". Заполни массив actions (технические ID).
3. Если нужно сохранить результат в базу знаний — добавь vault_writer последним в actions.

ОТВЕТ СТРОГО В FORMAT JSON:
{{
  "status": "proposal" | "execution",
  "reply_text": "Текст ответа...",
  "actions": [
    {{ "agent": "id_агента", "instruction": "..." }},
    {{ "agent": "vault_writer", "instruction": "сохрани как research", "tool": "vault_write", "tool_args": {{ "title": "Название", "content_type": "research", "tags": ["type/research"], "description": "Описание" }} }}
  ]
}}
"""

def extract_text_from_list(content_list: list) -> str:
    text = []
    for item in content_list:
        if isinstance(item, dict) and item.get("type") == "text":
            text.append(item.get("text", ""))
    return " ".join(text) + " [Картинка]"

def extract_text_from_content(content: Union[str, List[Any]]) -> str:
    if isinstance(content, str): return content
    return extract_text_from_list(content)

def extract_json_smart(text: str) -> dict:
    """Умный парсер JSON с защитой от мусора"""
    clean = text.replace("```json", "").replace("```", "").strip()
    try:
        start = clean.find('{'); end = clean.rfind('}')
        if start != -1 and end != -1:
            return json.loads(clean[start:end+1])
    except: pass
    
    # Regex Fallback
    try:
        match = re.search(r'"reply_text":\s*"(.*?)(?<!\\)"', text, re.DOTALL)
        status_match = re.search(r'"status":\s*"([^"]+)"', text)
        if match: 
            txt = bytes(match.group(1), "utf-8").decode("unicode_escape")
            return {"status": status_match.group(1) if status_match else "proposal", "reply_text": txt, "actions": []}
    except: pass
    return None