# 作用: 定义仅供管理员访问的API路由。

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_admin_user
from ..services import llm_service

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]
)

# --- 题库管理 ---

# 【重要修复】将函数声明为 async def
async def background_task_generate_questions(db: Session, request: schemas.BatchGenerateRequest, author_id: int):
    """后台任务：调用LLM生成题目并存入数据库"""
    print(f"后台任务开始：为用户 {author_id} 生成 {request.count} 道关于 '{request.topics}' 的题目。")
    for i in range(request.count):
        print(f"正在生成第 {i+1}/{request.count} 道题...")
        # 现在可以在这里安全地使用 await
        question_data = await llm_service.generate_question_from_llm(
            topics=request.topics,
            llm_provider=request.llm_provider
        )
        if "error" not in question_data.correct_sql:
            # 注意：crud 操作是同步的，在后台任务的异步函数中调用是可行的，
            # 但在高性能场景下需注意不要长时间阻塞事件循环。
            crud.create_question_draft(
                db=db,
                question_data=question_data,
                topics=",".join(request.topics),
                author_id=author_id
            )
    print("后台任务完成。")


@router.post("/questions/batch-generate")
async def batch_generate_questions(
    request: schemas.BatchGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    """
    管理员请求批量生成题目。该请求会立即返回，并在后台执行生成任务。
    """
    background_tasks.add_task(background_task_generate_questions, db, request, admin_user.id)
    return {"message": f"已开始在后台生成 {request.count} 道题目，请稍后在审核列表查看。"}


@router.get("/questions/drafts", response_model=List[schemas.QuestionAdminView])
def get_all_draft_questions(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """获取待审核的题目草稿列表"""
    return crud.get_draft_questions(db, skip=skip, limit=limit)


@router.put("/questions/{question_id}", response_model=schemas.QuestionAdminView)
def update_draft_question(
    question_id: int,
    question_update: schemas.QuestionUpdate,
    db: Session = Depends(get_db)
):
    """管理员更新一个题目草稿的内容"""
    updated_question = crud.update_question(db, question_id, question_update)
    if not updated_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该题目")
    return updated_question


@router.post("/questions/{question_id}/publish", response_model=schemas.QuestionAdminView)
def publish_a_question(
    question_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    """管理员审核通过并发布一个题目"""
    published_question = crud.publish_question(db, question_id, admin_user.id)
    if not published_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该题目或题目状态不正确")
    return published_question


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
