from pydantic import BaseModel, Field
from typing import Literal

# --- Chat Schemas ---
class ExplanationRequest(BaseModel):
    topic: str
    llm_provider: Literal["deepseek", "qwen"]