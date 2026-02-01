"""
Onboarding router for managing new hire onboarding progress.
Handles onboarding task completion and progress tracking.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from database import get_supabase_client
from dependencies import get_current_user, require_candidate, require_hr

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# ============ Constants ============

ONBOARDING_STATUSES = ["not_started", "in_progress", "completed", "on_hold"]
ITEM_STATUSES = ["pending", "in_progress", "completed", "skipped"]


# ============ Request/Response Models ============

class OnboardingProgressUpdate(BaseModel):
    item_index: int
    status: str  # pending, in_progress, completed, skipped
    notes: Optional[str] = None


class OnboardingItemProgress(BaseModel):
    item_index: int
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


class OnboardingResponse(BaseModel):
    id: str
    candidate_id: str
    application_id: str
    template_id: Optional[str] = None
    start_date: str
    status: str
    completion_percentage: float = 0.0
    progress: List[OnboardingItemProgress] = []
    expected_completion_date: Optional[str] = None
    actual_completion_date: Optional[str] = None
    manager_hr_id: Optional[str] = None
    created_at: Optional[str] = None


class OnboardingListResponse(BaseModel):
    id: str
    candidate_id: str
    status: str
    completion_percentage: float
    start_date: str
    candidate_name: Optional[str] = None


# ============ Endpoints ============

@router.get("/my", response_model=OnboardingResponse)
async def get_my_onboarding(
    current_user: dict = Depends(require_candidate)
):
    """
    Get the current candidate's onboarding record.
    Returns the active onboarding if exists.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Get active onboarding (not completed)
    result = supabase.table('new_hire_onboarding').select("*").eq('candidate_id', candidate_id).neq('status', 'completed').order('created_at', desc=True).limit(1).execute()
    
    if not result.data:
        # Check if there's any completed onboarding
        completed = supabase.table('new_hire_onboarding').select("*").eq('candidate_id', candidate_id).eq('status', 'completed').order('created_at', desc=True).limit(1).execute()
        if completed.data:
            o = completed.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No onboarding record found"
            )
    else:
        o = result.data[0]
    
    progress = o.get('progress', [])
    if progress is None:
        progress = []
    
    return OnboardingResponse(
        id=str(o['id']),
        candidate_id=str(o['candidate_id']),
        application_id=str(o['application_id']),
        template_id=str(o['template_id']) if o.get('template_id') else None,
        start_date=o['start_date'],
        status=o['status'],
        completion_percentage=o.get('completion_percentage', 0.0),
        progress=[OnboardingItemProgress(**p) for p in progress],
        expected_completion_date=o.get('expected_completion_date'),
        actual_completion_date=o.get('actual_completion_date'),
        manager_hr_id=str(o['manager_hr_id']) if o.get('manager_hr_id') else None,
        created_at=o.get('created_at')
    )


