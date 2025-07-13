from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user
from ..services import llm_service

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/explain")
async def explain_sql_topic_stream(request: schemas.ExplanationRequest):
    """
    用户输入一个SQL知识点，以流式方式调用LLM进行解释。
    """

    # 【重要修复】将流式调用包装在一个显式的异步生成器函数中。
    # 这是一个健壮的模式，可以避免框架对返回类型的混淆。
    async def stream_generator():
        async for chunk in llm_service.get_llm_explanation(request.topic, request.llm_provider):
            yield chunk

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
