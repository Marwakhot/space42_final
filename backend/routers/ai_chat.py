"""
AI Chat Router - Endpoints for RAG-powered conversations.
Handles candidate queries and onboarding help.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from dependencies import get_current_user
from services.chat_service import process_candidate_query, process_onboarding_query

router = APIRouter(prefix="/ai", tags=["AI Chat"])


# ============ Request/Response Models ============

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[Dict[str, Any]] = []
    context_used: bool = False


# ============ Endpoints ============

@router.post("/chat", response_model=ChatResponse)
async def candidate_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat endpoint for candidate queries.
    Uses RAG to answer questions about jobs, application process, company info.
    
    Example questions:
    - "What positions are available in engineering?"
    - "What skills do I need for the Software Developer role?"
    - "How do I apply for a job?"
    - "What are the benefits at Space42?"
    """
    try:
        result = await process_candidate_query(
            message=request.message,
            conversation_id=request.conversation_id,
            candidate_id=current_user.get("user_id")
        )
        
        return ChatResponse(
            response=result['response'],
            conversation_id=result['conversation_id'],
            sources=result['sources'],
            context_used=result['context_used']
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post("/onboarding", response_model=ChatResponse)
async def onboarding_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat endpoint for new hire onboarding assistance.
    Uses RAG to answer questions about onboarding tasks, team, policies.
    
    Example questions:
    - "What do I need to complete on my first day?"
    - "Who is on my team?"
    - "How do I set up my development environment?"
    - "Where can I find the company policies?"
    """
    try:
        result = await process_onboarding_query(
            message=request.message,
            conversation_id=request.conversation_id,
            candidate_id=current_user.get("user_id")
        )
        
        return ChatResponse(
            response=result['response'],
            conversation_id=result['conversation_id'],
            sources=result['sources'],
            context_used=result['context_used']
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/chat/{conversation_id}/history")
async def get_chat_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get chat history for a conversation.
    """
    from database import get_supabase_client
    supabase = get_supabase_client()
    
    # Verify access
    conv_result = supabase.table('conversations').select("*").eq('id', conversation_id).execute()
    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv = conv_result.data[0]
    if current_user["user_type"] == "candidate" and str(conv['participant_id']) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get messages directly from conversation record
    return {
        "conversation_id": conversation_id,
        "context_type": conv.get('conversation_type'),
        "messages": conv.get('messages', []) or []
    }
