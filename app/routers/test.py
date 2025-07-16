# 作用: 定义用户进行SQL能力测试的相关API路由。

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import re

from .. import crud, schemas, models
from ..database import get_db
from ..dependencies import get_current_user
from ..services import llm_service, sql_executor

router = APIRouter(
    prefix="/test",
    tags=["SQL Testing"],
    dependencies=[Depends(get_current_user)]
)

# 【重要修改】这个函数不再需要，我们将直接返回完整的建表语句
# def _extract_create_table(setup_sql: str) -> str:
#     """从完整的setup_sql中只提取CREATE TABLE语句部分"""
#     create_statements = re.findall(r'CREATE TABLE.*?;', setup_sql, re.IGNORECASE | re.DOTALL)
#     return "\n".join(create_statements)

@router.post("/get-question", response_model=schemas.QuestionPublicView)
def get_a_question_for_test(
    request: schemas.GetQuestionRequest,
    db: Session = Depends(get_db)
):
    """用户根据知识点随机抽取一道已发布的题目"""
    question = crud.get_random_published_question(db, topics=request.topics)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库中没有找到符合条件的题目。")

    return schemas.QuestionPublicView(
        question_id=question.id,
        title=question.title,
        question_text=question.question_text,
        # 【重要修改】直接返回完整的 setup_sql
        setup_sql=question.setup_sql,
        topics=question.topics
    )


@router.post("/submit-answer", response_model=schemas.TestAnswerEvaluationResponse)
async def submit_test_answer(
    request: schemas.TestAnswerSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """用户提交能力测试的答案并获取评测结果"""
    question = crud.get_question_by_id(db, request.question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到该题目")

    evaluation = sql_executor.evaluate_sql_in_isolation(
        setup_sql=question.setup_sql,
        correct_sql=question.correct_sql,
        user_sql=request.user_sql
    )

    crud.create_test_submission(
        db=db,
        user_id=current_user.id,
        question_id=question.id,
        is_correct=evaluation.get("is_correct", False)
    )

    evaluation_status = evaluation["status"]
    message = ""
    analysis = None

    if evaluation_status == "syntax_error":
        message = "你的SQL语句存在语法错误，看看AI导师的分析吧！"
        analysis = await llm_service.analyze_syntax_error(
            user_sql=request.user_sql,
            db_error=evaluation["error"],
            llm_provider="deepseek"
        )
    elif evaluation_status == "result_error":
        message = "语法没问题，但结果不对哦。看看AI导师对你的逻辑分析吧！"
        analysis = await llm_service.analyze_result_error(
            question=question.question_text,
            user_sql=request.user_sql,
            correct_sql=question.correct_sql,
            llm_provider="deepseek"
        )
    elif evaluation_status == "correct":
        message = "太棒了，完全正确！来看看AI导师有没有更好的建议吧！"
        analysis = await llm_service.analyze_for_improvement(
            question=question.question_text,
            user_sql=request.user_sql,
            correct_sql=question.correct_sql,
            llm_provider="deepseek"
        )
    else: # setup_error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=evaluation["error"])

    return schemas.TestAnswerEvaluationResponse(
        status=evaluation_status,
        message=message,
        analysis=analysis
    )
