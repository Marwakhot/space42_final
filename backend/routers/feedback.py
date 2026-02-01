"""
HR Feedback router for managing interview feedback and candidate evaluations.
Handles feedback creation, retrieval, and learning loop integration.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from database import get_supabase_client
from dependencies import get_current_user, require_hr

router = APIRouter(prefix="/feedback", tags=["HR Feedback"])


# ============ Constants ============

FEEDBACK_TYPES = ["interview", "screening", "technical_review", "final_decision"]
RECOMMENDATIONS = ["strong_hire", "hire", "no_hire", "strong_no_hire"]


# ============ Request/Response Models ============

class FeedbackCreate(BaseModel):
    application_id: str
    interview_id: Optional[str] = None  # Optional, if feedback is for specific interview
    feedback_type: str
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    missing_requirements: Optional[str] = None
    additional_notes: Optional[str] = None
    role_fit_score: Optional[int] = None  # 1-10
    recommendation: Optional[str] = None


class FeedbackUpdate(BaseModel):
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    missing_requirements: Optional[str] = None
    additional_notes: Optional[str] = None
    role_fit_score: Optional[int] = None
    recommendation: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    application_id: str
    interview_id: Optional[str] = None
    hr_user_id: str
    feedback_type: str
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    missing_requirements: Optional[str] = None
    additional_notes: Optional[str] = None
    role_fit_score: Optional[int] = None
    recommendation: Optional[str] = None
    is_used_for_training: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FeedbackWithHRResponse(FeedbackResponse):
    """Feedback with HR user details."""
    hr_name: Optional[str] = None
    hr_email: Optional[str] = None


# ============ Endpoints ============

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    request: FeedbackCreate,
    current_user: dict = Depends(require_hr)
):
    """
    Create HR feedback for an application. HR only.
    """
    supabase = get_supabase_client()
    hr_user_id = current_user["user_id"]
    
    # Validate feedback type
    if request.feedback_type not in FEEDBACK_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid feedback type. Must be one of: {', '.join(FEEDBACK_TYPES)}"
        )
    
    # Validate recommendation if provided
    if request.recommendation and request.recommendation not in RECOMMENDATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recommendation. Must be one of: {', '.join(RECOMMENDATIONS)}"
        )
    
    # Validate role_fit_score if provided
    if request.role_fit_score is not None:
        if not 1 <= request.role_fit_score <= 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role fit score must be between 1 and 10"
            )
    
    # Check if application exists
    app_result = supabase.table('applications').select("id").eq('id', request.application_id).execute()
    if not app_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Check if interview exists (if provided)
    if request.interview_id:
        interview_result = supabase.table('interviews').select("id").eq('id', request.interview_id).execute()
        if not interview_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
    
    # Create feedback
    new_feedback = {
        "application_id": request.application_id,
        "interview_id": request.interview_id,
        "hr_user_id": hr_user_id,
        "feedback_type": request.feedback_type,
        "strengths": request.strengths,
        "weaknesses": request.weaknesses,
        "missing_requirements": request.missing_requirements,
        "additional_notes": request.additional_notes,
        "role_fit_score": request.role_fit_score,
        "recommendation": request.recommendation,
        "is_used_for_training": False
    }
    
    result = supabase.table('hr_feedback').insert(new_feedback).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feedback"
        )
    
    feedback = result.data[0]
    
    return FeedbackResponse(
        id=str(feedback['id']),
        application_id=str(feedback['application_id']),
        interview_id=str(feedback['interview_id']) if feedback.get('interview_id') else None,
        hr_user_id=str(feedback['hr_user_id']),
        feedback_type=feedback['feedback_type'],
        strengths=feedback.get('strengths'),
        weaknesses=feedback.get('weaknesses'),
        missing_requirements=feedback.get('missing_requirements'),
        additional_notes=feedback.get('additional_notes'),
        role_fit_score=feedback.get('role_fit_score'),
        recommendation=feedback.get('recommendation'),
        is_used_for_training=feedback.get('is_used_for_training', False),
        created_at=feedback.get('created_at'),
        updated_at=feedback.get('updated_at')
    )


@router.get("", response_model=List[FeedbackWithHRResponse])
async def list_feedback(
    application_id: Optional[str] = Query(None, description="Filter by application"),
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type"),
    current_user: dict = Depends(require_hr)
):
    """
    List HR feedback. HR only.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('hr_feedback').select("*")
    
    if application_id:
        query = query.eq('application_id', application_id)
    
    if feedback_type:
        query = query.eq('feedback_type', feedback_type)
    
    result = query.order('created_at', desc=True).execute()
    
    feedbacks = []
    for feedback in result.data:
        # Get HR user details
        hr_result = supabase.table('hr_users').select("first_name, last_name, email").eq('id', feedback['hr_user_id']).execute()
        hr_name = None
        hr_email = None
        if hr_result.data:
            hr = hr_result.data[0]
            hr_name = f"{hr['first_name']} {hr['last_name']}"
            hr_email = hr['email']
        
        feedbacks.append(FeedbackWithHRResponse(
            id=str(feedback['id']),
            application_id=str(feedback['application_id']),
            interview_id=str(feedback['interview_id']) if feedback.get('interview_id') else None,
            hr_user_id=str(feedback['hr_user_id']),
            feedback_type=feedback['feedback_type'],
            strengths=feedback.get('strengths'),
            weaknesses=feedback.get('weaknesses'),
            missing_requirements=feedback.get('missing_requirements'),
            additional_notes=feedback.get('additional_notes'),
            role_fit_score=feedback.get('role_fit_score'),
            recommendation=feedback.get('recommendation'),
            is_used_for_training=feedback.get('is_used_for_training', False),
            created_at=feedback.get('created_at'),
            updated_at=feedback.get('updated_at'),
            hr_name=hr_name,
            hr_email=hr_email
        ))
    
    return feedbacks


