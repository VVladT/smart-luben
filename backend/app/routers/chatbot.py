from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chatbot_service import process_message


router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Consultar al asistente LubenBot",
    description="Envía un mensaje al chatbot y recibe una respuesta basada en los datos de SmartLuben.",
)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    return await process_message(request.message, db)