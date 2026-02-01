"""
Interviews router for managing HR interview scheduling.
Handles scheduling, rescheduling, and status updates.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from database import get_supabase_client
from dependencies import get_current_user, require_hr, require_candidate

router = APIRouter(prefix="/interviews", tags=["Interviews"])


# ============ Constants ============

INTERVIEW_STATUSES = ["scheduled", "confirmed", "rescheduled", "completed", "cancelled", "no_show"]
INTERVIEW_TYPES = ["phone_screen", "technical", "behavioral", "hr", "onsite", "final"]


# ============ Request/Response Models ============

class InterviewCreate(BaseModel):
    application_id: str
    interview_type: str
    scheduled_date: str  # ISO format datetime
    duration_minutes: int = 60
    location: Optional[str] = None
    interviewer_ids: Optional[List[str]] = []
    notes: Optional[str] = None


class InterviewUpdate(BaseModel):
    scheduled_date: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    interviewer_ids: Optional[List[str]] = None
    notes: Optional[str] = None


class InterviewStatusUpdate(BaseModel):
    status: str
    reschedule_reason: Optional[str] = None


class InterviewResponse(BaseModel):
    id: str
    application_id: str
    interview_type: str
    scheduled_date: str
    duration_minutes: int
    location: Optional[str] = None
    interviewer_ids: Optional[List[str]] = None
    status: str
    reschedule_count: int = 0
    reschedule_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class InterviewWithDetailsResponse(InterviewResponse):
    """Interview with candidate and job details."""
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_title: Optional[str] = None


# ============ Endpoints ============

@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def schedule_interview(
    request: InterviewCreate,
    current_user: dict = Depends(require_hr)
):
    """
    Schedule a new interview. HR only.
    Automatically updates application status to 'interview_scheduled'.
    """
    supabase = get_supabase_client()
    
    # Validate interview type
    if request.interview_type not in INTERVIEW_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interview type. Must be one of: {', '.join(INTERVIEW_TYPES)}"
        )
    
    # Check if application exists and is in valid state
    app_result = supabase.table('applications').select("id, status, candidate_id, job_role_id").eq('id', request.application_id).execute()
    if not app_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    application = app_result.data[0]
    
    # Application must be shortlisted to schedule interview
    if application['status'] not in ['shortlisted', 'interview_scheduled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot schedule interview. Application status must be 'shortlisted', current: '{application['status']}'"
        )
    
    # Validate scheduled date is in the future
    try:
        scheduled_dt = datetime.fromisoformat(request.scheduled_date.replace('Z', '+00:00'))
        if scheduled_dt < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled date must be in the future"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (e.g., 2025-02-01T10:00:00Z)"
        )
    
    # Create interview
    new_interview = {
        "application_id": request.application_id,
        "interview_type": request.interview_type,
        "scheduled_date": request.scheduled_date,
        "duration_minutes": request.duration_minutes,
        "location": request.location,
        "interviewer_ids": request.interviewer_ids,
        "status": "scheduled",
        "reschedule_count": 0,
        "notes": request.notes
    }
    
    result = supabase.table('interviews').insert(new_interview).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create interview"
        )
    
    # Update application status
    supabase.table('applications').update({
        "status": "interview_scheduled",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq('id', request.application_id).execute()
    
    interview = result.data[0]
    
    return InterviewResponse(
        id=str(interview['id']),
        application_id=str(interview['application_id']),
        interview_type=interview['interview_type'],
        scheduled_date=interview['scheduled_date'],
        duration_minutes=interview['duration_minutes'],
        location=interview.get('location'),
        interviewer_ids=interview.get('interviewer_ids'),
        status=interview['status'],
        reschedule_count=interview.get('reschedule_count', 0),
        reschedule_reason=interview.get('reschedule_reason'),
        notes=interview.get('notes'),
        created_at=interview.get('created_at'),
        updated_at=interview.get('updated_at')
    )


@router.get("", response_model=List[InterviewWithDetailsResponse])
async def list_interviews(
    application_id: Optional[str] = Query(None, description="Filter by application"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    interview_type: Optional[str] = Query(None, description="Filter by interview type"),
    current_user: dict = Depends(get_current_user)
):
    """
    List interviews.
    HR sees all interviews. Candidates see only their own.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('interviews').select("*")
    
    if application_id:
        query = query.eq('application_id', application_id)
    
    if status_filter:
        query = query.eq('status', status_filter)
    
    if interview_type:
        query = query.eq('interview_type', interview_type)
    
    result = query.order('scheduled_date', desc=False).execute()
    
    interviews = []
    for interview in result.data:
        # Get application details for candidate filtering
        app_result = supabase.table('applications').select("candidate_id, job_role_id").eq('id', interview['application_id']).execute()
        
        if not app_result.data:
            continue
        
        app = app_result.data[0]
        
        # Candidates can only see their own interviews
        if current_user["user_type"] == "candidate":
            if str(app['candidate_id']) != current_user["user_id"]:
                continue
        
        # Get candidate details
        candidate_result = supabase.table('candidates').select("first_name, last_name, email").eq('id', app['candidate_id']).execute()
        candidate_name = None
        candidate_email = None
        if candidate_result.data:
            c = candidate_result.data[0]
            candidate_name = f"{c['first_name']} {c['last_name']}"
            candidate_email = c['email']
        
        # Get job details
        job_result = supabase.table('job_roles').select("title").eq('id', app['job_role_id']).execute()
        job_title = job_result.data[0]['title'] if job_result.data else None
        
        interviews.append(InterviewWithDetailsResponse(
            id=str(interview['id']),
            application_id=str(interview['application_id']),
            interview_type=interview['interview_type'],
            scheduled_date=interview['scheduled_date'],
            duration_minutes=interview['duration_minutes'],
            location=interview.get('location'),
            interviewer_ids=interview.get('interviewer_ids'),
            status=interview['status'],
            reschedule_count=interview.get('reschedule_count', 0),
            reschedule_reason=interview.get('reschedule_reason'),
            notes=interview.get('notes'),
            created_at=interview.get('created_at'),
            updated_at=interview.get('updated_at'),
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            job_title=job_title
        ))
    
    return interviews


