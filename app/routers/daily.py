from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime

from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user, get_current_admin_user
from ..services import sql_executor

router = APIRouter(
    prefix="/daily",
    tags=["Daily Question & Leaderboard"],
)

POINTS_FOR_DAILY_QUESTION = 10


@router.post("/publish", response_model=schemas.DailyQuestionPublic, dependencies=[Depends(get_current_admin_user)])
def publish_daily_question(
        request: schemas.DailyQuestionPublishRequest,
        db: Session = Depends(get_db)
):
    """管理员从题库中指定一道题作为今天的每日一题"""
    # 检查题目是否存在且已发布
    question = crud.get_question_by_id(db, request.question_id)
    if not question or question.status != 'published':
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定的题目不存在或未发布。")

    # 检查今天是否已经发布过
    existing_daily = crud.get_daily_question_by_date(db, date=datetime.date.today())
    if existing_daily:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="今天的每日一题已经发布过了。")

    daily_entry = crud.create_daily_question(db, question_id=request.question_id)
    return schemas.DailyQuestionPublic(
        id=daily_entry.id,
        question_id=question.id,
        title=question.title,
        question_text=question.question_text,
        question_date=daily_entry.question_date
    )


@router.get("/question", response_model=schemas.DailyQuestionPublic)
def get_today_daily_question(db: Session = Depends(get_db)):
    """获取当天的每日一题。"""
    daily_entry = crud.get_daily_question_by_date(db, date=datetime.date.today())
    if not daily_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="今天的每日一题还没发布呢！")

    question = daily_entry.question
    return schemas.DailyQuestionPublic(
        id=daily_entry.id,
        question_id=question.id,
        title=question.title,
        question_text=question.question_text,
        question_date=daily_entry.question_date
    )


@router.post("/submit", response_model=schemas.DailyAnswerEvaluationResponse)
def submit_daily_answer(
        request: schemas.DailyAnswerSubmissionRequest,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """用户提交每日一题的答案。"""
    is_solved = crud.check_if_daily_question_is_solved(db, user_id=current_user.id,
                                                       daily_question_id=request.daily_question_id)
    if is_solved:
        return schemas.DailyAnswerEvaluationResponse(status="already_solved",
                                                     message="你已正确回答过此题，无需重复提交。")

    daily_entry = db.query(models.DailyQuestion).filter(models.DailyQuestion.id == request.daily_question_id).first()
    if not daily_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到该每日一题。")

    question = daily_entry.question
    evaluation = sql_executor.evaluate_sql_in_isolation(
        setup_sql=question.setup_sql,
        correct_sql=question.correct_sql,
        user_sql=request.user_sql
    )

    is_correct = evaluation["is_correct"]
    crud.create_daily_submission(db, current_user.id, request.daily_question_id, request.user_sql, is_correct)

    if evaluation["status"] == "syntax_error":
        return schemas.DailyAnswerEvaluationResponse(status="syntax_error", message=f"语法错误: {evaluation['error']}")

    if is_correct:
        crud.add_points_to_user(db, current_user.id, POINTS_FOR_DAILY_QUESTION)
        return schemas.DailyAnswerEvaluationResponse(status="correct",
                                                     message=f"回答正确！获得 {POINTS_FOR_DAILY_QUESTION} 积分！")
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
