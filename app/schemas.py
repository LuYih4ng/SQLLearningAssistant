# 作用: 定义Pydantic模型，用于API的数据校验和序列化。

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Any
import datetime


# --- User Schemas ---
class UserCreate(BaseModel):
    username: str
    password: str


# 增加了is_admin和points字段，用于在管理员界面显示
class User(BaseModel):
    id: int
    username: str
    is_admin: bool
    points: int
    class Config:
        from_attributes = True

class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str

# 新增: 用于管理员修改用户权限的请求体
class UserPermissionUpdate(BaseModel):
    user_id: int
    is_admin: bool

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# --- Chat Schemas (已修正) ---
class ExplanationRequest(BaseModel):
    topic: str
    llm_provider: Literal["deepseek", "qwen"]


class ExplanationResponse(BaseModel):
    answer: str


# 【重要修复】重新添加了之前遗漏的聊天记录模型
class ChatHistoryBase(BaseModel):
    request_message: str
    response_message: str
    llm_provider: str


class ChatHistoryCreate(ChatHistoryBase):
    pass


class ChatHistory(ChatHistoryBase):
    id: int
    user_id: int
    timestamp: datetime.datetime

    class Config:
        from_attributes = True


# --- Question & Test Schemas ---
class QuestionGenerationRequest(BaseModel):
    topics: List[str]
    llm_provider: Literal["deepseek", "qwen"]


class QuestionGenerationResponse(BaseModel):
    question_id: int
    question_text: str


class LLMGeneratedQuestion(BaseModel):
    question: str
    sql: str


class AnswerSubmissionRequest(BaseModel):
    question_id: int
    user_sql: str
    llm_provider: Literal["deepseek", "qwen"] = "deepseek"


class AnswerEvaluationResponse(BaseModel):
    status: Literal["correct", "syntax_error", "result_error"]
    message: str
    analysis: Optional[str] = None
    user_result: Optional[List[Any]] = None
    correct_result: Optional[List[Any]] = None


# --- Daily Question & Leaderboard Schemas ---
class DailyQuestionCreate(BaseModel):
    title: str = Field(..., max_length=100)
    question_text: str
    correct_sql: str


class DailyQuestionPublic(BaseModel):
    id: int
    title: str
    question_text: str
    question_date: datetime.date

    class Config:
        from_attributes = True


class DailyAnswerSubmissionRequest(BaseModel):
    question_id: int
    user_sql: str


class DailyAnswerEvaluationResponse(BaseModel):
    status: Literal["correct", "syntax_error", "result_error", "already_solved"]
    message: str


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    points: int

    class Config:
        from_attributes = True
