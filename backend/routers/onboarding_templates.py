"""
Onboarding Templates router for HR to manage onboarding checklists.
Also handles starting onboarding for candidates (assigning a template).
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from database import get_supabase_client
from dependencies import get_current_user, require_hr

router = APIRouter(prefix="", tags=["Onboarding Templates"]) 
# Note: Prefix is empty here because we need both /onboarding-templates and /onboarding(POST)
# We will define paths explicitly.


# ============ Request/Response Models ============

class OnboardingItem(BaseModel):
    title: str
    description: Optional[str] = None
    required: bool = True
    resource_link: Optional[str] = None
    estimated_hours: Optional[float] = None

class TemplateCreate(BaseModel):
    title: str
    role_types: List[str]
    items: List[OnboardingItem]
    is_active: bool = True

class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    role_types: Optional[List[str]] = None
    items: Optional[List[OnboardingItem]] = None
    is_active: Optional[bool] = None

class TemplateResponse(BaseModel):
    id: str
    title: str
    role_types: List[str]
    items: List[Dict[str, Any]]
    is_active: bool
    created_at: Optional[str] = None
    created_by: Optional[str] = None

class StartOnboardingRequest(BaseModel):
    candidate_id: str
    application_id: str
    template_id: str
    start_date: str
    expected_completion_date: Optional[str] = None
    manager_id: Optional[str] = None

class StartOnboardingResponse(BaseModel):
    id: str
    candidate_id: str
    status: str
    start_date: str


# ============ Endpoints ============

@router.get("/onboarding-templates", response_model=List[TemplateResponse])
async def list_templates(
    role_type: Optional[str] = None,
    current_user: dict = Depends(require_hr)
):
    """
    List onboarding templates.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('onboarding_templates').select("*")
    
    if role_type:
        query = query.contains('role_types', [role_type])
    
    result = query.order('created_at', desc=True).execute()
    
    return [TemplateResponse(
        id=str(t['id']),
        title=t['title'],
        role_types=t['role_types'],
        items=t['items'],
        is_active=t.get('is_active', True),
        created_at=t.get('created_at'),
        created_by=str(t['created_by']) if t.get('created_by') else None
    ) for t in result.data]


@router.post("/onboarding-templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: TemplateCreate,
    current_user: dict = Depends(require_hr)
):
    """
    Create a new onboarding template.
    """
    supabase = get_supabase_client()
    hr_id = current_user["user_id"]
    
    # Convert items to list of dicts for JSON storage
    items_json = [item.dict() for item in request.items]
    
    new_template = {
        "title": request.title,
        "role_types": request.role_types,
        "items": items_json,
        "is_active": request.is_active,
        "created_by": hr_id
    }
    
    result = supabase.table('onboarding_templates').insert(new_template).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )
    
    t = result.data[0]
    
    return TemplateResponse(
        id=str(t['id']),
        title=t['title'],
        role_types=t['role_types'],
        items=t['items'],
        is_active=t.get('is_active', True),
        created_at=t.get('created_at'),
        created_by=str(t['created_by']) if t.get('created_by') else None
    )


@router.get("/onboarding-templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Get template details.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('onboarding_templates').select("*").eq('id', template_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    t = result.data[0]
    
    return TemplateResponse(
        id=str(t['id']),
        title=t['title'],
        role_types=t['role_types'],
        items=t['items'],
        is_active=t.get('is_active', True),
        created_at=t.get('created_at'),
        created_by=str(t['created_by']) if t.get('created_by') else None
    )


@router.put("/onboarding-templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: TemplateUpdate,
    current_user: dict = Depends(require_hr)
):
    """
    Update an onboarding template.
    """
    supabase = get_supabase_client()
    
    # Check if exists
    existing = supabase.table('onboarding_templates').select("id").eq('id', template_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    update_data = {}
    if request.title is not None:
        update_data["title"] = request.title
    if request.role_types is not None:
        update_data["role_types"] = request.role_types
    if request.items is not None:
        update_data["items"] = [item.dict() for item in request.items]
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    result = supabase.table('onboarding_templates').update(update_data).eq('id', template_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template"
        )
    
    t = result.data[0]
    
    return TemplateResponse(
        id=str(t['id']),
        title=t['title'],
        role_types=t['role_types'],
        items=t['items'],
        is_active=t.get('is_active', True),
        created_at=t.get('created_at'),
        created_by=str(t['created_by']) if t.get('created_by') else None
    )


@router.delete("/onboarding-templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Delete (or deactivate) an onboarding template.
    Warning: Physical delete might fail if used by active onboardings.
    Consider setting is_active=False instead.
    """
    supabase = get_supabase_client()
    
    # Check usage
    usage = supabase.table('new_hire_onboarding').select("id", count="exact").eq('template_id', template_id).execute()
    if usage.count and usage.count > 0:
        # Soft delete
        result = supabase.table('onboarding_templates').update({"is_active": False}).eq('id', template_id).execute()
        return {"message": "Template deactivated (in use)", "id": template_id}
    else:
        # Hard delete
        result = supabase.table('onboarding_templates').delete().eq('id', template_id).execute()
        return {"message": "Template deleted", "id": template_id}


@router.post("/onboarding", response_model=StartOnboardingResponse, status_code=status.HTTP_201_CREATED)
async def start_new_hire_onboarding(
    request: StartOnboardingRequest,
    current_user: dict = Depends(require_hr)
):
    """
    Start onboarding for a candidate.
    This creates the onboarding record based on a template.
    """
    supabase = get_supabase_client()
    
    # 1. Validate Candidate & Application
    candidate = supabase.table('candidates').select("id").eq('id', request.candidate_id).execute()
    if not candidate.data:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    application = supabase.table('applications').select("id, status").eq('id', request.application_id).eq('candidate_id', request.candidate_id).execute()
    if not application.data:
        raise HTTPException(status_code=404, detail="Application not found for this candidate")
    
    if application.data[0]['status'] != 'offer_accepted':
        # Optional: Enforce that they must have accepted an offer
        pass 

    # 2. Get Template to copy items
    template = supabase.table('onboarding_templates').select("*").eq('id', request.template_id).execute()
    if not template.data:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 3. Create initial progress array from template items
    # Items from template have {title, description, ...}
    # Progress needs {item_index, status, notes}
    # We will just initialize an empty progress list. The logic in `onboarding.py` router
    # handles the updates. The frontend will combine Template Items + Progress to render.
    initial_progress = []
    
    new_onboarding = {
        "candidate_id": request.candidate_id,
        "application_id": request.application_id,
        "template_id": request.template_id,
        "start_date": request.start_date,
        "expected_completion_date": request.expected_completion_date,
        "manager_hr_id": request.manager_id,
        "status": "not_started",
        "progress": initial_progress,
        "completion_percentage": 0.0
    }
    
    result = supabase.table('new_hire_onboarding').insert(new_onboarding).execute()
    
    if not result.data:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start onboarding"
        )
    
    o = result.data[0]
    
    return StartOnboardingResponse(
        id=str(o['id']),
        candidate_id=str(o['candidate_id']),
        status=o['status'],
        start_date=o['start_date']
    )
