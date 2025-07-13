# 作用: 定义Pydantic模型，用于API的数据校验和序列化。

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Any
import datetime


# --- User & Auth Schemas ---
class UserCreate(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str
    is_admin: bool
    points: int

    class Config:
        from_attributes = True


# 【重要修复】重新添加了用于修改密码的模型
class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str


class UserPermissionUpdate(BaseModel):
    user_id: int
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# --- Chat Schema ---
class ExplanationRequest(BaseModel):
    topic: str
    llm_provider: Literal["deepseek", "qwen"]


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
class LLMGeneratedQuestionData(BaseModel):
    question: str
    setup_sql: str
    correct_sql: str


class BatchGenerateRequest(BaseModel):
    topics: List[str]
    count: int = Field(gt=0, le=10)
    llm_provider: Literal["deepseek", "qwen"] = "deepseek"

# 【重要修复】为抽题功能新增一个专门的请求模型
class GetQuestionRequest(BaseModel):
    topics: List[str]

class QuestionUpdate(BaseModel):
    title: str
    question_text: str
    setup_sql: str
    correct_sql: str
    topics: str


class QuestionAdminView(QuestionUpdate):
    id: int
    status: str
    author_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class QuestionPublicView(BaseModel):
    question_id: int
    title: str
    question_text: str
    setup_sql: str
    topics: str

    class Config:
        from_attributes = True


class TestAnswerSubmissionRequest(BaseModel):
    question_id: int
    user_sql: str


class TestAnswerEvaluationResponse(BaseModel):
    status: Literal["correct", "syntax_error", "result_error"]
    message: str
    analysis: Optional[str] = None


# --- Daily Question & Leaderboard Schemas ---
class DailyQuestionPublishRequest(BaseModel):
    question_id: int


class DailyQuestionPublic(BaseModel):
    id: int
    question_id: int
    title: str
    question_text: str
    question_date: datetime.date


class DailyAnswerSubmissionRequest(BaseModel):
    daily_question_id: int
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