@router.get("/application/{application_id}", response_model=List[FeedbackWithHRResponse])
async def get_application_feedback(
    application_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Get all feedback for a specific application. HR only.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('hr_feedback').select("*").eq('application_id', application_id).order('created_at', desc=True).execute()
    
    feedbacks = []
    for feedback in result.data:
        # Get HR user details
        hr_result = supabase.table('hr_users').select("first_name, last_name, email").eq('id', feedback['hr_user_id']).execute()
        hr_name = None
        hr_email = None
        if hr_result.data:
            hr = hr_result.data[0]
            hr_name = f"{hr['first_name']} {hr['last_name']}"
            hr_email = hr['email']
        
        feedbacks.append(FeedbackWithHRResponse(
            id=str(feedback['id']),
            application_id=str(feedback['application_id']),
            interview_id=str(feedback['interview_id']) if feedback.get('interview_id') else None,
            hr_user_id=str(feedback['hr_user_id']),
            feedback_type=feedback['feedback_type'],
            strengths=feedback.get('strengths'),
            weaknesses=feedback.get('weaknesses'),
            missing_requirements=feedback.get('missing_requirements'),
            additional_notes=feedback.get('additional_notes'),
            role_fit_score=feedback.get('role_fit_score'),
            recommendation=feedback.get('recommendation'),
            is_used_for_training=feedback.get('is_used_for_training', False),
            created_at=feedback.get('created_at'),
            updated_at=feedback.get('updated_at'),
            hr_name=hr_name,
            hr_email=hr_email
        ))
    
    return feedbacks


@router.get("/{feedback_id}", response_model=FeedbackWithHRResponse)
async def get_feedback(
    feedback_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Get specific feedback by ID. HR only.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('hr_feedback').select("*").eq('id', feedback_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    feedback = result.data[0]
    
    # Get HR user details
    hr_result = supabase.table('hr_users').select("first_name, last_name, email").eq('id', feedback['hr_user_id']).execute()
    hr_name = None
    hr_email = None
    if hr_result.data:
        hr = hr_result.data[0]
        hr_name = f"{hr['first_name']} {hr['last_name']}"
        hr_email = hr['email']
    
    return FeedbackWithHRResponse(
        id=str(feedback['id']),
        application_id=str(feedback['application_id']),
        interview_id=str(feedback['interview_id']) if feedback.get('interview_id') else None,
        hr_user_id=str(feedback['hr_user_id']),
        feedback_type=feedback['feedback_type'],
        strengths=feedback.get('strengths'),
        weaknesses=feedback.get('weaknesses'),
        missing_requirements=feedback.get('missing_requirements'),
        additional_notes=feedback.get('additional_notes'),
        role_fit_score=feedback.get('role_fit_score'),
        recommendation=feedback.get('recommendation'),
        is_used_for_training=feedback.get('is_used_for_training', False),
        created_at=feedback.get('created_at'),
        updated_at=feedback.get('updated_at'),
        hr_name=hr_name,
        hr_email=hr_email
    )


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    request: FeedbackUpdate,
    current_user: dict = Depends(require_hr)
):
    """
    Update feedback. HR only.
    Only the HR who created the feedback can update it.
    """
    supabase = get_supabase_client()
    hr_user_id = current_user["user_id"]
    
    # Check if feedback exists
    existing = supabase.table('hr_feedback').select("*").eq('id', feedback_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    feedback = existing.data[0]
    
    # Check ownership
    if str(feedback['hr_user_id']) != hr_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own feedback"
        )
    
    # Validate recommendation if provided
    if request.recommendation and request.recommendation not in RECOMMENDATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recommendation. Must be one of: {', '.join(RECOMMENDATIONS)}"
        )
    
    # Validate role_fit_score if provided
    if request.role_fit_score is not None:
        if not 1 <= request.role_fit_score <= 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role fit score must be between 1 and 10"
            )
    
    # Build update data
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if request.strengths is not None:
        update_data["strengths"] = request.strengths
    if request.weaknesses is not None:
        update_data["weaknesses"] = request.weaknesses
    if request.missing_requirements is not None:
        update_data["missing_requirements"] = request.missing_requirements
    if request.additional_notes is not None:
        update_data["additional_notes"] = request.additional_notes
    if request.role_fit_score is not None:
        update_data["role_fit_score"] = request.role_fit_score
    if request.recommendation is not None:
        update_data["recommendation"] = request.recommendation
    
    result = supabase.table('hr_feedback').update(update_data).eq('id', feedback_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feedback"
        )
    
    updated = result.data[0]
    
    return FeedbackResponse(
        id=str(updated['id']),
        application_id=str(updated['application_id']),
        interview_id=str(updated['interview_id']) if updated.get('interview_id') else None,
        hr_user_id=str(updated['hr_user_id']),
        feedback_type=updated['feedback_type'],
        strengths=updated.get('strengths'),
        weaknesses=updated.get('weaknesses'),
        missing_requirements=updated.get('missing_requirements'),
        additional_notes=updated.get('additional_notes'),
        role_fit_score=updated.get('role_fit_score'),
        recommendation=updated.get('recommendation'),
        is_used_for_training=updated.get('is_used_for_training', False),
        created_at=updated.get('created_at'),
        updated_at=updated.get('updated_at')
    )


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Delete feedback. HR only.
    Only the HR who created the feedback can delete it.
    """
    supabase = get_supabase_client()
    hr_user_id = current_user["user_id"]
    
    # Check if feedback exists
    existing = supabase.table('hr_feedback').select("id, hr_user_id").eq('id', feedback_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    feedback = existing.data[0]
    
    # Check ownership
    if str(feedback['hr_user_id']) != hr_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own feedback"
        )
    
    # Delete feedback
    supabase.table('hr_feedback').delete().eq('id', feedback_id).execute()
    
    return {"message": "Feedback deleted", "feedback_id": feedback_id}


@router.post("/{feedback_id}/mark-for-training")
async def mark_for_training(
    feedback_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Mark feedback as used for AI training/learning loop.
    This helps improve future candidate evaluations.
    """
    supabase = get_supabase_client()
    
    # Check if feedback exists
    existing = supabase.table('hr_feedback').select("id").eq('id', feedback_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Mark for training
    supabase.table('hr_feedback').update({
        "is_used_for_training": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq('id', feedback_id).execute()
    
    return {"message": "Feedback marked for AI training", "feedback_id": feedback_id}
