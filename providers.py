import openai
import os
from config import LM_STUDIO_URL, LM_STUDIO_API_KEY, YANDEX_FOLDER_ID, YANDEX_API_KEY, GEMINI_API_KEY, PERPLEXITY_API_KEY, AGENTS_CONFIG
from utils import extract_text_from_list

# --- ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ ---
print("⏳ [PROVIDERS] Инициализация клиентов...", flush=True)

# 1. Local
local_client = openai.OpenAI(base_url=LM_STUDIO_URL, api_key=LM_STUDIO_API_KEY)

# 2. Yandex
yandex_sdk = None
try:
    from yandex_cloud_ml_sdk import YCloudML
    if YANDEX_FOLDER_ID and YANDEX_API_KEY:
        yandex_sdk = YCloudML(folder_id=YANDEX_FOLDER_ID, auth=YANDEX_API_KEY)
        print("✅ Yandex SDK: Ready", flush=True)
except ImportError:
    print("❌ Yandex SDK: Not installed", flush=True)
except Exception as e:
    print(f"❌ Yandex SDK: Error {e}", flush=True)

# 3. Google
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ Google Gemini: Ready", flush=True)
except: pass

# 4. Perplexity
perplexity_client = None
if PERPLEXITY_API_KEY:
    perplexity_client = openai.OpenAI(base_url="https://api.perplexity.ai", api_key=PERPLEXITY_API_KEY)
    print("✅ Perplexity: Ready", flush=True)


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def merge_consecutive_messages(messages: list) -> list:
    """
    Склеивает подряд идущие сообщения от одной роли, чтобы не ломать Gemma/Llama.
    Пример: [User, User, Assistant] -> [User (merged), Assistant]
    """
    if not messages:
        return []
    
    merged = [messages[0]]
    
    for msg in messages[1:]:
        last_msg = merged[-1]
        
        # Если роль совпадает - клеим контент
        if msg["role"] == last_msg["role"]:
            # Добавляем перенос строки для читаемости
            last_msg["content"] += "\n\n" + msg["content"]
        else:
            merged.append(msg)
            
    return merged

# --- ФУНКЦИИ ВЫЗОВА ---

def google_completion(messages, model, temp):
    """Запрос к Google Gemini с автоматическим Fallback"""
    try:
        import google.generativeai as genai
        
        def try_generate(target_model):
            m = genai.GenerativeModel(target_model)
            last_content = messages[-1].get("content") or messages[-1].get("text")
            config = genai.types.GenerationConfig(temperature=temp)
            return m.generate_content(str(last_content), generation_config=config).text

        try:
            return try_generate(model)
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "not found" in error_str:
                print(f"⚠️ [Gemini] Модель '{model}' не найдена. Пробую Fallback на 'gemini-2.0-flash-lite'...", flush=True)
                return try_generate("gemini-2.0-flash-lite")
            else:
                raise e
    except Exception as e:
        return f"[Gemini Error: {e}]"

def perplexity_completion(messages, model, temp):
    if not perplexity_client: return "[Perplexity Key Missing]"
    clean = [{"role": m["role"], "content": str(m.get("content") or m.get("text"))} for m in messages]
    return perplexity_client.chat.completions.create(model=model, messages=clean, temperature=temp).choices[0].message.content

def yandex_completion(messages, model_key, temp):
    if not yandex_sdk: return "[Yandex SDK Missing]"
    
    clean_msgs = []
    for m in messages:
        txt = m.get("text") or m.get("content")
        if isinstance(txt, list): txt = extract_text_from_list(txt)
        clean_msgs.append({"role": m["role"], "text": str(txt) if txt else ""})

    def run_model(target_key):
        model = yandex_sdk.models.completions(target_key)
        return model.configure(temperature=temp).run(clean_msgs).alternatives[0].text

    try:
        return run_model(model_key)
    except Exception as e:
        print(f"⚠️ [Yandex] Ошибка модели '{model_key}': {e}. Пробую Fallback на 'yandexgpt'...", flush=True)
        if model_key != "yandexgpt":
            try:
                return run_model("yandexgpt")
            except Exception as e2:
                return f"[Yandex Critical Error: {e2}]"
        else:
            return f"[Yandex Error: {e}]"

def local_completion(messages, model, temp, stream=False):
    """Функция для вызова локальной модели через LM Studio"""
    # 1. Очистка контента
    clean = []
    for m in messages:
        c = m.get("content") or m.get("text")
        if isinstance(c, list): c = extract_text_from_list(c)
        clean.append({"role": m["role"], "content": c})
    
    # 2. Слияние дублей (FIX для Gemma)
    sanitized_messages = merge_consecutive_messages(clean)
    
    if stream:
        print(f"   🧠 [Local] Stream started...", flush=True)
        return local_client.chat.completions.create(model=model, messages=sanitized_messages, temperature=temp, stream=True)
    
    resp = local_client.chat.completions.create(model=model, messages=sanitized_messages, temperature=temp)
    return resp.choices[0].message.content

def unified_completion(agent_key, messages):
    cfg = AGENTS_CONFIG.get(agent_key)
    if not cfg: return f"Error: Agent {agent_key} not configured"
    
    p, m, t = cfg["provider"], cfg["model_key"], cfg.get("temperature", 0.3)
    print(f"⚡ [Call] {agent_key} -> {p} ({m})", flush=True)
    
    if p == "google": return google_completion(messages, m, t)
    if p == "perplexity": return perplexity_completion(messages, m, t)
    if p == "yandex": return yandex_completion(messages, m, t)
    if p == "local": return local_completion(messages, m, t, stream=False)
    return "Unknown provider"