# 作用: 定义与SQL题目生成、测试相关的API路由。

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json # 新增导入

from .. import crud, models, schemas
from ..database import get_db, get_practice_db_path
from ..dependencies import get_current_user
from ..services import llm_service
from ..services.sql_executor import SQLExecutor, _execute_sql

router = APIRouter(
    prefix="/test",
    tags=["SQL Testing"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/schema", response_model=str)
def get_practice_database_schema(
    practice_db_path: str = Depends(get_practice_db_path)
):
    """
    获取练习数据库的表结构，以便在前端展示。
    """
    executor = SQLExecutor(practice_db_path)
    schema = executor.get_db_schema()
    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="无法找到或读取练习数据库的表结构。"
        )
    return schema


@router.post("/generate-question", response_model=schemas.QuestionGenerationResponse)
async def generate_sql_question(
        request: schemas.QuestionGenerationRequest,
        db: Session = Depends(get_db),
        practice_db_path: str = Depends(get_practice_db_path),
        current_user: models.User = Depends(get_current_user)
):
    """
    1. 从LLM获取题目和正确SQL。
    2. 执行正确SQL，计算结果哈希。
    3. 将题目信息存入数据库。
    4. 返回题目ID和问题描述给用户。
    """
    executor = SQLExecutor(practice_db_path)
    schema = executor.get_db_schema()

    # 1. 从LLM获取题目
    llm_question = await llm_service.generate_question_from_llm(
        topics=request.topics,
        schema=schema,
        llm_provider=request.llm_provider
    )

    # 2. 执行正确SQL，获取结果哈希
    correct_hash, error = executor.execute_and_get_hash(llm_question.sql)
    if error:
        # 如果LLM生成的SQL本身就有问题，抛出异常
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM生成的SQL无法执行: {error}"
        )

    # 3. 将题目信息存入数据库
    db_question = crud.create_generated_question(
        db=db,
        question_text=llm_question.question,
        correct_sql=llm_question.sql,
        correct_result_hash=correct_hash,
        topics=",".join(request.topics),
        user_id=current_user.id
    )

    # 4. 返回
    return schemas.QuestionGenerationResponse(
        question_id=db_question.id,
        question_text=db_question.question_text
    )


@router.post("/submit-answer", response_model=schemas.AnswerEvaluationResponse)
async def submit_sql_answer(
        request: schemas.AnswerSubmissionRequest,
        db: Session = Depends(get_db),
        practice_db_path: str = Depends(get_practice_db_path),
):
    """
    1. 根据question_id获取题目信息。
    2. 执行用户的SQL并比对结果。
    3. 根据比对结果（正确、语法错误、结果错误）调用LLM进行分析。
    4. 返回最终的评测报告。
    """
    db_question = crud.get_question_by_id(db, request.question_id)
    if not db_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到该题目")

    executor = SQLExecutor(practice_db_path)

    # --- 新增调试代码 ---
    # 在比对前，我们先获取并打印正确答案的原始结果
    correct_result, _ = _execute_sql(practice_db_path, db_question.correct_sql)
    print("\n--- DEBUG: Result Comparison ---")
    print("Correct Result:")
    print(json.dumps(correct_result, indent=2, ensure_ascii=False))

    is_correct, error, user_result = executor.execute_and_compare(
        user_sql=request.user_sql,
        correct_result_hash=db_question.correct_result_hash
    )

    print("\nUser Result:")
    print(json.dumps(user_result, indent=2, ensure_ascii=False))
    print("--------------------------------\n")
    # --- 调试代码结束 ---

    if error:
        analysis = await llm_service.analyze_syntax_error(
            user_sql=request.user_sql,
            db_error=error,
            llm_provider=request.llm_provider
        )
        return schemas.AnswerEvaluationResponse(
            status="syntax_error",
            message="你的SQL语句存在语法错误，看看AI导师的分析吧！",
            analysis=analysis
        )

    if is_correct:
        return schemas.AnswerEvaluationResponse(
            status="correct",
            message="太棒了，完全正确！你真是个SQL小天才！"
        )
    else:
        analysis = await llm_service.analyze_result_error(
            question=db_question.question_text,
            user_sql=request.user_sql,
            correct_sql=db_question.correct_sql,
            llm_provider=request.llm_provider
        )
        return schemas.AnswerEvaluationResponse(
            status="result_error",
            message="语法没问题，但结果不对哦。看看AI导师对你的逻辑分析吧！",
            analysis=analysis,
            user_result=user_result
        )
