# 作用: 定义仅供管理员访问的API路由。

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime
from pydantic import BaseModel

from .. import crud, models, schemas
from ..database import get_db, get_practice_db_path
from ..dependencies import get_current_admin_user
from ..services import llm_service
from ..services.sql_executor import SQLExecutor

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]
)

# --- 每日一题相关 ---
class DailyQuestionAIRequest(BaseModel):
    topics: List[str]
    llm_provider: str = "deepseek"

@router.post("/daily-question/ai-generate", response_model=schemas.LLMGeneratedQuestion)
async def ai_generate_daily_question(
    request: DailyQuestionAIRequest,
    practice_db_path: str = Depends(get_practice_db_path)
):
    """由AI生成每日一题的草稿（问题和SQL）"""
    executor = SQLExecutor(practice_db_path)
    schema = executor.get_db_schema()
    llm_question = await llm_service.generate_question_from_llm(
        topics=request.topics,
        schema=schema,
        llm_provider=request.llm_provider
    )
    # 只是返回草稿，不保存
    return llm_question

@router.post("/daily-question/publish", response_model=schemas.DailyQuestionPublic, status_code=status.HTTP_201_CREATED)
def publish_daily_question(
    question: schemas.DailyQuestionCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    """管理员确认并发布每日一题"""
    existing_question = crud.get_daily_question_by_date(db, date=datetime.date.today())
    if existing_question:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"今天的每日一题已经由 '{existing_question.user.username}' 发布过了。"
        )
    return crud.create_daily_question(db=db, question=question, author_id=admin_user.id)

# --- 用户管理相关 ---
@router.get("/users", response_model=List[schemas.User])
def list_all_users(db: Session = Depends(get_db)):
    """获取所有用户列表"""
    return crud.get_all_users(db)

@router.put("/users/permissions", response_model=schemas.User)
def change_user_permissions(
    permission_data: schemas.UserPermissionUpdate,
    db: Session = Depends(get_db)
):
    """修改指定用户的管理员权限"""
    if permission_data.user_id == 1: # 假设ID为1的用户是超级管理员，不能被修改
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能修改超级管理员的权限。")
    updated_user = crud.update_user_permissions(
        db=db,
        user_id=permission_data.user_id,
        is_admin=permission_data.is_admin
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该用户。")
    return updated_user
