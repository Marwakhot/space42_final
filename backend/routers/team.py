"""
Team Directory router for viewing team members.
Candidates (new hires) can view their team after being hired.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from database import get_supabase_client
from dependencies import get_current_user

router = APIRouter(prefix="/team", tags=["Team Directory"])


# ============ Response Models ============

class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    user_type: str
    department: str
    position: str
    team_name: Optional[str] = None
    first_name: str
    last_name: str
    bio: Optional[str] = None
    expertise_areas: Optional[List[str]] = None
    profile_photo_url: Optional[str] = None
    is_active: bool = True


class TeamMemberListResponse(BaseModel):
    id: str
    department: str
    position: str
    team_name: Optional[str] = None
    first_name: str
    last_name: str
    profile_photo_url: Optional[str] = None


# ============ Endpoints ============

@router.get("", response_model=List[TeamMemberListResponse])
async def list_team_members(
    department: Optional[str] = Query(None, description="Filter by department"),
    team_name: Optional[str] = Query(None, description="Filter by team name"),
    current_user: dict = Depends(get_current_user)
):
    """
    List all active team members.
    Available to authenticated users (candidates who are hired, HR, admin).
    """
    supabase = get_supabase_client()
    
    # For candidates, check if they have an accepted offer (onboarding status)
    if current_user["user_type"] == "candidate":
        # Check if candidate has an active onboarding (meaning they're hired)
        onboarding = supabase.table('new_hire_onboarding').select("id").eq('candidate_id', current_user["user_id"]).execute()
        if not onboarding.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team directory is only available after being hired"
            )
    
    query = supabase.table('team_directory').select("*").eq('is_active', True)
    
    if department:
        query = query.eq('department', department)
    
    if team_name:
        query = query.eq('team_name', team_name)
    
    result = query.order('department').order('position').execute()
    
    team_members = []
    for t in result.data:
        # Get user details based on user_type
        first_name = ""
        last_name = ""
        
        if t['user_type'] == 'hr':
            user_result = supabase.table('hr_users').select("first_name, last_name").eq('id', t['user_id']).execute()
        elif t['user_type'] == 'admin':
            user_result = supabase.table('admin_users').select("first_name, last_name").eq('id', t['user_id']).execute()
        else:
            user_result = supabase.table('candidates').select("first_name, last_name").eq('id', t['user_id']).execute()
        
        if user_result.data:
            first_name = user_result.data[0]['first_name']
            last_name = user_result.data[0]['last_name']
        
        team_members.append(TeamMemberListResponse(
            id=str(t['id']),
            department=t['department'],
            position=t['position'],
            team_name=t.get('team_name'),
            first_name=first_name,
            last_name=last_name,
            profile_photo_url=t.get('profile_photo_url')
        ))
    
    return team_members


@router.get("/{member_id}", response_model=TeamMemberResponse)
async def get_team_member(
    member_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get details of a specific team member.
    """
    supabase = get_supabase_client()
    
    # For candidates, check if they have an accepted offer
    if current_user["user_type"] == "candidate":
        onboarding = supabase.table('new_hire_onboarding').select("id").eq('candidate_id', current_user["user_id"]).execute()
        if not onboarding.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team directory is only available after being hired"
            )
    
    result = supabase.table('team_directory').select("*").eq('id', member_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    t = result.data[0]
    
    # Get user details
    first_name = ""
    last_name = ""
    
    if t['user_type'] == 'hr':
        user_result = supabase.table('hr_users').select("first_name, last_name").eq('id', t['user_id']).execute()
    elif t['user_type'] == 'admin':
        user_result = supabase.table('admin_users').select("first_name, last_name").eq('id', t['user_id']).execute()
    else:
        user_result = supabase.table('candidates').select("first_name, last_name").eq('id', t['user_id']).execute()
    
    if user_result.data:
        first_name = user_result.data[0]['first_name']
        last_name = user_result.data[0]['last_name']
    
    return TeamMemberResponse(
        id=str(t['id']),
        user_id=str(t['user_id']),
        user_type=t['user_type'],
        department=t['department'],
        position=t['position'],
        team_name=t.get('team_name'),
        first_name=first_name,
        last_name=last_name,
        bio=t.get('bio'),
        expertise_areas=t.get('expertise_areas'),
        profile_photo_url=t.get('profile_photo_url'),
        is_active=t.get('is_active', True)
    )


@router.get("/department/{department}", response_model=List[TeamMemberListResponse])
async def get_department_team(
    department: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all team members in a specific department.
    """
    supabase = get_supabase_client()
    
    # For candidates, check if they have an accepted offer
    if current_user["user_type"] == "candidate":
        onboarding = supabase.table('new_hire_onboarding').select("id").eq('candidate_id', current_user["user_id"]).execute()
        if not onboarding.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team directory is only available after being hired"
            )
    
    result = supabase.table('team_directory').select("*").eq('department', department).eq('is_active', True).order('position').execute()
    
    team_members = []
    for t in result.data:
        # Get user details
        first_name = ""
        last_name = ""
        
        if t['user_type'] == 'hr':
            user_result = supabase.table('hr_users').select("first_name, last_name").eq('id', t['user_id']).execute()
        elif t['user_type'] == 'admin':
            user_result = supabase.table('admin_users').select("first_name, last_name").eq('id', t['user_id']).execute()
        else:
            user_result = supabase.table('candidates').select("first_name, last_name").eq('id', t['user_id']).execute()
        
        if user_result.data:
            first_name = user_result.data[0]['first_name']
            last_name = user_result.data[0]['last_name']
        
        team_members.append(TeamMemberListResponse(
            id=str(t['id']),
            department=t['department'],
            position=t['position'],
            team_name=t.get('team_name'),
            first_name=first_name,
            last_name=last_name,
            profile_photo_url=t.get('profile_photo_url')
        ))
    
    return team_members


# ============ Management Endpoints (Admin/HR Only) ============

class TeamMemberCreate(BaseModel):
    user_id: str
    user_type: str
    department: str
    position: str
    team_name: Optional[str] = None
    bio: Optional[str] = None
    expertise_areas: Optional[List[str]] = []
    profile_photo_url: Optional[str] = None

class TeamMemberUpdate(BaseModel):
    department: Optional[str] = None
    position: Optional[str] = None
    team_name: Optional[str] = None
    bio: Optional[str] = None
    expertise_areas: Optional[List[str]] = None
    profile_photo_url: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    request: TeamMemberCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new member to the team directory.
    Admin or HR only.
    """
    if current_user["user_type"] not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or HR can manage team directory"
        )
        
    supabase = get_supabase_client()
    
    # Check if user exists in the respective table
    table_name = "candidates"
    if request.user_type == "hr":
        table_name = "hr_users"
    elif request.user_type == "admin":
        table_name = "admin_users"
        
    user_exists = supabase.table(table_name).select("id").eq("id", request.user_id).execute()
    if not user_exists.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found in {table_name}"
        )

    # Check if already in directory
    existing = supabase.table('team_directory').select("id").eq("user_id", request.user_id).execute()
    if existing.data:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already in team directory"
        )

    new_member = {
        "user_id": request.user_id,
        "user_type": request.user_type,
        "department": request.department,
        "position": request.position,
        "team_name": request.team_name,
        "bio": request.bio,
        "expertise_areas": request.expertise_areas,
        "profile_photo_url": request.profile_photo_url,
        "is_active": True
    }
    
    result = supabase.table('team_directory').insert(new_member).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member"
        )
        
    t = result.data[0]
    
    # Get user details for response
    first_name = ""
    last_name = ""
    if user_exists.data:
         # Need to fetch details since we only checked ID above
         details = supabase.table(table_name).select("first_name, last_name").eq("id", request.user_id).execute()
         if details.data:
             first_name = details.data[0]['first_name']
             last_name = details.data[0]['last_name']

    return TeamMemberResponse(
        id=str(t['id']),
        user_id=str(t['user_id']),
        user_type=t['user_type'],
        department=t['department'],
        position=t['position'],
        team_name=t.get('team_name'),
        first_name=first_name,
        last_name=last_name,
        bio=t.get('bio'),
        expertise_areas=t.get('expertise_areas'),
        profile_photo_url=t.get('profile_photo_url'),
        is_active=t.get('is_active', True)
    )