@router.put("/{onboarding_id}/progress", response_model=OnboardingResponse)
async def update_progress(
    onboarding_id: str,
    request: OnboardingProgressUpdate,
    current_user: dict = Depends(require_candidate)
):
    """
    Update progress on an onboarding item.
    Candidate marks tasks as in_progress or completed.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Validate status
    if request.status not in ITEM_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(ITEM_STATUSES)}"
        )
    
    # Get onboarding record
    existing = supabase.table('new_hire_onboarding').select("*").eq('id', onboarding_id).eq('candidate_id', candidate_id).execute()
    
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding record not found"
        )
    
    onboarding = existing.data[0]
    
    if onboarding['status'] == 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed"
        )
    
    # Update progress array
    progress = onboarding.get('progress', [])
    if progress is None:
        progress = []
    
    # Find or create progress entry for this item
    now = datetime.now(timezone.utc).isoformat()
    found = False
    
    for p in progress:
        if p['item_index'] == request.item_index:
            p['status'] = request.status
            if request.status == 'in_progress' and not p.get('started_at'):
                p['started_at'] = now
            if request.status == 'completed':
                p['completed_at'] = now
            if request.notes:
                p['notes'] = request.notes
            found = True
            break
    
    if not found:
        new_progress = {
            "item_index": request.item_index,
            "status": request.status,
            "started_at": now if request.status in ['in_progress', 'completed'] else None,
            "completed_at": now if request.status == 'completed' else None,
            "notes": request.notes
        }
        progress.append(new_progress)
    
    # Calculate completion percentage
    # We need to get the template to know total items
    total_items = len(progress)  # Fallback
    if onboarding.get('template_id'):
        template = supabase.table('onboarding_templates').select("items").eq('id', onboarding['template_id']).execute()
        if template.data and template.data[0].get('items'):
            total_items = len(template.data[0]['items'])
    
    completed_items = sum(1 for p in progress if p.get('status') == 'completed')
    completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
    
    # Determine overall status
    new_status = onboarding['status']
    if new_status == 'not_started':
        new_status = 'in_progress'
    if completion_percentage >= 100:
        new_status = 'completed'
    
    # Update onboarding
    update_data = {
        "progress": progress,
        "completion_percentage": round(completion_percentage, 1),
        "status": new_status,
        "updated_at": now
    }
    
    if new_status == 'completed':
        update_data["actual_completion_date"] = now
    
    result = supabase.table('new_hire_onboarding').update(update_data).eq('id', onboarding_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update onboarding progress"
        )
    
    o = result.data[0]
    updated_progress = o.get('progress', [])
    if updated_progress is None:
        updated_progress = []
    
    return OnboardingResponse(
        id=str(o['id']),
        candidate_id=str(o['candidate_id']),
        application_id=str(o['application_id']),
        template_id=str(o['template_id']) if o.get('template_id') else None,
        start_date=o['start_date'],
        status=o['status'],
        completion_percentage=o.get('completion_percentage', 0.0),
        progress=[OnboardingItemProgress(**p) for p in updated_progress],
        expected_completion_date=o.get('expected_completion_date'),
        actual_completion_date=o.get('actual_completion_date'),
        manager_hr_id=str(o['manager_hr_id']) if o.get('manager_hr_id') else None,
        created_at=o.get('created_at')
    )


@router.get("", response_model=List[OnboardingListResponse])
async def list_onboarding(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: dict = Depends(require_hr)
):
    """
    List all onboarding records. HR only.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('new_hire_onboarding').select("*")
    
    if status_filter:
        query = query.eq('status', status_filter)
    
    result = query.order('created_at', desc=True).execute()
    
    onboardings = []
    for o in result.data:
        # Get candidate name
        candidate_result = supabase.table('candidates').select("first_name, last_name").eq('id', o['candidate_id']).execute()
        candidate_name = None
        if candidate_result.data:
            c = candidate_result.data[0]
            candidate_name = f"{c['first_name']} {c['last_name']}"
        
        onboardings.append(OnboardingListResponse(
            id=str(o['id']),
            candidate_id=str(o['candidate_id']),
            status=o['status'],
            completion_percentage=o.get('completion_percentage', 0.0),
            start_date=o['start_date'],
            candidate_name=candidate_name
        ))
    
    return onboardings


@router.get("/{onboarding_id}", response_model=OnboardingResponse)
async def get_onboarding(
    onboarding_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get onboarding details by ID.
    Candidates can only view their own onboarding.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('new_hire_onboarding').select("*").eq('id', onboarding_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding record not found"
        )
    
    o = result.data[0]
    
    # Check access
    if current_user["user_type"] == "candidate" and str(o['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    progress = o.get('progress', [])
    if progress is None:
        progress = []
    
    return OnboardingResponse(
        id=str(o['id']),
        candidate_id=str(o['candidate_id']),
        application_id=str(o['application_id']),
        template_id=str(o['template_id']) if o.get('template_id') else None,
        start_date=o['start_date'],
        status=o['status'],
        completion_percentage=o.get('completion_percentage', 0.0),
        progress=[OnboardingItemProgress(**p) for p in progress],
        expected_completion_date=o.get('expected_completion_date'),
        actual_completion_date=o.get('actual_completion_date'),
        manager_hr_id=str(o['manager_hr_id']) if o.get('manager_hr_id') else None,
        created_at=o.get('created_at')
    )
