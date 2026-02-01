"""
Candidates router for managing candidate profiles.
Handles profile viewing and updates.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from database import get_supabase_client
from dependencies import get_current_user, require_candidate, require_hr

router = APIRouter(prefix="/candidates", tags=["Candidates"])


# ============ Request/Response Models ============

class CandidateProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class CandidateProfileResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class CandidateListResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    is_active: bool = True
    created_at: Optional[str] = None


# ============ Endpoints ============

@router.get("/me", response_model=CandidateProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(require_candidate)
):
    """
    Get the current candidate's profile.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    result = supabase.table('candidates').select("*").eq('id', candidate_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    c = result.data[0]
    
    return CandidateProfileResponse(
        id=str(c['id']),
        email=c['email'],
        first_name=c['first_name'],
        last_name=c['last_name'],
        location=c.get('location'),
        years_of_experience=c.get('years_of_experience'),
        phone=c.get('phone'),
        linkedin_url=c.get('linkedin_url'),
        is_active=c.get('is_active', True),
        created_at=c.get('created_at'),
        last_login=c.get('last_login')
    )


@router.put("/me", response_model=CandidateProfileResponse)
async def update_my_profile(
    request: CandidateProfileUpdate,
    current_user: dict = Depends(require_candidate)
):
    """
    Update the current candidate's profile.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Build update data
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if request.first_name is not None:
        update_data["first_name"] = request.first_name
    if request.last_name is not None:
        update_data["last_name"] = request.last_name
    if request.location is not None:
        update_data["location"] = request.location
    if request.years_of_experience is not None:
        update_data["years_of_experience"] = request.years_of_experience
    if request.phone is not None:
        update_data["phone"] = request.phone
    if request.linkedin_url is not None:
        update_data["linkedin_url"] = request.linkedin_url
    
    if len(update_data) == 1:  # Only updated_at
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    result = supabase.table('candidates').update(update_data).eq('id', candidate_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
    
    c = result.data[0]
    
    return CandidateProfileResponse(
        id=str(c['id']),
        email=c['email'],
        first_name=c['first_name'],
        last_name=c['last_name'],
        location=c.get('location'),
        years_of_experience=c.get('years_of_experience'),
        phone=c.get('phone'),
        linkedin_url=c.get('linkedin_url'),
        is_active=c.get('is_active', True),
        created_at=c.get('created_at'),
        last_login=c.get('last_login')
    )


@router.get("", response_model=List[CandidateListResponse])
async def list_candidates(
    location: Optional[str] = Query(None, description="Filter by location"),
    min_experience: Optional[int] = Query(None, description="Minimum years of experience"),
    active_only: bool = Query(True, description="Show only active candidates"),
    current_user: dict = Depends(require_hr)
):
    """
    List all candidates. HR only.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('candidates').select("id, email, first_name, last_name, location, years_of_experience, is_active, created_at")
    
    if active_only:
        query = query.eq('is_active', True)
    
    if location:
        query = query.ilike('location', f'%{location}%')
    
    if min_experience is not None:
        query = query.gte('years_of_experience', min_experience)
    
    result = query.order('created_at', desc=True).execute()
    
    return [CandidateListResponse(
        id=str(c['id']),
        email=c['email'],
        first_name=c['first_name'],
        last_name=c['last_name'],
        location=c.get('location'),
        years_of_experience=c.get('years_of_experience'),
        is_active=c.get('is_active', True),
        created_at=c.get('created_at')
    ) for c in result.data]


@router.get("/{candidate_id}", response_model=CandidateProfileResponse)
async def get_candidate(
    candidate_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Get a specific candidate's profile. HR only.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('candidates').select("*").eq('id', candidate_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    c = result.data[0]
    
    return CandidateProfileResponse(
        id=str(c['id']),
        email=c['email'],
        first_name=c['first_name'],
        last_name=c['last_name'],
        location=c.get('location'),
        years_of_experience=c.get('years_of_experience'),
        phone=c.get('phone'),
        linkedin_url=c.get('linkedin_url'),
        is_active=c.get('is_active', True),
        created_at=c.get('created_at'),
        last_login=c.get('last_login')
    )