@router.get("/{interview_id}", response_model=InterviewWithDetailsResponse)
async def get_interview(
    interview_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get interview details by ID.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('interviews').select("*").eq('id', interview_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    interview = result.data[0]
    
    # Get application to check access
    app_result = supabase.table('applications').select("candidate_id, job_role_id").eq('id', interview['application_id']).execute()
    
    if not app_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    app = app_result.data[0]
    
    # Candidates can only see their own interviews
    if current_user["user_type"] == "candidate" and str(app['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get candidate details
    candidate_result = supabase.table('candidates').select("first_name, last_name, email").eq('id', app['candidate_id']).execute()
    candidate_name = None
    candidate_email = None
    if candidate_result.data:
        c = candidate_result.data[0]
        candidate_name = f"{c['first_name']} {c['last_name']}"
        candidate_email = c['email']
    
    # Get job details
    job_result = supabase.table('job_roles').select("title").eq('id', app['job_role_id']).execute()
    job_title = job_result.data[0]['title'] if job_result.data else None
    
    return InterviewWithDetailsResponse(
        id=str(interview['id']),
        application_id=str(interview['application_id']),
        interview_type=interview['interview_type'],
        scheduled_date=interview['scheduled_date'],
        duration_minutes=interview['duration_minutes'],
        location=interview.get('location'),
        interviewer_ids=interview.get('interviewer_ids'),
        status=interview['status'],
        reschedule_count=interview.get('reschedule_count', 0),
        reschedule_reason=interview.get('reschedule_reason'),
        notes=interview.get('notes'),
        created_at=interview.get('created_at'),
        updated_at=interview.get('updated_at'),
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        job_title=job_title
    )


@router.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: str,
    request: InterviewUpdate,
    current_user: dict = Depends(require_hr)
):
    """
    Update interview details. HR only.
    """
    supabase = get_supabase_client()
    
    # Check if interview exists
    existing = supabase.table('interviews').select("*").eq('id', interview_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    interview = existing.data[0]
    
    # Can't update completed/cancelled interviews
    if interview['status'] in ['completed', 'cancelled', 'no_show']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update interview with status '{interview['status']}'"
        )
    
    # Build update data
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if request.scheduled_date is not None:
        update_data["scheduled_date"] = request.scheduled_date
    if request.duration_minutes is not None:
        update_data["duration_minutes"] = request.duration_minutes
    if request.location is not None:
        update_data["location"] = request.location
    if request.interviewer_ids is not None:
        update_data["interviewer_ids"] = request.interviewer_ids
    if request.notes is not None:
        update_data["notes"] = request.notes
    
    result = supabase.table('interviews').update(update_data).eq('id', interview_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update interview"
        )
    
    updated = result.data[0]
    
    return InterviewResponse(
        id=str(updated['id']),
        application_id=str(updated['application_id']),
        interview_type=updated['interview_type'],
        scheduled_date=updated['scheduled_date'],
        duration_minutes=updated['duration_minutes'],
        location=updated.get('location'),
        interviewer_ids=updated.get('interviewer_ids'),
        status=updated['status'],
        reschedule_count=updated.get('reschedule_count', 0),
        reschedule_reason=updated.get('reschedule_reason'),
        notes=updated.get('notes'),
        created_at=updated.get('created_at'),
        updated_at=updated.get('updated_at')
    )


@router.put("/{interview_id}/status", response_model=InterviewResponse)
async def update_interview_status(
    interview_id: str,
    request: InterviewStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update interview status.
    - HR can set any valid status
    - Candidates can only 'confirm' or request 'reschedule'
    """
    supabase = get_supabase_client()
    
    if request.status not in INTERVIEW_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(INTERVIEW_STATUSES)}"
        )
    
    # Get interview
    existing = supabase.table('interviews').select("*").eq('id', interview_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    interview = existing.data[0]
    
    # Get application to check access
    app_result = supabase.table('applications').select("candidate_id").eq('id', interview['application_id']).execute()
    if not app_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    app = app_result.data[0]
    
    # Candidates can only confirm or request reschedule
    if current_user["user_type"] == "candidate":
        if str(app['candidate_id']) != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        if request.status not in ['confirmed', 'rescheduled']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates can only confirm or request reschedule"
            )
    
    # Build update data
    update_data = {
        "status": request.status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Handle reschedule
    if request.status == 'rescheduled':
        update_data["reschedule_count"] = interview.get('reschedule_count', 0) + 1
        if request.reschedule_reason:
            update_data["reschedule_reason"] = request.reschedule_reason
    
    # Update interview
    result = supabase.table('interviews').update(update_data).eq('id', interview_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update interview"
        )
    
    # If interview is completed, update application status
    if request.status == 'completed':
        supabase.table('applications').update({
            "status": "interview_completed",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq('id', interview['application_id']).execute()
    
    updated = result.data[0]
    
    return InterviewResponse(
        id=str(updated['id']),
        application_id=str(updated['application_id']),
        interview_type=updated['interview_type'],
        scheduled_date=updated['scheduled_date'],
        duration_minutes=updated['duration_minutes'],
        location=updated.get('location'),
        interviewer_ids=updated.get('interviewer_ids'),
        status=updated['status'],
        reschedule_count=updated.get('reschedule_count', 0),
        reschedule_reason=updated.get('reschedule_reason'),
        notes=updated.get('notes'),
        created_at=updated.get('created_at'),
        updated_at=updated.get('updated_at')
    )


@router.delete("/{interview_id}")
async def cancel_interview(
    interview_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Cancel an interview. HR only.
    """
    supabase = get_supabase_client()
    
    # Check if interview exists
    existing = supabase.table('interviews').select("id, status").eq('id', interview_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    interview = existing.data[0]
    
    if interview['status'] in ['completed', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel interview with status '{interview['status']}'"
        )
    
    # Update status to cancelled
    supabase.table('interviews').update({
        "status": "cancelled",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq('id', interview_id).execute()
    
    return {"message": "Interview cancelled", "interview_id": interview_id}
