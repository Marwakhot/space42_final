"""
Applications router for managing job applications.
Handles candidate applications, status updates, and eligibility checking.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import json

from database import get_supabase_client
from dependencies import get_current_user, require_hr, require_candidate

router = APIRouter(prefix="/applications", tags=["Applications"])


# ============ Constants ============

APPLICATION_STATUSES = [
    "applied",
    "under_ai_review", 
    "shortlisted",
    "interview_scheduled",
    "interview_completed",
    "rejected",
    "offered"
]

VALID_TRANSITIONS = {
    "applied": ["under_ai_review", "shortlisted", "interview_scheduled", "rejected"],
    "under_ai_review": ["shortlisted", "interview_scheduled", "rejected"],
    "shortlisted": ["interview_scheduled", "rejected", "offered"],
    "interview_scheduled": ["interview_completed", "rejected", "offered"],
    "interview_completed": ["offered", "rejected"],
    "rejected": [],
    "offered": []
}


# ============ Request/Response Models ============

class ApplicationCreate(BaseModel):
    job_role_id: str
    cv_id: Optional[str] = None  # If not provided, uses primary CV
    cover_letter: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class EligibilityDetails(BaseModel):
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    explanation: str


class ApplicationResponse(BaseModel):
    id: str
    candidate_id: str
    job_role_id: str
    cv_id: Optional[str] = None
    status: str
    technical_score: Optional[float] = None
    behavioral_score: Optional[float] = None
    combined_score: Optional[float] = None
    rank_in_role: Optional[int] = None
    eligibility_check_passed: Optional[bool] = None
    eligibility_details: Optional[dict] = None
    parameter_scores: Optional[dict] = None  # Behavioral assessment breakdown
    feedback_summary: Optional[str] = None   # AI feedback summary
    interview_scheduled_at: Optional[str] = None
    interview_type: Optional[str] = None
    interview_with: Optional[str] = None
    interview_link: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ApplicationWithJobResponse(ApplicationResponse):
    """Application response with job details included."""
    job_title: Optional[str] = None
    job_department: Optional[str] = None


class EligibilityCheckResponse(BaseModel):
    eligible: bool
    matched_skills: List[str]
    missing_skills: List[str]
    explanation: str


# ============ Helper Functions ============

def check_eligibility(cv_skills: List[str], job_non_negotiable: List[str]) -> dict:
    """
    Check if candidate's skills meet job's non-negotiable requirements.
    Returns eligibility status with matched/missing skills.
    """
    if not cv_skills:
        cv_skills = []
    if not job_non_negotiable:
        job_non_negotiable = []
    
    # Normalize skills for comparison (lowercase)
    cv_skills_lower = [s.lower().strip() for s in cv_skills]
    
    matched = []
    missing = []
    
    for skill in job_non_negotiable:
        if skill.lower().strip() in cv_skills_lower:
            matched.append(skill)
        else:
            missing.append(skill)
    
    is_eligible = len(missing) == 0
    
    if is_eligible:
        explanation = "All required skills matched"
    else:
        explanation = f"Missing required skills: {', '.join(missing)}"
    
    return {
        "eligible": is_eligible,
        "matched_skills": matched,
        "missing_skills": missing,
        "explanation": explanation
    }


def validate_status_transition(current_status: str, new_status: str) -> bool:
    """Check if status transition is valid."""
    if current_status not in VALID_TRANSITIONS:
        return False
    return new_status in VALID_TRANSITIONS[current_status]


# ============ Endpoints ============

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    request: ApplicationCreate,
    current_user: dict = Depends(require_candidate)
):
    """
    Submit a new job application. Candidate only.
    Performs eligibility check based on CV skills and job requirements.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Check if job role exists and is active
    job_result = supabase.table('job_roles').select("*").eq('id', request.job_role_id).eq('is_active', True).execute()
    if not job_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job role not found or inactive"
        )
    job = job_result.data[0]
    
    # Check for existing application
    existing = supabase.table('applications').select("id").eq('candidate_id', candidate_id).eq('job_role_id', request.job_role_id).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied for this job"
        )
    
    # Get CV (use provided cv_id or find primary CV)
    cv_id = request.cv_id
    cv_data = None
    
    if cv_id:
        cv_result = supabase.table('cvs').select("*").eq('id', cv_id).eq('candidate_id', candidate_id).execute()
        if not cv_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV not found"
            )
        cv_data = cv_result.data[0]
    else:
        # Get primary CV
        cv_result = supabase.table('cvs').select("*").eq('candidate_id', candidate_id).eq('is_primary', True).execute()
        if cv_result.data:
            cv_data = cv_result.data[0]
            cv_id = cv_data['id']
    
    # Perform eligibility check if CV has parsed data
    eligibility_passed = True
    eligibility_details = {"matched_skills": [], "missing_skills": [], "explanation": "No CV data for eligibility check"}
    
    if cv_data and cv_data.get('parsed_data'):
        parsed_data = cv_data['parsed_data']
        # Extract skills from nested structure
        skills_data = parsed_data.get('skills', {})
        if isinstance(skills_data, dict):
            cv_skills = skills_data.get('technical', [])
        else:
            cv_skills = skills_data if isinstance(skills_data, list) else []
        
        job_non_negotiable = job.get('non_negotiable_skills', [])
        # Parse JSON if needed
        if isinstance(job_non_negotiable, str):
            job_non_negotiable = json.loads(job_non_negotiable) if job_non_negotiable else []
        
        eligibility_result = check_eligibility(cv_skills, job_non_negotiable)
        eligibility_passed = eligibility_result['eligible']
        eligibility_details = eligibility_result
    
    # Create application
    new_application = {
        "candidate_id": candidate_id,
        "job_role_id": request.job_role_id,
        "cv_id": cv_id,
        "status": "applied",
        "cover_letter": request.cover_letter,
        "eligibility_check_passed": eligibility_passed,
        "eligibility_details": eligibility_details
    }
    
    result = supabase.table('applications').insert(new_application).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application"
        )
    
    app = result.data[0]
    
    return ApplicationResponse(
        id=str(app['id']),
        candidate_id=str(app['candidate_id']),
        job_role_id=str(app['job_role_id']),
        cv_id=str(app['cv_id']) if app.get('cv_id') else None,
        status=app['status'],
        technical_score=app.get('technical_score'),
        behavioral_score=app.get('behavioral_score'),
        combined_score=app.get('combined_score'),
        rank_in_role=app.get('rank_in_role'),
        eligibility_check_passed=app.get('eligibility_check_passed'),
        eligibility_details=app.get('eligibility_details'),
        created_at=app.get('created_at'),
        updated_at=app.get('updated_at')
    )


