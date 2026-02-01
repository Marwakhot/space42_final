"""
Job Roles router for managing job positions.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_supabase_client
from dependencies import get_current_user, require_hr

router = APIRouter(prefix="/jobs", tags=["Job Roles"])


# ============ Request/Response Models ============

class JobRoleCreate(BaseModel):
    title: str
    department: str
    description: str
    location: Optional[str] = None
    work_type: Optional[str] = "onsite"  # remote, hybrid, onsite
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = "AED"
    experience_min: Optional[int] = 0
    experience_max: Optional[int] = None
    non_negotiable_skills: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    openings_count: Optional[int] = 1


class JobRoleUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    work_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    non_negotiable_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    openings_count: Optional[int] = None
    is_active: Optional[bool] = None


class JobRoleResponse(BaseModel):
    id: str
    title: str
    department: str
    description: str
    location: Optional[str] = None
    work_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    non_negotiable_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    openings_count: Optional[int] = None
    is_active: bool
    created_at: Optional[str] = None


# ============ Endpoints ============

@router.get("", response_model=List[JobRoleResponse])
async def list_jobs(
    department: Optional[str] = Query(None, description="Filter by department"),
    work_type: Optional[str] = Query(None, description="Filter by work type"),
    active_only: bool = Query(True, description="Show only active jobs")
):
    """
    List all job roles. Public endpoint.
    Supports filtering by department and work type.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('job_roles').select("*")
    
    if active_only:
        query = query.eq('is_active', True)
    
    if department:
        query = query.eq('department', department)
    
    if work_type:
        query = query.eq('work_type', work_type)
    
    result = query.order('created_at', desc=True).execute()
    
    return [JobRoleResponse(
        id=str(job['id']),
        title=job['title'],
        department=job['department'],
        description=job['description'],
        location=job.get('location'),
        work_type=job.get('work_type'),
        salary_min=job.get('salary_min'),
        salary_max=job.get('salary_max'),
        currency=job.get('currency'),
        experience_min=job.get('experience_min'),
        experience_max=job.get('experience_max'),
        non_negotiable_skills=job.get('non_negotiable_skills'),
        preferred_skills=job.get('preferred_skills'),
        openings_count=job.get('openings_count'),
        is_active=job.get('is_active', True),
        created_at=job.get('created_at')
    ) for job in result.data]


@router.get("/{job_id}", response_model=JobRoleResponse)
async def get_job(job_id: str):
    """Get a specific job role by ID. Public endpoint."""
    supabase = get_supabase_client()
    
    result = supabase.table('job_roles').select("*").eq('id', job_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job role not found"
        )
    
    job = result.data[0]
    
    return JobRoleResponse(
        id=str(job['id']),
        title=job['title'],
        department=job['department'],
        description=job['description'],
        location=job.get('location'),
        work_type=job.get('work_type'),
        salary_min=job.get('salary_min'),
        salary_max=job.get('salary_max'),
        currency=job.get('currency'),
        experience_min=job.get('experience_min'),
        experience_max=job.get('experience_max'),
        non_negotiable_skills=job.get('non_negotiable_skills'),
        preferred_skills=job.get('preferred_skills'),
        openings_count=job.get('openings_count'),
        is_active=job.get('is_active', True),
        created_at=job.get('created_at')
    )


@router.post("", response_model=JobRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: JobRoleCreate,
    current_user: dict = Depends(require_hr)
):
    """Create a new job role. HR only."""
    supabase = get_supabase_client()
    
    new_job = {
        "title": request.title,
        "department": request.department,
        "description": request.description,
        "location": request.location,
        "work_type": request.work_type,
        "salary_min": request.salary_min,
        "salary_max": request.salary_max,
        "currency": request.currency,
        "experience_min": request.experience_min,
        "experience_max": request.experience_max,
        "non_negotiable_skills": request.non_negotiable_skills,
        "preferred_skills": request.preferred_skills,
        "openings_count": request.openings_count,
        "is_active": True,
        "created_by": current_user["user_id"]
    }
    
    result = supabase.table('job_roles').insert(new_job).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job role"
        )
    
    job = result.data[0]
    
    return JobRoleResponse(
        id=str(job['id']),
        title=job['title'],
        department=job['department'],
        description=job['description'],
        location=job.get('location'),
        work_type=job.get('work_type'),
        salary_min=job.get('salary_min'),
        salary_max=job.get('salary_max'),
        currency=job.get('currency'),
        experience_min=job.get('experience_min'),
        experience_max=job.get('experience_max'),
        non_negotiable_skills=job.get('non_negotiable_skills'),
        preferred_skills=job.get('preferred_skills'),
        openings_count=job.get('openings_count'),
        is_active=job.get('is_active', True),
        created_at=job.get('created_at')
    )


@router.put("/{job_id}", response_model=JobRoleResponse)
async def update_job(
    job_id: str,
    request: JobRoleUpdate,
    current_user: dict = Depends(require_hr)
):
    """Update a job role. HR only."""
    supabase = get_supabase_client()
    
    # Check if job exists
    existing = supabase.table('job_roles').select("id").eq('id', job_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job role not found"
        )
    
    # Build update dict with only provided fields
    update_data = {}
    for field, value in request.model_dump().items():
        if value is not None:
            update_data[field] = value
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = supabase.table('job_roles').update(update_data).eq('id', job_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job role"
        )
    
    job = result.data[0]
    
    return JobRoleResponse(
        id=str(job['id']),
        title=job['title'],
        department=job['department'],
        description=job['description'],
        location=job.get('location'),
        work_type=job.get('work_type'),
        salary_min=job.get('salary_min'),
        salary_max=job.get('salary_max'),
        currency=job.get('currency'),
        experience_min=job.get('experience_min'),
        experience_max=job.get('experience_max'),
        non_negotiable_skills=job.get('non_negotiable_skills'),
        preferred_skills=job.get('preferred_skills'),
        openings_count=job.get('openings_count'),
        is_active=job.get('is_active', True),
        created_at=job.get('created_at')
    )


@router.delete("/{job_id}")
async def deactivate_job(
    job_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Deactivate a job role (soft delete). HR only.
    Sets is_active to False instead of deleting.
    """
    supabase = get_supabase_client()
    
    # Check if job exists
    existing = supabase.table('job_roles').select("id").eq('id', job_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job role not found"
        )
    
    result = supabase.table('job_roles').update({
        "is_active": False,
        "updated_at": datetime.utcnow().isoformat()
    }).eq('id', job_id).execute()
    
    return {"message": "Job role deactivated", "job_id": job_id}
