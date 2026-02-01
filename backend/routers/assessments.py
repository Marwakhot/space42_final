"""
Assessments router for storing behavioral scores from AI interviews.
Data access layer for assessment results.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_supabase_client
from dependencies import get_current_user, require_hr

router = APIRouter(prefix="/assessments", tags=["Assessments"])


# ============ Request/Response Models ============

class AssessmentCreate(BaseModel):
    application_id: str
    overall_score: float
    parameter_scores: Dict[str, float]
    feedback_summary: str
    detailed_feedback: Optional[Dict[str, Any]] = None

class AssessmentResponse(BaseModel):
    id: str
    application_id: str
    overall_score: float
    parameter_scores: Dict[str, float]
    feedback_summary: str
    detailed_feedback: Optional[Dict[str, Any]] = None
    created_at: str


# ============ Endpoints ============

@router.get("/application/{application_id}", response_model=List[AssessmentResponse])
async def get_application_assessments(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get assessment scores for a specific application.
    """
    supabase = get_supabase_client()
    
    # Access check: Candidate can only see if it's their app? 
    # Usually assessments are internal to HR, but maybe some feedback is shared.
    # For now, let's assume HR only or owner candidate.
    
    query = supabase.table('behavioral_assessment_scores').select("*").eq('application_id', application_id)
    result = query.order('created_at', desc=True).execute()
    
    return [AssessmentResponse(
        id=str(a['id']),
        application_id=str(a['application_id']),
        overall_score=a['overall_score'],
        parameter_scores=a['parameter_scores'],
        feedback_summary=a['feedback_summary'],
        detailed_feedback=a.get('detailed_feedback'),
        created_at=a['created_at']
    ) for a in result.data]


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: str,
    current_user: dict = Depends(require_hr) # HR only for deep dive
):
    """
    Get specific assessment details.
    """
    supabase = get_supabase_client()
    
    result = supabase.table('behavioral_assessment_scores').select("*").eq('id', assessment_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    a = result.data[0]
    
    return AssessmentResponse(
        id=str(a['id']),
        application_id=str(a['application_id']),
        overall_score=a['overall_score'],
        parameter_scores=a['parameter_scores'],
        feedback_summary=a['feedback_summary'],
        detailed_feedback=a.get('detailed_feedback'),
        created_at=a['created_at']
    )


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    request: AssessmentCreate,
    current_user: dict = Depends(require_hr) # Internal system or HR manual override
):
    """
    Create/Save an assessment result.
    Typically called by the AI service, but exposed here for testing/manual entry.
    """
    supabase = get_supabase_client()
    
    new_assessment = {
        "application_id": request.application_id,
        "overall_score": request.overall_score,
        "parameter_scores": request.parameter_scores,
        "feedback_summary": request.feedback_summary,
        "detailed_feedback": request.detailed_feedback
    }
    
    result = supabase.table('behavioral_assessment_scores').insert(new_assessment).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save assessment")
        
    a = result.data[0]
    
    return AssessmentResponse(
        id=str(a['id']),
        application_id=str(a['application_id']),
        overall_score=a['overall_score'],
        parameter_scores=a['parameter_scores'],
        feedback_summary=a['feedback_summary'],
        detailed_feedback=a.get('detailed_feedback'),
        created_at=a['created_at']
    )