@router.get("", response_model=List[ApplicationResponse])
async def list_applications(
    job_role_id: Optional[str] = Query(None, description="Filter by job role"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: dict = Depends(require_hr)
):
    """
    List all applications. HR only.
    Supports filtering by job role and status.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('applications').select("*")
    
    if job_role_id:
        query = query.eq('job_role_id', job_role_id)
    
    if status_filter:
        query = query.eq('status', status_filter)
    
    result = query.order('applied_date', desc=True).execute()
    
    # Fetch behavioral assessment details for each application
    applications = []
    for app in result.data:
        # Try to get behavioral assessment scores
        parameter_scores = None
        feedback_summary = None
        try:
            assessment_result = supabase.table('behavioral_assessment_scores').select(
                "parameter_scores, feedback_summary"
            ).eq('application_id', app['id']).order('created_at', desc=True).limit(1).execute()
            
            if assessment_result.data:
                parameter_scores = assessment_result.data[0].get('parameter_scores')
                feedback_summary = assessment_result.data[0].get('feedback_summary')
        except:
            pass  # Table may not exist or other error
        
        applications.append(ApplicationResponse(
            id=str(app['id']),
            candidate_id=str(app['candidate_id']),
            job_role_id=str(app['job_role_id']),
            cv_id=str(app['cv_id']) if app.get('cv_id') else None,
            status=app['status'],
            technical_score=app.get('technical_score'),
            behavioral_score=app.get('behavioral_score'),
            combined_score=app.get('combined_score'),
            rank_in_role=app.get('rank_in_role'),
            eligibility_check_passed=app.get('eligibility_check_passed'),
            eligibility_details=app.get('eligibility_details'),
            parameter_scores=parameter_scores,
            feedback_summary=feedback_summary,
            interview_scheduled_at=app.get('interview_scheduled_at'),
            interview_type=app.get('interview_type'),
            interview_with=app.get('interview_with'),
            interview_link=app.get('interview_link'),
            created_at=app.get('created_at'),
            updated_at=app.get('updated_at')
        ))
    
    return applications


@router.get("/my", response_model=List[ApplicationWithJobResponse])
async def get_my_applications(
    current_user: dict = Depends(require_candidate)
):
    """
    Get current candidate's own applications with job details.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Get applications
    apps_result = supabase.table('applications').select("*").eq('candidate_id', candidate_id).order('applied_date', desc=True).execute()
    
    applications = []
    for app in apps_result.data:
        # Get job details
        job_result = supabase.table('job_roles').select("title, department").eq('id', app['job_role_id']).execute()
        job_title = None
        job_department = None
        if job_result.data:
            job_title = job_result.data[0].get('title')
            job_department = job_result.data[0].get('department')
        
        # Get behavioral assessment details (only parameter_scores and feedback_summary for candidate view is optional)
        parameter_scores = None
        feedback_summary = None
        
        applications.append(ApplicationWithJobResponse(
            id=str(app['id']),
            candidate_id=str(app['candidate_id']),
            job_role_id=str(app['job_role_id']),
            cv_id=str(app['cv_id']) if app.get('cv_id') else None,
            status=app['status'],
            technical_score=app.get('technical_score'),
            behavioral_score=app.get('behavioral_score'),
            combined_score=app.get('combined_score'),
            rank_in_role=app.get('rank_in_role'),
            eligibility_check_passed=app.get('eligibility_check_passed'),
            eligibility_details=app.get('eligibility_details'),
            parameter_scores=parameter_scores,
            feedback_summary=feedback_summary,
            interview_scheduled_at=app.get('interview_scheduled_at'),
            interview_type=app.get('interview_type'),
            interview_with=app.get('interview_with'),
            interview_link=app.get('interview_link'),
            created_at=app.get('created_at'),
            updated_at=app.get('updated_at'),
            job_title=job_title,
            job_department=job_department
        ))
    
    return applications


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific application by ID.
    Candidates can only view their own applications.
    HR can view any application.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('applications').select("*").eq('id', application_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    app = result.data[0]
    
    # Check access: candidates can only see their own
    if current_user["user_type"] == "candidate" and str(app['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own applications"
        )
    
    return ApplicationResponse(
        id=str(app['id']),
        candidate_id=str(app['candidate_id']),
        job_role_id=str(app['job_role_id']),
        cv_id=str(app['cv_id']) if app.get('cv_id') else None,
        status=app['status'],
        technical_score=app.get('technical_score'),
        behavioral_score=app.get('behavioral_score'),
        combined_score=app.get('combined_score'),
        rank_in_role=app.get('rank_in_role'),
        eligibility_check_passed=app.get('eligibility_check_passed'),
        eligibility_details=app.get('eligibility_details'),
        created_at=app.get('created_at'),
        updated_at=app.get('updated_at')
    )


@router.put("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: str,
    request: ApplicationStatusUpdate,
    current_user: dict = Depends(require_hr)
):
    """
    Update application status. HR only.
    Validates status transitions.
    """
    supabase = get_supabase_client()
    
    if request.status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(APPLICATION_STATUSES)}"
        )
    
    # Get current application
    existing = supabase.table('applications').select("*").eq('id', application_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    current_app = existing.data[0]
    current_status = current_app['status']
    
    # Validate transition
    if not validate_status_transition(current_status, request.status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current_status}' to '{request.status}'"
        )
    
    # Update application
    update_data = {
        "status": request.status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase.table('applications').update(update_data).eq('id', application_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application"
        )
    
    app = result.data[0]
    
    # Send email notifications based on status change
    if request.status == 'rejected':
        # Send personalized rejection email
        try:
            from services.email_service import send_rejection_email
            
            # Get candidate info
            candidate_result = supabase.table('candidates').select("*").eq('id', app['candidate_id']).execute()
            candidate = candidate_result.data[0] if candidate_result.data else None
            
            # Get job info
            job_result = supabase.table('job_roles').select("title, description").eq('id', app['job_role_id']).execute()
            job_title = job_result.data[0]['title'] if job_result.data else "the position"
            job_description = job_result.data[0].get('description', '') if job_result.data else ""
            
            # Get feedback from multiple sources
            feedback_parts = []
            
            # 1. Get HR notes/feedback - THIS IS THE KEY ADDITION
            try:
                hr_feedback_result = supabase.table('hr_feedback').select(
                    "weaknesses, missing_requirements, additional_notes, recommendation"
                ).eq('application_id', app['id']).order('created_at', desc=True).execute()
                
                if hr_feedback_result.data:
                    for fb in hr_feedback_result.data:
                        if fb.get('weaknesses'):
                            feedback_parts.append(f"Areas for improvement: {fb['weaknesses']}")
                        if fb.get('missing_requirements'):
                            feedback_parts.append(f"Skills to develop: {fb['missing_requirements']}")
            except:
                pass
            
            # 2. Get behavioral assessment feedback
            try:
                assessment_result = supabase.table('behavioral_assessment_scores').select(
                    "summary"
                ).eq('application_id', app['id']).limit(1).execute()
                if assessment_result.data and assessment_result.data[0].get('summary'):
                    feedback_parts.append(assessment_result.data[0]['summary'])
            except:
                pass
            
            # Combine all feedback
            feedback_summary = ". ".join(feedback_parts[:2]) if feedback_parts else None  # Limit to 2 pieces
            
            # Get CV/resume text for AI generation
            resume_text = ""
            if app.get('cv_id'):
                try:
                    cv_result = supabase.table('cvs').select("parsed_data").eq('id', app['cv_id']).execute()
                    if cv_result.data and cv_result.data[0].get('parsed_data'):
                        parsed = cv_result.data[0]['parsed_data']
                        skills = parsed.get('skills', {})
                        if isinstance(skills, dict):
                            resume_text = ", ".join(skills.get('technical', []))
                except:
                    pass
            
            if candidate:
                # Fire and forget - don't block the response
                import asyncio
                candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
                if not candidate_name:
                    candidate_name = candidate['email'].split('@')[0]
                    
                asyncio.create_task(send_rejection_email(
                    candidate_email=candidate['email'],
                    candidate_name=candidate_name,
                    job_title=job_title,
                    feedback_summary=feedback_summary,
                    role_description=job_description,
                    candidate_resume=resume_text
                ))
        except Exception as e:
            print(f"Failed to send rejection email: {e}")
    
    elif request.status == 'offered':
        # Send offer email
        try:
            from services.email_service import send_offer_email
            
            candidate_result = supabase.table('candidates').select("*").eq('id', app['candidate_id']).execute()
            candidate = candidate_result.data[0] if candidate_result.data else None
            
            job_result = supabase.table('job_roles').select("title").eq('id', app['job_role_id']).execute()
            job_title = job_result.data[0]['title'] if job_result.data else "the position"
            
            if candidate:
                import asyncio
                candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
                if not candidate_name:
                    candidate_name = candidate['email'].split('@')[0]
                    
                asyncio.create_task(send_offer_email(
                    candidate_email=candidate['email'],
                    candidate_name=candidate_name,
                    job_title=job_title
                ))
        except Exception as e:
            print(f"Failed to send offer email: {e}")
    
    return ApplicationResponse(
        id=str(app['id']),
        candidate_id=str(app['candidate_id']),
        job_role_id=str(app['job_role_id']),
        cv_id=str(app['cv_id']) if app.get('cv_id') else None,
        status=app['status'],
        technical_score=app.get('technical_score'),
        behavioral_score=app.get('behavioral_score'),
        combined_score=app.get('combined_score'),
        rank_in_role=app.get('rank_in_role'),
        eligibility_check_passed=app.get('eligibility_check_passed'),
        eligibility_details=app.get('eligibility_details'),
        created_at=app.get('created_at'),
        updated_at=app.get('updated_at')
    )


# ============ Interview Scheduling ============

class InterviewScheduleRequest(BaseModel):
    scheduled_at: str  # ISO datetime string
    interview_type: str = "Video Call"  # Video Call, Phone Call, In-Person
    interviewer: str = "HR Team"
    meeting_link: Optional[str] = None


@router.post("/{application_id}/schedule-interview", response_model=ApplicationResponse)
async def schedule_interview(
    application_id: str,
    request: InterviewScheduleRequest,
    current_user: dict = Depends(require_hr)
):
    """
    Schedule an interview for an application. HR only.
    Updates the application with interview details and sets status to 'interview_scheduled'.
    """
    supabase = get_supabase_client()
    
    # Get current application
    existing = supabase.table('applications').select("*").eq('id', application_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    current_app = existing.data[0]
    
    # Can't schedule interview for rejected applications
    if current_app['status'] == 'rejected':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule interview for rejected application"
        )
    
    # Update application with interview details
    update_data = {
        "status": "interview_scheduled",
        "interview_scheduled_at": request.scheduled_at,
        "interview_type": request.interview_type,
        "interview_with": request.interviewer,
        "interview_link": request.meeting_link,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase.table('applications').update(update_data).eq('id', application_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule interview"
        )
    
    app = result.data[0]
    
    # Send interview scheduled email
    try:
        from services.email_service import send_interview_scheduled_email
        
        candidate_result = supabase.table('candidates').select("*").eq('id', app['candidate_id']).execute()
        candidate = candidate_result.data[0] if candidate_result.data else None
        
        job_result = supabase.table('job_roles').select("title").eq('id', app['job_role_id']).execute()
        job_title = job_result.data[0]['title'] if job_result.data else "the position"
        
        if candidate:
            import asyncio
            candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
            if not candidate_name:
                candidate_name = candidate['email'].split('@')[0]
                
            asyncio.create_task(send_interview_scheduled_email(
                candidate_email=candidate['email'],
                candidate_name=candidate_name,
                job_title=job_title,
                interview_date=request.scheduled_at,
                interview_type=request.interview_type,
                interviewer=request.interviewer,
                meeting_link=request.meeting_link
            ))
    except Exception as e:
        print(f"Failed to send interview email: {e}")
    
    return ApplicationResponse(
        id=str(app['id']),
        candidate_id=str(app['candidate_id']),
        job_role_id=str(app['job_role_id']),
        cv_id=str(app['cv_id']) if app.get('cv_id') else None,
        status=app['status'],
        technical_score=app.get('technical_score'),
        behavioral_score=app.get('behavioral_score'),
        combined_score=app.get('combined_score'),
        rank_in_role=app.get('rank_in_role'),
        eligibility_check_passed=app.get('eligibility_check_passed'),
        eligibility_details=app.get('eligibility_details'),
        interview_scheduled_at=app.get('interview_scheduled_at'),
        interview_type=app.get('interview_type'),
        interview_with=app.get('interview_with'),
        interview_link=app.get('interview_link'),
        created_at=app.get('created_at'),
        updated_at=app.get('updated_at')
    )


@router.delete("/{application_id}")
async def withdraw_application(
    application_id: str,
    current_user: dict = Depends(require_candidate)
):
    """
    Withdraw (delete) an application. Candidate only.
    Can only withdraw applications that haven't progressed past 'applied' status.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Get application
    existing = supabase.table('applications').select("*").eq('id', application_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    app = existing.data[0]
    
    # Check ownership
    if str(app['candidate_id']) != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only withdraw your own applications"
        )
    
    # Can only withdraw if still in early stage
    if app['status'] not in ['applied', 'under_ai_review']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot withdraw application at this stage"
        )
    
    # Delete application
    supabase.table('applications').delete().eq('id', application_id).execute()
    
    return {"message": "Application withdrawn", "application_id": application_id}


@router.get("/job/{job_role_id}/rankings", response_model=List[ApplicationResponse])
async def get_job_rankings(
    job_role_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Get ranked candidates for a specific job role. HR only.
    Returns applications ordered by combined_score.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('applications').select("*").eq('job_role_id', job_role_id).eq('eligibility_check_passed', True).order('combined_score', desc=True).execute()
    
    return [ApplicationResponse(
        id=str(app['id']),
        candidate_id=str(app['candidate_id']),
        job_role_id=str(app['job_role_id']),
        cv_id=str(app['cv_id']) if app.get('cv_id') else None,
        status=app['status'],
        technical_score=app.get('technical_score'),
        behavioral_score=app.get('behavioral_score'),
        combined_score=app.get('combined_score'),
        rank_in_role=app.get('rank_in_role'),
        eligibility_check_passed=app.get('eligibility_check_passed'),
        eligibility_details=app.get('eligibility_details'),
        created_at=app.get('created_at'),
        updated_at=app.get('updated_at')
    ) for app in result.data]


@router.post("/{application_id}/check-eligibility", response_model=EligibilityCheckResponse)
async def recheck_eligibility(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Re-check eligibility for an application.
    Useful after CV is updated or re-parsed.
    """
    supabase = get_supabase_client()
    
    # Get application
    app_result = supabase.table('applications').select("*").eq('id', application_id).execute()
    if not app_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    app = app_result.data[0]
    
    # Check access
    if current_user["user_type"] == "candidate" and str(app['candidate_id']) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get CV
    if not app.get('cv_id'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CV attached to application"
        )
    
    cv_result = supabase.table('cvs').select("parsed_data").eq('id', app['cv_id']).execute()
    if not cv_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    
    cv_data = cv_result.data[0]
    
    # Get job
    job_result = supabase.table('job_roles').select("non_negotiable_skills").eq('id', app['job_role_id']).execute()
    if not job_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job role not found"
        )
    
    job = job_result.data[0]
    
    # Check eligibility
    cv_skills = cv_data.get('parsed_data', {}).get('skills', []) if cv_data.get('parsed_data') else []
    job_non_negotiable = job.get('non_negotiable_skills', [])
    
    eligibility_result = check_eligibility(cv_skills, job_non_negotiable)
    
    # Update application
    supabase.table('applications').update({
        "eligibility_check_passed": eligibility_result['eligible'],
        "eligibility_details": eligibility_result,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq('id', application_id).execute()
    
    return EligibilityCheckResponse(**eligibility_result)
