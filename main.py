import sys
import time
import json
import uuid
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

# Импортируем наши модули
from config import AGENTS_CONFIG
from schemas import ChatRequest, OrchestratorPlan
from utils import generate_system_prompt, extract_text_from_content, extract_json_smart
from providers import unified_completion
from executor import execute_actions
from commands import execute_slash_command

sys.stdout.reconfigure(encoding='utf-8')
app = FastAPI(title="Design Ops Orchestrator (Modular)")

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
        # Имитация посимвольного вывода для плавности (опционально) или чанком
        yield f"data: {json.dumps({'id': cid, 'object': 'chat.completion.chunk', 'created': t, 'model': 'modular', 'choices': [{'index': 0, 'delta': {'content': final_output}, 'finish_reason': None}]})}\n\n"
        yield f"data: {json.dumps({'id': cid, 'object': 'chat.completion.chunk', 'created': t, 'model': 'modular', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    if request.stream:
        return StreamingResponse(stream_gen(), media_type="text/event-stream")
    else:
        return {"choices": [{"message": {"content": final_output}}], "usage": {}}