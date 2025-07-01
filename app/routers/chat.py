from fastapi import APIRouter
from .. import schemas
from ..services import llm_service

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

@router.post("/explain", response_model=str)
async def explain_sql_topic(
    request: schemas.ExplanationRequest,
):
    explanation_text = await llm_service.get_llm_explanation(request.topic, request.llm_provider)
    return explanation_text # 直接返回解释文本