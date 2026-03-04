"""
Component presets — context hints injected into AI prompts.
Each preset contains:
  - name: human-readable display name
  - keywords: list of lowercase substrings to match against component name
  - context: detailed text injected into system prompt
"""

COMPONENT_PRESETS: dict[str, dict] = {
    "button": {
        "name": "Button",
        "keywords": ["button", "btn", "cta", "action", "кнопк"],
        "context": """Это кнопка (Button). Стандартные паттерны:
- Размеры: xs / sm / md / lg / xl
- Варианты: primary, secondary, ghost, outline, destructive, link
- Состояния: default, hover, active, focus, disabled, loading
- Слоты: leading icon, label, trailing icon, icon-only
- Типичные VARIANT-свойства: Size, Variant, State, Has Icon, Icon Position
Accessibility: role=button (или <button>), tabindex=0, focus-visible ring, WCAG contrast ≥4.5:1 для текста и 3:1 для UI-элементов.
Usage DO: один primary CTA на экран, глагол в тексте ("Сохранить", "Отправить").
Usage DON'T: не использовать кнопку как ссылку для навигации, не перегружать иконками."""
    },

    "input": {
        "name": "Input / Text Field",
        "keywords": ["input", "field", "text field", "textfield", "поле", "инпут", "text input"],
        "context": """Это текстовое поле (Input / Text Field). Стандартные паттерны:
- Состояния: default, focus, filled, error, disabled, read-only
- Варианты: outlined, filled, borderless
- Слоты: label, placeholder, leading icon, trailing icon, helper text, error message, character counter
- Типичные VARIANT-свойства: State, Size, Has Label, Has Icon, Type
- Типы input: text, email, password, search, number, tel, url
Accessibility: <label> привязан через htmlFor или aria-label, aria-describedby для ошибок, aria-invalid=true при ошибке, autocomplete где применимо.
Usage DO: всегда видимый label (не только placeholder), явное сообщение об ошибке.
Usage DON'T: placeholder не заменяет label — он исчезает при вводе."""
    },

    "checkbox": {
        "name": "Checkbox",
        "keywords": ["checkbox", "check box", "чекбокс"],
        "context": """Это чекбокс (Checkbox). Стандартные паттерны:
- Состояния: unchecked, checked, indeterminate, disabled (все 4)
- Размеры: sm / md / lg
- Слоты: checkbox mark, label, helper text
Accessibility: role=checkbox, aria-checked (true/false/mixed для indeterminate), группа чекбоксов — в <fieldset> + <legend>.
Usage DO: для множественного выбора из списка, независимые опции.
Usage DON'T: не использовать как переключатель с немедленным эффектом (для этого Toggle)."""
    },

    "toggle": {
        "name": "Toggle / Switch",
        "keywords": ["toggle", "switch", "switcher", "тоггл", "свич", "переключат"],
        "context": """Это переключатель (Toggle / Switch). Стандартные паттерны:
- Состояния: off, on, disabled-off, disabled-on
- Размеры: sm / md / lg
- Слоты: track, thumb, label (слева или справа)
Accessibility: role=switch, aria-checked=true/false, label через aria-label или видимый текст.
Usage DO: для настроек с немедленным эффектом (вкл/выкл уведомлений, тёмная тема).
Usage DON'T: не путать с Checkbox — Toggle не требует Submit, эффект мгновенный."""
    },

    "modal": {
        "name": "Modal / Dialog",
        "keywords": ["modal", "dialog", "dialogue", "overlay", "popup", "pop-up", "модал", "диалог"],
        "context": """Это модальное окно (Modal / Dialog). Стандартные паттерны:
- Размеры: sm / md / lg / full-screen
- Варианты: info, warning, error, confirmation, form
- Слоты: overlay/backdrop, container, header (title + close button), body, footer (actions)
- Состояния: closed, open, loading
Accessibility: role=dialog, aria-modal=true, aria-labelledby (title), aria-describedby (body), focus trap внутри, ESC закрывает, возврат фокуса на триггер при закрытии.
Usage DO: только для критичных действий требующих подтверждения или изолированных форм.
Usage DON'T: не показывать несколько модалок друг над другом, не блокировать без возможности закрыть."""
    },

    "select": {
        "name": "Select / Dropdown",
        "keywords": ["select", "dropdown", "drop-down", "listbox", "combobox", "селект", "дропдаун"],
        "context": """Это выпадающий список (Select / Dropdown). Стандартные паттерны:
- Варианты: native select, custom dropdown, combobox (с поиском), multi-select
- Состояния: closed, open, selected, disabled, error
- Слоты: trigger (label + value + chevron), dropdown container, option items, search field (опционально), placeholder
Accessibility: role=combobox + role=listbox + role=option, aria-expanded, стрелки ↑↓ для навигации, Enter для выбора, ESC для закрытия.
Usage DO: 4–7 опций для native select, поиск при >7 опций.
Usage DON'T: не использовать для < 3 опций (лучше radio), не прятать важные действия в dropdown."""
    },

    "badge": {
        "name": "Badge / Tag / Chip",
        "keywords": ["badge", "tag", "chip", "label", "pill", "status", "бейдж", "тег", "чип", "статус"],
        "context": """Это Badge / Tag / Chip. Стандартные паттерны:
- Варианты семантики: neutral, success, warning, error, info, brand
- Варианты использования: status badge, tag (filterable), chip (removable)
- Размеры: sm / md / lg
- Слоты: dot/icon, label, remove button (для chip)
Accessibility: по умолчанию не интерактивный (span). Если кликабельный — role=button, tabindex=0. Если removable — кнопка удаления с aria-label="Удалить {name}".
Usage DO: краткий текст (1–3 слова), чёткий цветовой смысл.
Usage DON'T: не использовать для действий (для этого Button), не перегружать страницу бейджами."""
    },

    "card": {
        "name": "Card",
        "keywords": ["card", "tile", "panel", "карточк"],
        "context": """Это карточка (Card). Стандартные паттерны:
- Варианты: flat, elevated, outlined, interactive (clickable)
- Слоты: media (image/video), header, body (content), footer (meta/actions)
- Размеры: sm / md / lg / wide / narrow
- Состояния: default, hover, selected, disabled
Accessibility: если вся карточка кликабельная — один семантический <a> охватывает весь контент, не вкладывать интерактивные элементы внутрь кликабельной карточки.
Usage DO: вертикальная иерархия контента, ограниченная ширина для читаемости.
Usage DON'T: не вкладывать карточки друг в друга без явной необходимости."""
    },

    "avatar": {
        "name": "Avatar",
        "keywords": ["avatar", "user pic", "profile pic", "userpic", "аватар", "юзерпик"],
        "context": """Это аватар пользователя (Avatar). Стандартные паттерны:
- Варианты: image, initials (2 буквы), icon (anonymous), placeholder
- Размеры: xs (16) / sm (24) / md (32) / lg (40) / xl (48) / 2xl (64)
- Форма: circle (по умолчанию), square (для брендов), rounded
- Модификаторы: online indicator, notification badge
Accessibility: <img> с alt="{Имя Пользователя}" или aria-label для non-img реализаций. Декоративные аватары — alt="".
Usage DO: initials как fallback при недоступном изображении.
Usage DON'T: не показывать персональные данные без явного согласия."""
    },

    "tabs": {
        "name": "Tabs",
        "keywords": ["tab", "tabs", "tabbar", "tab bar", "navigation tabs", "таб", "табы", "вкладк"],
        "context": """Это табы (Tabs). Стандартные паттерны:
- Варианты: underline (default), pill, card, vertical
- Состояния таба: default, hover, active/selected, disabled
- Слоты таба: icon (опционально), label, badge/count (опционально), close button (closeable tabs)
- Вариации: scrollable tabs, justified tabs (fill container)
Accessibility: role=tablist на контейнере, role=tab на каждом табе, aria-selected=true для активного, aria-controls → id панели, role=tabpanel на панели, aria-labelledby. Навигация: ← → между табами, Enter/Space для активации.
Usage DO: 2–6 вкладок, видимые label, одинаковый контент-тип в каждой вкладке.
Usage DON'T: не прятать критичный контент за табами, не использовать для навигации между страницами (для этого Nav)."""
    },

    "table": {
        "name": "Table / Data Grid",
        "keywords": ["table", "grid", "data grid", "datagrid", "таблиц", "грид"],
        "context": """Это таблица / Data Grid. Стандартные паттерны:
- Варианты: simple table, sortable, selectable (checkbox), expandable rows, pagination
- Слоты: thead (column headers), tbody (rows), tfoot (summary), pagination controls
- Состояния строки: default, hover, selected, expanded, loading
Accessibility: <table> с <caption> или aria-label, <th scope="col/row">, aria-sort для сортируемых колонок, role=grid для интерактивных. Клавиатурная навигация Tab/Enter/стрелки для grid.
Usage DO: выравнивание числовых данных вправо, текстовых влево.
Usage DON'T: не использовать table для layout, не делать более 7-8 колонок без горизонтального скролла."""
    },

    "tooltip": {
        "name": "Tooltip / Popover",
        "keywords": ["tooltip", "popover", "hint", "тултип", "тул тип", "подсказк"],
        "context": """Это Tooltip / Popover. Стандартные паттерны:
- Tooltip: короткий текст (<80 символов), без интерактивных элементов внутри, показывается по hover/focus
- Popover: богатый контент, может содержать ссылки/кнопки, показывается по клику
- Позиционирование: top, right, bottom, left + auto-flip
- Слоты: trigger, arrow/caret, content
Accessibility: Tooltip — role=tooltip + aria-describedby на триггере. Popover — role=dialog или region, focus trap если сложный контент.
Usage DO: только для дополнительной информации (не обязательной для понимания UI).
Usage DON'T: не скрывать важную информацию только в tooltip (мобильный нет hover)."""
    },
}


def detect_preset(component_name: str) -> str | None:
    """Auto-detect component type from name using keyword matching."""
    name_lower = component_name.lower()
    for key, preset in COMPONENT_PRESETS.items():
        for kw in preset["keywords"]:
            if kw in name_lower:
                return key
    return None


def get_context_for_preset(preset_key: str | None) -> str:
    """Return context string to inject into system prompt, or empty string."""
    if preset_key and preset_key in COMPONENT_PRESETS:
        ctx = COMPONENT_PRESETS[preset_key]["context"]
        return f"\n\nКОНТЕКСТ ПО ТИПУ КОМПОНЕНТА:\n{ctx}"
    return ""


def list_preset_names() -> dict[str, str]:
    """Return {key: name} mapping (legacy)."""
    return {k: v["name"] for k, v in COMPONENT_PRESETS.items()}


def list_presets() -> dict[str, dict]:
    """Return {key: {name, context}} — full preset data for client-side editing."""
    return {k: {"name": v["name"], "context": v["context"]} for k, v in COMPONENT_PRESETS.items()}
