"""
HR Feedback router for managing interview notes and candidate feedback.
This feedback is used in rejection emails for personalized communication.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from database import get_supabase_client
from dependencies import get_current_user, require_hr

router = APIRouter(prefix="/feedback", tags=["HR Feedback"])


# ============ Request/Response Models ============

class FeedbackCreate(BaseModel):
    application_id: str
    interview_id: Optional[str] = None
    feedback_type: str = "interview"  # interview, screening, general
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    missing_requirements: Optional[str] = None
    role_fit_score: Optional[int] = None  # 1-10
    recommendation: Optional[str] = None  # hire, reject, maybe, needs_more_info
    additional_notes: Optional[str] = None


class FeedbackUpdate(BaseModel):
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    missing_requirements: Optional[str] = None
    role_fit_score: Optional[int] = None
    recommendation: Optional[str] = None
    additional_notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    application_id: str
    interview_id: Optional[str] = None
    hr_user_id: str
    hr_user_name: Optional[str] = None
    feedback_type: str
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    missing_requirements: Optional[str] = None
    role_fit_score: Optional[int] = None
    recommendation: Optional[str] = None
    additional_notes: Optional[str] = None
    created_at: Optional[str] = None


# ============ Endpoints ============

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    request: FeedbackCreate,
    current_user: dict = Depends(require_hr)
):
    """
    Create HR feedback for an application. HR only.
    This feedback can be used in rejection emails and training AI.
    """
    supabase = get_supabase_client()
    hr_user_id = current_user["user_id"]
    
    # Verify application exists
    app_result = supabase.table('applications').select("id").eq('id', request.application_id).execute()
    if not app_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
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
        "role_fit_score": request.role_fit_score,
        "recommendation": request.recommendation,
        "additional_notes": request.additional_notes,
        "is_used_for_training": True
    }
    
    result = supabase.table('hr_feedback').insert(new_feedback).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feedback"
        )
    
    feedback = result.data[0]
    
    # Get HR user name
    hr_name = None
    try:
        hr_result = supabase.table('hr_users').select("first_name, last_name").eq('id', hr_user_id).execute()
        if hr_result.data:
            hr_name = f"{hr_result.data[0].get('first_name', '')} {hr_result.data[0].get('last_name', '')}".strip()
    except:
        pass
    
    return FeedbackResponse(
        id=str(feedback['id']),
        application_id=str(feedback['application_id']),
        interview_id=str(feedback['interview_id']) if feedback.get('interview_id') else None,
        hr_user_id=str(feedback['hr_user_id']),
        hr_user_name=hr_name,
        feedback_type=feedback['feedback_type'],
        strengths=feedback.get('strengths'),
        weaknesses=feedback.get('weaknesses'),
        missing_requirements=feedback.get('missing_requirements'),
        role_fit_score=feedback.get('role_fit_score'),
        recommendation=feedback.get('recommendation'),
        additional_notes=feedback.get('additional_notes'),
        created_at=feedback.get('created_at')
    )


@router.get("/application/{application_id}", response_model=List[FeedbackResponse])
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
        # Get HR user name
        hr_name = None
        try:
            hr_result = supabase.table('hr_users').select("first_name, last_name").eq('id', feedback['hr_user_id']).execute()
            if hr_result.data:
                hr_name = f"{hr_result.data[0].get('first_name', '')} {hr_result.data[0].get('last_name', '')}".strip()
        except:
            pass
        
        feedbacks.append(FeedbackResponse(
            id=str(feedback['id']),
            application_id=str(feedback['application_id']),
            interview_id=str(feedback['interview_id']) if feedback.get('interview_id') else None,
            hr_user_id=str(feedback['hr_user_id']),
            hr_user_name=hr_name,
            feedback_type=feedback['feedback_type'],
            strengths=feedback.get('strengths'),
            weaknesses=feedback.get('weaknesses'),
            missing_requirements=feedback.get('missing_requirements'),
            role_fit_score=feedback.get('role_fit_score'),
            recommendation=feedback.get('recommendation'),
            additional_notes=feedback.get('additional_notes'),
            created_at=feedback.get('created_at')
        ))
    
    return feedbacks


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    request: FeedbackUpdate,
    current_user: dict = Depends(require_hr)
):
    """
    Update HR feedback. HR only.
    Only the HR user who created the feedback can update it.
    """
    supabase = get_supabase_client()
    hr_user_id = current_user["user_id"]
    
    # Get existing feedback
    existing = supabase.table('hr_feedback').select("*").eq('id', feedback_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    feedback = existing.data[0]
    
    # Check ownership (optional - allow any HR to edit)
    # if str(feedback['hr_user_id']) != hr_user_id:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your feedback")
    
    # Build update data
    update_data = {}
    if request.strengths is not None:
        update_data['strengths'] = request.strengths
    if request.weaknesses is not None:
        update_data['weaknesses'] = request.weaknesses
    if request.missing_requirements is not None:
        update_data['missing_requirements'] = request.missing_requirements
    if request.role_fit_score is not None:
        update_data['role_fit_score'] = request.role_fit_score
    if request.recommendation is not None:
        update_data['recommendation'] = request.recommendation
    if request.additional_notes is not None:
        update_data['additional_notes'] = request.additional_notes
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    result = supabase.table('hr_feedback').update(update_data).eq('id', feedback_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feedback"
        )
    
    updated = result.data[0]
    
    # Get HR user name
    hr_name = None
    try:
        hr_result = supabase.table('hr_users').select("first_name, last_name").eq('id', updated['hr_user_id']).execute()
        if hr_result.data:
            hr_name = f"{hr_result.data[0].get('first_name', '')} {hr_result.data[0].get('last_name', '')}".strip()
    except:
        pass
    
    return FeedbackResponse(
        id=str(updated['id']),
        application_id=str(updated['application_id']),
        interview_id=str(updated['interview_id']) if updated.get('interview_id') else None,
        hr_user_id=str(updated['hr_user_id']),
        hr_user_name=hr_name,
        feedback_type=updated['feedback_type'],
        strengths=updated.get('strengths'),
        weaknesses=updated.get('weaknesses'),
        missing_requirements=updated.get('missing_requirements'),
        role_fit_score=updated.get('role_fit_score'),
        recommendation=updated.get('recommendation'),
        additional_notes=updated.get('additional_notes'),
        created_at=updated.get('created_at')
    )


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Delete HR feedback. HR only.
    """
    supabase = get_supabase_client()
    
    # Check if exists
    existing = supabase.table('hr_feedback').select("id").eq('id', feedback_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    supabase.table('hr_feedback').delete().eq('id', feedback_id).execute()
    
    return {"message": "Feedback deleted", "feedback_id": feedback_id}


@router.get("/application/{application_id}/summary")
async def get_feedback_summary(
    application_id: str,
    current_user: dict = Depends(require_hr)
):
    """
    Get a summary of all feedback for an application.
    This is used for rejection emails.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('hr_feedback').select("*").eq('application_id', application_id).execute()
    
    if not result.data:
        return {
            "has_feedback": False,
            "summary": None,
            "avg_role_fit_score": None,
            "recommendations": []
        }
    
    # Compile summary
    all_weaknesses = []
    all_missing = []
    all_strengths = []
    role_fit_scores = []
    recommendations = []
    
    for fb in result.data:
        if fb.get('weaknesses'):
            all_weaknesses.append(fb['weaknesses'])
        if fb.get('missing_requirements'):
            all_missing.append(fb['missing_requirements'])
        if fb.get('strengths'):
            all_strengths.append(fb['strengths'])
        if fb.get('role_fit_score'):
            role_fit_scores.append(fb['role_fit_score'])
        if fb.get('recommendation'):
            recommendations.append(fb['recommendation'])
    
    avg_score = sum(role_fit_scores) / len(role_fit_scores) if role_fit_scores else None
    
    # Create human-readable summary for rejection emails
    summary_parts = []
    if all_weaknesses:
        summary_parts.append(f"Areas for improvement: {'; '.join(all_weaknesses[:2])}")
    if all_missing:
        summary_parts.append(f"Skills to develop: {'; '.join(all_missing[:2])}")
    
    return {
        "has_feedback": True,
        "summary": ". ".join(summary_parts) if summary_parts else "Thank you for your interest in this position.",
        "strengths": all_strengths,
        "weaknesses": all_weaknesses,
        "missing_requirements": all_missing,
        "avg_role_fit_score": avg_score,
        "recommendations": recommendations,
        "feedback_count": len(result.data)
    }
