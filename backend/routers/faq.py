"""
FAQ router for managing company knowledge base.
Used by HR/Admins to maintain content for the RAG system.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from database import get_supabase_client
from dependencies import get_current_user, require_hr

router = APIRouter(prefix="/faq", tags=["FAQ"])


# ============ Request/Response Models ============

class FAQCreate(BaseModel):
    category: str
    question: str
    answer: str
    tags: Optional[List[str]] = []
    is_public: bool = True

class FAQUpdate(BaseModel):
    category: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None

class FAQResponse(BaseModel):
    id: str
    category: str
    question: str
    answer: str
    tags: List[str]
    is_public: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None


# ============ Endpoints ============

@router.get("", response_model=List[FAQResponse])
async def list_faqs(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search term"),
    current_user: dict = Depends(get_current_user)
):
    """
    List FAQs.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('faq_content').select("*")
    
    # If candidate, only show public
    if current_user["user_type"] == "candidate":
        query = query.eq('is_public', True)
    
    if category:
        query = query.eq('category', category)
        
    if search:
        # Simple text search on question/answer
        query = query.or_(f"question.ilike.%{search}%,answer.ilike.%{search}%")
    
    result = query.order('category').execute()
    
    return [FAQResponse(
        id=str(f['id']),
        category=f['category'],
        question=f['question'],
        answer=f['answer'],
        tags=f.get('tags', []),
        is_public=f.get('is_public', True),
        created_at=f.get('created_at'),
        updated_at=f.get('updated_at'),
        created_by=str(f['created_by']) if f.get('created_by') else None
    ) for f in result.data]


@router.get("/{faq_id}", response_model=FAQResponse)
async def get_faq(
    faq_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get FAQ details.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('faq_content').select("*").eq('id', faq_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    f = result.data[0]
    
    # Access check
    if current_user["user_type"] == "candidate" and not f['is_public']:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return FAQResponse(
        id=str(f['id']),
        category=f['category'],
        question=f['question'],
        answer=f['answer'],
        tags=f.get('tags', []),
        is_public=f.get('is_public', True),
        created_at=f.get('created_at'),
        updated_at=f.get('updated_at'),
        created_by=str(f['created_by']) if f.get('created_by') else None
    )


@router.post("", response_model=FAQResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    request: FAQCreate,
    current_user: dict = Depends(require_hr)
):
    """
    Create a new FAQ. HR/Admin only.
    """
    supabase = get_supabase_client()
    
    new_faq = {
        "category": request.category,
        "question": request.question,
        "answer": request.answer,
        "tags": request.tags,
        "is_public": request.is_public,
        "created_by": current_user["user_id"]
    }
    
    result = supabase.table('faq_content').insert(new_faq).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create FAQ"
        )
    
    f = result.data[0]
    
    return FAQResponse(
        id=str(f['id']),
        category=f['category'],
        question=f['question'],
        answer=f['answer'],
        tags=f.get('tags', []),
        is_public=f.get('is_public', True),
        created_at=f.get('created_at'),
        updated_at=f.get('updated_at'),
        created_by=str(f['created_by']) if f.get('created_by') else None
    )


@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: str,
    request: FAQUpdate,
    current_user: dict = Depends(require_hr)
):
    """
    Update FAQ. HR/Admin only.
    """
    supabase = get_supabase_client()
    
    existing = supabase.table('faq_content').select("id").eq('id', faq_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
        
    update_data = {"updated_at": "now()"}
    if request.category is not None: update_data["category"] = request.category
    if request.question is not None: update_data["question"] = request.question
    if request.answer is not None: update_data["answer"] = request.answer
    if request.tags is not None: update_data["tags"] = request.tags
    if request.is_public is not None: update_data["is_public"] = request.is_public
    
    result = supabase.table('faq_content').update(update_data).eq('id', faq_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update FAQ"
        )
    
    f = result.data[0]
    
    return FAQResponse(
        id=str(f['id']),
        category=f['category'],
        question=f['question'],
        answer=f['answer'],
        tags=f.get('tags', []),
        is_public=f.get('is_public', True),
        created_at=f.get('created_at'),
        updated_at=f.get('updated_at'),
        created_by=str(f['created_by']) if f.get('created_by') else None
    )


@router.delete("/{faq_id}")
async def delete_faq(
    faq_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Delete FAQ. HR/Admin only.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('faq_content').delete().eq('id', faq_id).execute()
    
    # Supabase delete returns deleted row in newer versions, or empty in older
    # We'll just assume success if no error raised
    
    return {"message": "FAQ deleted", "id": faq_id}
