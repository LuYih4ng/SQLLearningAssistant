# 作用: 定义与个性化每日一题和排行榜相关的API路由。

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime

from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user
from ..services import sql_executor

router = APIRouter(
    prefix="/daily",
    tags=["Personalized Daily"],
)

POINTS_FOR_DAILY_QUESTION = 10


@router.get("/get-personalized-question", response_model=schemas.QuestionPublicView)
def get_personalized_daily_question(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """
    为用户推荐一道个性化的“每日”题目。
    """
    weakest_topics = crud.get_user_weakest_topics(db, user_id=current_user.id)
    question = crud.get_random_published_question(db, topics=weakest_topics)

    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库中暂时没有适合你的题目，试试其他功能吧！")

    return schemas.QuestionPublicView(
        question_id=question.id,
        title=question.title,
        question_text=question.question_text,
        setup_sql=question.setup_sql,
        topics=question.topics
    )


@router.post("/submit-personalized-answer", response_model=schemas.DailyAnswerEvaluationResponse)
def submit_personalized_answer(
        request: schemas.TestAnswerSubmissionRequest,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """用户提交个性化题目的答案"""
    question = crud.get_question_by_id(db, request.question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到该题目")

    evaluation = sql_executor.evaluate_sql_in_isolation(
        setup_sql=question.setup_sql,
        correct_sql=question.correct_sql,
        user_sql=request.user_sql
    )

    is_correct = evaluation.get("is_correct", False)

    # 如果回答错误，直接返回结果
    if not is_correct:
        if evaluation["status"] == "syntax_error":
            return schemas.DailyAnswerEvaluationResponse(status="syntax_error",
                                                         message=f"语法错误: {evaluation['error']}")
        else:
            return schemas.DailyAnswerEvaluationResponse(status="result_error", message="答案错误，再接再厉！")

    # --- 【核心修改】如果回答正确，执行以下积分逻辑 ---

    # 1. 检查用户今天是否已经获得过每日积分
    has_received_points = crud.has_user_received_daily_points_today(db, user_id=current_user.id)

    if has_received_points:
        return schemas.DailyAnswerEvaluationResponse(status="correct",
                                                     message="回答正确！不过今天已经获得过每日积分了哦。")
    else:
        # 2. 如果今天没得过分，现在就给分
        crud.add_points_to_user(db, current_user.id, POINTS_FOR_DAILY_QUESTION)

        # 3. 为了“标记”今天已得分，我们需要在 daily_submissions 表中创建一条记录。
        #    为此，我们找到或创建一个“今天”的 DailyQuestion 锚点记录。
        today_daily_entry = crud.get_daily_question_by_date(db, date=datetime.date.today())
        if not today_daily_entry:
            # 如果不存在，就用当前用户答对的这道题作为今天的“锚点”
            today_daily_entry = crud.create_daily_question(db, question_id=question.id)

        # 4. 创建提交记录
        crud.create_daily_submission(db, current_user.id, today_daily_entry.id, request.user_sql, is_correct)

        return schemas.DailyAnswerEvaluationResponse(status="correct",
                                                     message=f"回答正确！恭喜你获得了 {POINTS_FOR_DAILY_QUESTION} 积分！")


@router.get("/leaderboard", response_model=List[schemas.LeaderboardEntry])
def get_leaderboard_endpoint(limit: int = 10, db: Session = Depends(get_db)):
    """获取积分排行榜。"""
    users = crud.get_leaderboard(db, limit=limit)
    return [
        schemas.LeaderboardEntry(rank=i + 1, username=user.username, points=user.points)
        for i, user in enumerate(users)
    ]
