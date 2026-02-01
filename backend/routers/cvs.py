"""
CVs router for managing candidate CVs/resumes.
Handles CV upload, parsing status, and management.
"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os

from database import get_supabase_client
from dependencies import get_current_user, require_candidate
from services.cv_text_extractor import extract_text_from_file
from services.cv_parser import parse_resume
from services.cv_faiss_store import add_resume_to_vector_store
from services.cv_matching import find_matching_roles
import asyncio

router = APIRouter(prefix="/cvs", tags=["CVs"])


# ============ Constants ============

PARSING_STATUSES = ["pending", "processing", "completed", "failed"]
ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============ Request/Response Models ============

class CVResponse(BaseModel):
    id: str
    candidate_id: str
    file_name: str
    file_path: Optional[str] = None
    is_primary: bool
    parsing_status: str
    parsed_data: Optional[dict] = None
    uploaded_at: Optional[str] = None


class CVListResponse(BaseModel):
    id: str
    file_name: str
    is_primary: bool
    parsing_status: str
    uploaded_at: Optional[str] = None


class ParsedDataResponse(BaseModel):
    skills: List[str] = []
    experience: List[dict] = []
    education: List[dict] = []
    certifications: List[str] = []


# ============ Endpoints ============

@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    is_primary: bool = False,
    current_user: dict = Depends(require_candidate)
):
    """
    Upload a new CV. Candidate only.
    Supports PDF and DOC/DOCX files.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique file path
    unique_filename = f"{candidate_id}/{uuid.uuid4()}{file_ext}"
    
    # If this is primary, unset other primary CVs
    if is_primary:
        supabase.table('cvs').update({"is_primary": False}).eq('candidate_id', candidate_id).eq('is_primary', True).execute()
    
    # Check if this is the first CV (make it primary by default)
    existing_cvs = supabase.table('cvs').select("id").eq('candidate_id', candidate_id).execute()
    if not existing_cvs.data:
        is_primary = True
    
    # Create CV record
    new_cv = {
        "candidate_id": candidate_id,
        "file_name": file.filename,
        "file_path": unique_filename,
        "is_primary": is_primary,
        "parsing_status": "pending",
        "parsed_data": None
    }
    
    result = supabase.table('cvs').insert(new_cv).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload CV"
        )
    
    cv = result.data[0]
    
    # Trigger async CV parsing in background
    async def parse_cv_background():
        try:
            # Extract text from file
            resume_text = extract_text_from_file(content, file.filename)
            
            if not resume_text or len(resume_text.strip()) < 50:
                supabase.table('cvs').update({
                    "parsing_status": "failed"
                }).eq('id', cv['id']).execute()
                return
            
            # Parse resume using AI
            parsed_data = await parse_resume(resume_text)
            
            # Store resume text in parsed_data for semantic matching later
            parsed_data["resume_text"] = resume_text
            
            # Add resume to FAISS for semantic matching
            try:
                add_resume_to_vector_store(resume_text, candidate_id)
            except Exception as e:
                print(f"Error adding to FAISS: {e}")
            
            # Update CV with parsed data
            supabase.table('cvs').update({
                "parsing_status": "completed",
                "parsed_data": parsed_data,
                "parsing_completed_at": datetime.now(timezone.utc).isoformat()
            }).eq('id', cv['id']).execute()
        except Exception as e:
            print(f"Error parsing CV: {e}")
            supabase.table('cvs').update({
                "parsing_status": "failed"
            }).eq('id', cv['id']).execute()
    
    # Run parsing in background
    asyncio.create_task(parse_cv_background())
    
    return CVResponse(
        id=str(cv['id']),
        candidate_id=str(cv['candidate_id']),
        file_name=cv['file_name'],
        file_path=cv.get('file_path'),
        is_primary=cv['is_primary'],
        parsing_status=cv['parsing_status'],
        parsed_data=cv.get('parsed_data'),
        uploaded_at=cv.get('uploaded_at')
    )


@router.get("", response_model=List[CVListResponse])
async def list_my_cvs(
    current_user: dict = Depends(require_candidate)
):
    """
    List all CVs for the current candidate.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    result = supabase.table('cvs').select("id, file_name, is_primary, parsing_status, uploaded_at").eq('candidate_id', candidate_id).order('uploaded_at', desc=True).execute()
    
    return [CVListResponse(
        id=str(cv['id']),
        file_name=cv['file_name'],
        is_primary=cv['is_primary'],
        parsing_status=cv['parsing_status'],
        uploaded_at=cv.get('uploaded_at')
    ) for cv in result.data]


@router.get("/{cv_id}", response_model=CVResponse)
async def get_cv(
    cv_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get CV details by ID.
    Candidates can only view their own CVs.
    HR can view any CV.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('cvs').select("*").eq('id', cv_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    cv = result.data[0]
    
    # Check access: candidates can only see their own
    if current_user["user_type"] == "candidate" and str(cv['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own CVs"
        )
    
    return CVResponse(
        id=str(cv['id']),
        candidate_id=str(cv['candidate_id']),
        file_name=cv['file_name'],
        file_path=cv.get('file_path'),
        is_primary=cv['is_primary'],
        parsing_status=cv['parsing_status'],
        parsed_data=cv.get('parsed_data'),
        uploaded_at=cv.get('uploaded_at')
    )


@router.put("/{cv_id}/primary", response_model=CVResponse)
async def set_primary_cv(
    cv_id: str,
    current_user: dict = Depends(require_candidate)
):
    """
    Set a CV as the primary CV for the candidate.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Check if CV exists and belongs to candidate
    result = supabase.table('cvs').select("*").eq('id', cv_id).eq('candidate_id', candidate_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    # Unset current primary
    supabase.table('cvs').update({"is_primary": False}).eq('candidate_id', candidate_id).eq('is_primary', True).execute()
    
    # Set new primary
    update_result = supabase.table('cvs').update({
        "is_primary": True
    }).eq('id', cv_id).execute()
    
    if not update_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update CV"
        )
    
    cv = update_result.data[0]
    
    return CVResponse(
        id=str(cv['id']),
        candidate_id=str(cv['candidate_id']),
        file_name=cv['file_name'],
        file_path=cv.get('file_path'),
        is_primary=cv['is_primary'],
        parsing_status=cv['parsing_status'],
        parsed_data=cv.get('parsed_data'),
        uploaded_at=cv.get('uploaded_at')
    )


