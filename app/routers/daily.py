# 作用: 定义与每日一题和排行榜相关的API路由。

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime

from .. import crud, models, schemas
from ..database import get_db, get_practice_db_path
from ..dependencies import get_current_user
from ..services.sql_executor import SQLExecutor

router = APIRouter(
    prefix="/daily",
    tags=["Daily Question & Leaderboard"],
)

POINTS_FOR_DAILY_QUESTION = 10  # 答对每日一题获得的积分


@router.get("/question", response_model=schemas.DailyQuestionPublic)
def get_today_daily_question(db: Session = Depends(get_db)):
    """获取当天的每日一题。"""
    today = datetime.date.today()
    question = crud.get_daily_question_by_date(db, date=today)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="今天的每日一题还没有发布，敬请期待！"
        )
    return question


@router.post("/submit", response_model=schemas.DailyAnswerEvaluationResponse)
def submit_daily_answer(
        request: schemas.DailyAnswerSubmissionRequest,
        db: Session = Depends(get_db),
        practice_db_path: str = Depends(get_practice_db_path),
        current_user: models.User = Depends(get_current_user)
):
    """提交每日一题的答案。"""
    # 【重要修复】使用正确的函数名 check_if_daily_question_is_solved
    is_already_solved = crud.check_if_daily_question_is_solved(db, user_id=current_user.id,
                                                               question_id=request.question_id)
    if is_already_solved:
        return schemas.DailyAnswerEvaluationResponse(
            status="already_solved",
            message="你已经正确回答过这道题了，无需重复提交。"
        )

    # 使用正确的函数获取每日一题的信息
    question = crud.get_daily_question_by_id(db=db, question_id=request.question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到该题目")

    executor = SQLExecutor(practice_db_path)

    # 实时计算正确答案的哈希值
    correct_hash, error = executor.execute_and_get_hash(question.correct_sql)
    if error:
        print(f"DEBUG: Daily question correct SQL failed to execute! SQL: {question.correct_sql}, Error: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="每日一题的正确答案存在问题，请联系管理员。")

    # 执行并比对用户的答案
    is_correct, user_error, _ = executor.execute_and_compare(
        user_sql=request.user_sql,
        correct_result_hash=correct_hash
    )

    # 记录提交历史，无论对错
    crud.create_daily_submission(
        db=db,
        user_id=current_user.id,
        question_id=request.question_id,
        submitted_sql=request.user_sql,
        is_correct=is_correct
    )

    if user_error:
        return schemas.DailyAnswerEvaluationResponse(status="syntax_error", message=f"语法错误: {user_error}")

    if is_correct:
        # 增加积分
        crud.add_points_to_user(db=db, user_id=current_user.id, points_to_add=POINTS_FOR_DAILY_QUESTION)
        return schemas.DailyAnswerEvaluationResponse(status="correct",
                                                     message=f"回答正确！恭喜你获得了 {POINTS_FOR_DAILY_QUESTION} 积分！")
    else:
        return schemas.DailyAnswerEvaluationResponse(status="result_error", message="答案错误，再接再厉！")


@router.get("/leaderboard", response_model=List[schemas.LeaderboardEntry])
def get_leaderboard_endpoint(limit: int = 10, db: Session = Depends(get_db)):
    """获取积分排行榜。"""
    users = crud.get_leaderboard(db, limit=limit)
    # 将数据库用户对象转换为带有名次的Pydantic模型列表
    return [
        schemas.LeaderboardEntry(rank=i + 1, username=user.username, points=user.points)
        for i, user in enumerate(users)
    ]
