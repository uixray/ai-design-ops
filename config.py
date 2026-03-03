import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# --- КЛЮЧИ И URL ---
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1")
LM_STUDIO_API_KEY = "lm-studio"

YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIGMA_FILE_KEY = os.getenv("FIGMA_FILE_KEY", "").strip()

# --- КОНФИГУРАЦИЯ АГЕНТОВ ---
AGENTS_CONFIG = {
    "orchestrator": {
        "name": "Orchestrator",
        "provider": "yandex",
        "model_key": "yandexgpt",
        "temperature": 0.1,
        "description": "Управляющий"
    },
    
    "research_lead": {
        "name": "Researcher (Perplexity)",
        "provider": "perplexity",
        "model_key": "sonar-pro",
        "temperature": 0.1,
        "description": "Поиск в интернете, тренды, факты, конкуренты.",
        "system_prompt": """Ты — Senior UX Researcher. 
Твоя цель: Найти достоверную информацию, подтвержденную фактами.
Методология: Опирайся на стандарты Nielsen Norman Group (NNG), Baymard Institute.
Формат: Краткий ответ + Маркированный список + Источники."""
    },
    
    "visual_lead": {
        "name": "Visual Lead (Gemini)",
        "provider": "google", 
        "model_key": "gemini-1.5-pro",
        "temperature": 0.2,
        "description": "Анализ изображений и скриншотов.",
        "system_prompt": """Ты — Art Director и эксперт по UI. 
Цель: Визуальное совершенство и доступность (WCAG 2.1).
Смотри на: Иерархию, Контраст, Сетку, Тренды."""
    },
    
    "tech_lead": {
        "name": "Tech Lead (Gemini)",
        "provider": "google",
        "model_key": "gemini-1.5-pro", 
        "temperature": 0.1,
        "description": "Написание кода (React, CSS), техническая архитектура.",
        "system_prompt": """Ты — Senior Frontend Architect.
Стек: React, TypeScript, Tailwind CSS.
Принципы: DRY, Clean Code, Mobile-First."""
    },
    
    "product_lead": {
        "name": "Product Lead (Alice)",
        "provider": "yandex",
        "model_key": "alice",
        "temperature": 0.7,
        "description": "Креативные тексты, маркетинг, 'живой' язык.",
        "system_prompt": """Ты — Lead UX Writer. Язык: Русский.
Tone of Voice: Полезный, Понятный, Человечный. Без канцеляризмов."""
    },
    
    "logic_lead": {
        "name": "Logic Lead (YandexGPT)",
        "provider": "yandex",
        "model_key": "yandexgpt",
        "temperature": 0.1,
        "description": "Формальные тексты, переводы, структура.",
        "system_prompt": """Ты — Системный Аналитик.
Цель: Структурировать хаос. Переводы, таблицы, тех. требования."""
    },

    # --- Tool-based agents (v2) ---
    "vault_writer": {
        "name": "Vault Writer",
        "provider": "tool",
        "default_tool": "vault_write",
        "description": "Сохраняет результат работы команды в Obsidian vault (GitHub API). tool_args: title, content_type (research|pattern|clipping|guide), tags[], description.",
    },

    "figma_reader": {
        "name": "Figma Reader",
        "provider": "tool",
        "default_tool": "figma_get_node",
        "description": "Читает данные компонента или фрейма из Figma. tool_args: node_id (обязательно), file_key (опционально).",
    },
}