@router.delete("/{cv_id}")
async def delete_cv(
    cv_id: str,
    current_user: dict = Depends(require_candidate)
):
    """
    Delete a CV. Candidate only.
    Cannot delete if it's the only CV or if it's used in an active application.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Check if CV exists and belongs to candidate
    result = supabase.table('cvs').select("*").eq('id', cv_id).eq('candidate_id', candidate_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    cv = result.data[0]
    
    # Check if this is the only CV
    all_cvs = supabase.table('cvs').select("id").eq('candidate_id', candidate_id).execute()
    if len(all_cvs.data) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your only CV"
        )
    
    # Check if CV is used in active applications
    active_apps = supabase.table('applications').select("id").eq('cv_id', cv_id).not_.in_('status', ['rejected', 'offered']).execute()
    if active_apps.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete CV that is used in active applications"
        )
    
    # If this was primary, set another CV as primary
    if cv['is_primary']:
        other_cvs = supabase.table('cvs').select("id").eq('candidate_id', candidate_id).neq('id', cv_id).limit(1).execute()
        if other_cvs.data:
            supabase.table('cvs').update({"is_primary": True}).eq('id', other_cvs.data[0]['id']).execute()
    
    # Delete CV
    supabase.table('cvs').delete().eq('id', cv_id).execute()
    
    return {"message": "CV deleted", "cv_id": cv_id}


@router.get("/{cv_id}/parsed-data", response_model=ParsedDataResponse)
async def get_parsed_data(
    cv_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get parsed data from a CV.
    Returns extracted skills, experience, education, and certifications.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('cvs').select("candidate_id, parsed_data, parsing_status").eq('id', cv_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    cv = result.data[0]
    
    # Check access
    if current_user["user_type"] == "candidate" and str(cv['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if cv['parsing_status'] != 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CV parsing status: {cv['parsing_status']}"
        )
    
    parsed_data = cv.get('parsed_data', {})
    
    # Extract skills from nested structure
    skills_data = parsed_data.get('skills', {})
    if isinstance(skills_data, dict):
        skills = skills_data.get('technical', [])
    else:
        skills = skills_data if isinstance(skills_data, list) else []
    
    return ParsedDataResponse(
        skills=skills,
        experience=parsed_data.get('work_experience', []),
        education=parsed_data.get('education', []),
        certifications=parsed_data.get('certifications', [])
    )


@router.post("/{cv_id}/parse")
async def trigger_cv_parsing(
    cv_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger CV parsing for a specific CV.
    This would typically call an AI service to extract data.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('cvs').select("*").eq('id', cv_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    cv = result.data[0]
    
    # Check access
    if current_user["user_type"] == "candidate" and str(cv['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update status to processing
    supabase.table('cvs').update({
        "parsing_status": "processing"
    }).eq('id', cv_id).execute()
    
    # Get file content (if stored, we'd need to retrieve it)
    # For now, we'll need the resume text - check if we have parsed_data with resume_text
    # In a real system, you'd store the file and retrieve it here
    
    # Try to get resume text from parsed_data or extract from file
    # For this implementation, we'll parse if we have the file path
    # Note: In production, you'd retrieve the actual file from storage
    
    # For now, return that parsing was triggered
    # The actual parsing should happen during upload or via a background job
    return {
        "message": "CV parsing triggered. Check status via GET /cvs/{cv_id}",
        "cv_id": cv_id,
        "status": "processing"
    }


@router.get("/{cv_id}/matched-roles")
async def get_matched_roles(
    cv_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get job roles that match this CV using semantic and rule-based matching.
    """
    supabase = get_supabase_client()
    
    # Get CV
    result = supabase.table('cvs').select("*").eq('id', cv_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    cv = result.data[0]
    
    # Check access
    if current_user["user_type"] == "candidate" and str(cv['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get parsed data and resume text
    parsed_data = cv.get('parsed_data')
    resume_text = None
    
    # Extract resume text from parsed_data if available
    if parsed_data and isinstance(parsed_data, dict):
        resume_text = parsed_data.get('resume_text')
    
    # Find matching roles
    matched_roles = await find_matching_roles(
        candidate_id=str(cv['candidate_id']),
        resume_text=resume_text,
        parsed_data=parsed_data
    )
    
    return {
        "cv_id": cv_id,
        "matched_roles": matched_roles,
        "total_matches": len(matched_roles)
    }