@router.put("/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    member_id: str,
    request: TeamMemberUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update team member details.
    Admin or HR only.
    """
    if current_user["user_type"] not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or HR can manage team directory"
        )
        
    supabase = get_supabase_client()
    
    existing = supabase.table('team_directory').select("*").eq('id', member_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    t = existing.data[0]
    
    # Build update dict
    update_data = {}
    if request.department is not None: update_data["department"] = request.department
    if request.position is not None: update_data["position"] = request.position
    if request.team_name is not None: update_data["team_name"] = request.team_name
    if request.bio is not None: update_data["bio"] = request.bio
    if request.expertise_areas is not None: update_data["expertise_areas"] = request.expertise_areas
    if request.profile_photo_url is not None: update_data["profile_photo_url"] = request.profile_photo_url
    if request.is_active is not None: update_data["is_active"] = request.is_active
    
    if not update_data:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    result = supabase.table('team_directory').update(update_data).eq('id', member_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team member"
        )
        
    updated = result.data[0]
    
    # Get user details
    first_name = ""
    last_name = ""
    
    table_name = "candidates"
    if updated['user_type'] == 'hr': table_name = "hr_users"
    elif updated['user_type'] == 'admin': table_name = "admin_users"
    
    user_result = supabase.table(table_name).select("first_name, last_name").eq('id', updated['user_id']).execute()
    if user_result.data:
        first_name = user_result.data[0]['first_name']
        last_name = user_result.data[0]['last_name']

    return TeamMemberResponse(
        id=str(updated['id']),
        user_id=str(updated['user_id']),
        user_type=updated['user_type'],
        department=updated['department'],
        position=updated['position'],
        team_name=updated.get('team_name'),
        first_name=first_name,
        last_name=last_name,
        bio=updated.get('bio'),
        expertise_areas=updated.get('expertise_areas'),
        profile_photo_url=updated.get('profile_photo_url'),
        is_active=updated.get('is_active', True)
    )


@router.delete("/{member_id}")
async def remove_team_member(
    member_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove member from team directory (hard delete).
    Admin or HR only.
    """
    if current_user["user_type"] not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or HR can manage team directory"
        )
        
    supabase = get_supabase_client()
    
    # Check existence
    existing = supabase.table('team_directory').select("id").eq('id', member_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
        
    supabase.table('team_directory').delete().eq('id', member_id).execute()
    
    return {"message": "Team member removed", "id": member_id}
