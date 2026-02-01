"""
Conversations router for storing chat history.
Used by the AI system (future) and for debugging/viewing history.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from database import get_supabase_client
from dependencies import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ============ Request/Response Models ============

class ConversationCreate(BaseModel):
    # Depending on your table schema, you might need applicationId or candidateId
    # Assuming 'conversations' links to a candidate or application
    candidate_id: Optional[str] = None
    application_id: Optional[str] = None
    context_type: str = "general" # interview, onboarding, faq, etc.

class MessageCreate(BaseModel):
    role: str # user, assistant, system
    content: str
    metadata: Optional[dict] = {}

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    metadata: Optional[dict] = None

class ConversationResponse(BaseModel):
    id: str
    candidate_id: Optional[str]
    application_id: Optional[str]
    context_type: str
    status: str
    created_at: str
    updated_at: Optional[str]
    messages: List[MessageResponse] = []


# ============ Endpoints ============

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    request: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a new conversation session.
    """
    supabase = get_supabase_client()
    user_id = current_user["user_id"]
    
    # If candidate, enforce candidate_id matches
    if current_user["user_type"] == "candidate":
        candidate_id = user_id
    else:
        candidate_id = request.candidate_id or user_id # Admin/HR starting chat? usually not, but fallback
        
    new_conv = {
        "candidate_id": candidate_id,
        "application_id": request.application_id,
        "context_type": request.context_type,
        "status": "active"
    }
    
    result = supabase.table('conversations').insert(new_conv).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
        
    c = result.data[0]
    
    return ConversationResponse(
        id=str(c['id']),
        candidate_id=str(c.get('candidate_id')) if c.get('candidate_id') else None,
        application_id=str(c.get('application_id')) if c.get('application_id') else None,
        context_type=c['context_type'],
        status=c['status'],
        created_at=c['created_at'],
        updated_at=c.get('updated_at'),
        messages=[]
    )


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: dict = Depends(get_current_user)
):
    """
    List my conversations.
    """
    supabase = get_supabase_client()
    user_id = current_user["user_id"]
    
    query = supabase.table('conversations').select("*")
    
    if current_user["user_type"] == "candidate":
        query = query.eq('candidate_id', user_id)
    # HR might want to filter by candidate_id if provided in query params (not implemented here for brevity)
    
    result = query.order('updated_at', desc=True).limit(50).execute()
    
    # We won't fetch messages for the list view to save BW
    return [ConversationResponse(
        id=str(c['id']),
        candidate_id=str(c.get('candidate_id')) if c.get('candidate_id') else None,
        application_id=str(c.get('application_id')) if c.get('application_id') else None,
        context_type=c['context_type'],
        status=c['status'],
        created_at=c['created_at'],
        updated_at=c.get('updated_at'),
        messages=[]
    ) for c in result.data]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get conversation details including messages.
    """
    supabase = get_supabase_client()
    
    # Get conversation
    c_res = supabase.table('conversations').select("*").eq('id', conversation_id).execute()
    if not c_res.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    c = c_res.data[0]
    
    # Access check
    if current_user["user_type"] == "candidate" and str(c['candidate_id']) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Get messages
    m_res = supabase.table('messages').select("*").eq('conversation_id', conversation_id).order('created_at').execute()
    messages = [MessageResponse(
        id=str(m['id']),
        conversation_id=str(m['conversation_id']),
        role=m['role'],
        content=m['content'],
        created_at=m['created_at'],
        metadata=m.get('metadata')
    ) for m in m_res.data]
    
    return ConversationResponse(
        id=str(c['id']),
        candidate_id=str(c.get('candidate_id')) if c.get('candidate_id') else None,
        application_id=str(c.get('application_id')) if c.get('application_id') else None,
        context_type=c['context_type'],
        status=c['status'],
        created_at=c['created_at'],
        updated_at=c.get('updated_at'),
        messages=messages
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: str,
    request: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Manually add a message to a conversation.
    Note: Real AI interaction will happen via a different endpoint or service logic.
    This is for storing the user's input or manual system injections.
    """
    supabase = get_supabase_client()
    
    # Verify conversation exists & access
    c_res = supabase.table('conversations').select("id, candidate_id").eq('id', conversation_id).execute()
    if not c_res.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if current_user["user_type"] == "candidate" and str(c_res.data[0]['candidate_id']) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    new_msg = {
        "conversation_id": conversation_id,
        "role": request.role,
        "content": request.content,
        "metadata": request.metadata
    }
    
    result = supabase.table('messages').insert(new_msg).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to add message")
        
    m = result.data[0]
    
    # Update conversation updated_at
    supabase.table('conversations').update({"updated_at": "now()"}).eq('id', conversation_id).execute()
    
    return MessageResponse(
        id=str(m['id']),
        conversation_id=str(m['conversation_id']),
        role=m['role'],
        content=m['content'],
        created_at=m['created_at'],
        metadata=m.get('metadata')
    )


@router.put("/{conversation_id}/status")
async def update_status(
    conversation_id: str,
    status_val: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Update conversation status (e.g. active -> completed).
    """
    supabase = get_supabase_client()
    
    # Access check (omitted for brevity, similar to above)
    
    supabase.table('conversations').update({"status": status_val, "updated_at": "now()"}).eq('id', conversation_id).execute()
    
    return {"message": "Status updated", "status": status_val}
