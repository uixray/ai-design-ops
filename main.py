import sys
import time
import json
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

# Импортируем наши модули
from config import AGENTS_CONFIG
from schemas import ChatRequest, OrchestratorPlan
from utils import generate_system_prompt, extract_text_from_content, extract_json_smart
from providers import unified_completion
from executor import execute_actions
from commands import execute_slash_command
from keys import (validate_key, consume_key, generate_key, list_keys,
                  delete_key, consume_trial, get_trial_remaining, ADMIN_TOKEN)
from presets import get_context_for_preset, list_preset_names, list_presets

sys.stdout.reconfigure(encoding='utf-8')
app = FastAPI(title="Design Ops Orchestrator (Modular)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /v1/direct ────────────────────────────────────────────────────────────────

@app.post("/v1/direct")
async def direct_endpoint(request: ChatRequest, req: Request):
    """Direct LLM call — bypasses orchestrator. Used by Figma plugins.
    Supports API key quota (X-API-Key header) and free trial (by IP, 10 requests).
    Injects preset_key context into system prompt.
    """
    # — Auth / quota check —
    api_key = req.headers.get("X-API-Key", "") or (request.api_key or "")

    if api_key:
        if not consume_key(api_key):
            raise HTTPException(
                status_code=402,
                detail="Quota exceeded. Contact @uixray to top up your key."
            )
        print(f"🔑 [Key] {api_key[:12]}... used", flush=True)
    else:
        ip = (req.headers.get("X-Forwarded-For") or
              req.headers.get("X-Real-IP") or
              (req.client.host if req.client else None) or
              "unknown")
        if not consume_trial(ip):
            remaining = get_trial_remaining(ip)
            raise HTTPException(
                status_code=402,
                detail=f"Free trial exhausted (10/10). Get an API key: t.me/uixray"
            )
        remaining_after = get_trial_remaining(ip)
        print(f"🆓 [Trial] IP={ip} remaining={remaining_after}", flush=True)

    # — Build messages with optional preset context —
    preset_key = request.preset_key
    preset_context = get_context_for_preset(preset_key)
    if preset_key:
        print(f"🎛️ [Preset] {preset_key}", flush=True)

    msgs = []
    for m in request.messages:
        txt = extract_text_from_content(m.content)
        if m.role == "system" and preset_context:
            txt += preset_context
        msgs.append({"role": m.role, "content": txt})

    result = unified_completion("logic_lead", msgs)
    return {"choices": [{"message": {"role": "assistant", "content": result}}], "usage": {}}


# ── /v1/presets ───────────────────────────────────────────────────────────────

@app.get("/v1/presets")
async def list_presets_endpoint():
    """Return built-in component presets with full context for client-side editing (no auth required)."""
    return list_presets()


# ── /keys/* ───────────────────────────────────────────────────────────────────

def _check_admin(req: Request):
    token = req.headers.get("X-Admin-Token", "")
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/keys/validate")
async def validate_key_endpoint(body: dict):
    """Check if API key is valid and return quota info."""
    key = body.get("key", "")
    info = validate_key(key)
    if not info:
        return {"valid": False}
    return {"valid": True, **info}


@app.post("/keys/generate")
async def generate_key_endpoint(body: dict, req: Request):
    """[Admin] Generate a new API key with given quota."""
    _check_admin(req)
    quota = body.get("quota")
    if not quota or not isinstance(quota, int) or quota <= 0:
        raise HTTPException(status_code=400, detail="'quota' must be a positive integer")
    label = body.get("label", "")
    result = generate_key(quota=quota, label=label)
    print(f"🔑 [Admin] Generated key: {result['token'][:16]}... quota={quota} label={label}", flush=True)
    return result


@app.get("/keys/stats")
async def keys_stats(req: Request):
    """[Admin] List all keys with usage statistics."""
    _check_admin(req)
    return list_keys()


@app.delete("/keys/{token}")
async def delete_key_endpoint(token: str, req: Request):
    """[Admin] Delete an API key."""
    _check_admin(req)
    if not delete_key(token):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"deleted": True}


