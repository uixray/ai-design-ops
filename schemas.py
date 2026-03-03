from typing import List, Union, Any, Optional
from pydantic import BaseModel, Field

# Входные данные
class Message(BaseModel):
    role: str
    content: Union[str, List[Any]]

class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = "orchestrator"
    stream: Optional[bool] = False 

# Выходные данные (Структура ответа Дирижера)
class ActionItem(BaseModel):
    agent: str = Field(..., description="ID агента")
    instruction: str = Field(..., description="Инструкция")
    # Tool-based actions (v2): если задан tool — выполняется инструмент, не LLM
    tool: Optional[str] = Field(None, description="Имя инструмента (vault_write, figma_get_node)")
    tool_args: Optional[dict] = Field(None, description="Аргументы инструмента")

class OrchestratorPlan(BaseModel):
    status: str = Field(..., pattern="^(proposal|execution)$")
    reply_text: str
    actions: List[ActionItem] = []