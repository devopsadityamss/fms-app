# backend/app/api/farmer/chat_advisory.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.chat_advisory_service import (
    answer_query,
    supported_intents,
    suggested_questions
)

router = APIRouter()

class ChatAskRequest(BaseModel):
    query: str
    unit_id: Optional[int] = None
    crop: Optional[str] = None
    stage: Optional[str] = None

@router.post("/chat-advisory/ask")
def api_chat_ask(req: ChatAskRequest):
    """
    Ask a free-text question. Example payload:
    {
      "query": "Leaves have white powdery spots, what is it?",
      "unit_id": 123,
      "crop": "rice",
      "stage": "flowering"
    }
    """
    if not req.query or len(req.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="empty_query")
    res = answer_query(req.query.strip(), unit_id=req.unit_id, crop=req.crop, stage=req.stage)
    return res

@router.get("/chat-advisory/intents")
def api_intents():
    return {"intents": supported_intents()}

@router.get("/chat-advisory/suggested-questions")
def api_suggested_questions():
    return {"questions": suggested_questions()}