# ── /v1/chat/completions ──────────────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_endpoint(request: ChatRequest):
    print(f"\n📥 [API] Stream={request.stream}", flush=True)

    # 1. Подготовка истории
    prompt = generate_system_prompt()
    history = [{"role": "system", "content": prompt}]

    # Sliding Window + Обработка контента
    for m in request.messages[-10:]:
        if m.role != "system":
            txt = extract_text_from_content(m.content)
            history.append({"role": m.role, "content": txt})

    final_output = ""

    # ── Slash command intercept ───────────────────────────────────────────────
    last_user_msg = ""
    for m in request.messages:
        if m.role == "user":
            last_user_msg = extract_text_from_content(m.content)

    if last_user_msg.strip().startswith("/"):
        print(f"⚡ [Slash] Перехвачено: {last_user_msg[:60]}", flush=True)
        slash_result = execute_slash_command(last_user_msg.strip())
        if slash_result is not None:
            final_output = slash_result
            # Skip orchestrator entirely
            async def stream_gen():
                cid = f"chatcmpl-{uuid.uuid4()}"
                t = int(time.time())
                yield f"data: {json.dumps({'id': cid, 'object': 'chat.completion.chunk', 'created': t, 'model': 'modular', 'choices': [{'index': 0, 'delta': {'content': final_output}, 'finish_reason': None}]})}\\n\\n"
                yield f"data: {json.dumps({'id': cid, 'object': 'chat.completion.chunk', 'created': t, 'model': 'modular', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\\n\\n"
                yield "data: [DONE]\\n\\n"
            if request.stream:
                return StreamingResponse(stream_gen(), media_type="text/event-stream")
            else:
                return {"choices": [{"message": {"content": final_output}}], "usage": {}}

    try:
        # 2. Вызов Дирижера (Local)
        orch_cfg = AGENTS_CONFIG["orchestrator"]
        print(f"🧠 [Дирижер] Анализирует...", flush=True)

        # Получаем полный ответ от оркестратора (без стрима для парсинга)
        raw_resp = unified_completion("orchestrator", history)

        # 3. Парсинг и Валидация
        data = extract_json_smart(raw_resp)

        # Валидация через Pydantic
        plan = None
        if data:
            try:
                # Если поля пропущены, добавляем заглушки
                if "actions" not in data: data["actions"] = []
                plan = OrchestratorPlan(**data)
            except ValidationError:
                print("⚠️ Ошибка валидации плана")

        if not plan:
            print("⚠️ Fallback: отдаем сырой текст")
            final_output = raw_resp
        else:
            final_output = plan.reply_text

            # 4. Исполнение (Execution)
            if plan.status == "execution":
                print(f"🚀 [EXECUTION] Задач: {len(plan.actions)}", flush=True)
                actions_dicts = [
                    {
                        "agent":       a.agent,
                        "instruction": a.instruction,
                        "tool":        a.tool,
                        "tool_args":   a.tool_args,
                    }
                    for a in plan.actions
                    if a.agent in AGENTS_CONFIG
                ]
                _, combined = execute_actions(actions_dicts)
                final_output += "\n" + combined
            else:
                print("✋ [PROPOSAL]", flush=True)

    except Exception as e:
        print(f"❌ Critical Error: {e}", flush=True)
        final_output = f"System Error: {e}"

    # 5. Стриминг ответа клиенту
    async def stream_gen():
        cid = f"chatcmpl-{uuid.uuid4()}"
        t = int(time.time())
        yield f"data: {json.dumps({'id': cid, 'object': 'chat.completion.chunk', 'created': t, 'model': 'modular', 'choices': [{'index': 0, 'delta': {'content': final_output}, 'finish_reason': None}]})}\n\n"
        yield f"data: {json.dumps({'id': cid, 'object': 'chat.completion.chunk', 'created': t, 'model': 'modular', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    if request.stream:
        return StreamingResponse(stream_gen(), media_type="text/event-stream")
    else:
        return {"choices": [{"message": {"content": final_output}}], "usage": {}}
