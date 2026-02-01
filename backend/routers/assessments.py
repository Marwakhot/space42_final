"""
Assessments router for storing behavioral scores from AI interviews.
Data access layer for assessment results.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from database import get_supabase_client
from dependencies import get_current_user, require_hr, require_candidate
from services.ai_service import chat_completion

router = APIRouter(prefix="/assessments", tags=["Assessments"])


# ============ Request/Response Models ============

class BehavioralAnswer(BaseModel):
    question: str
    answer: str

class BehavioralAssessmentRequest(BaseModel):
    application_id: str
    answers: List[BehavioralAnswer]

class BehavioralAssessmentResponse(BaseModel):
    success: bool
    message: str
    behavioral_score: Optional[float] = None

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


@router.post("/behavioral", response_model=BehavioralAssessmentResponse)
async def submit_behavioral_assessment(
    request: BehavioralAssessmentRequest,
    current_user: dict = Depends(require_candidate)
):
    """
    Submit behavioral assessment answers for AI scoring.
    Called by candidates after completing the assessment.
    """
    supabase = get_supabase_client()
    candidate_id = current_user["user_id"]
    
    # Verify application belongs to candidate
    app_result = supabase.table('applications').select("*").eq('id', request.application_id).eq('candidate_id', candidate_id).execute()
    
    if not app_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied"
        )
    
    application = app_result.data[0]
    
    # Get CV data separately if cv_id exists
    cv_data = None
    if application.get('cv_id'):
        cv_result = supabase.table('cvs').select("parsed_data").eq('id', application['cv_id']).execute()
        if cv_result.data:
            cv_data = cv_result.data[0]
    
    # Check if already completed
    if application.get('behavioral_score') is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Behavioral assessment already completed for this application"
        )
    
    # Format answers for AI scoring
    answers_text = "\n\n".join([
        f"Question: {a.question}\nAnswer: {a.answer}"
        for a in request.answers
    ])
    
    # AI scoring prompt
    scoring_prompt = f"""You are an expert HR assessor evaluating behavioral interview responses.

Evaluate the following behavioral interview responses and provide scores for each category.

RESPONSES:
{answers_text}

Score each category from 0-100:
1. Problem Solving - How well they analyze problems and find solutions
2. Communication - Clarity, structure, and articulation of responses
3. Teamwork - Ability to collaborate and work with others
4. Adaptability - How they handle change and learn new things
5. Leadership - Initiative, decision-making, and influence

Respond ONLY with valid JSON in this exact format:
{{
    "problem_solving": <score>,
    "communication": <score>,
    "teamwork": <score>,
    "adaptability": <score>,
    "leadership": <score>,
    "overall_score": <weighted_average>,
    "feedback_summary": "<2-3 sentence summary of candidate's behavioral strengths and areas for improvement>"
}}"""

    try:
        # Call AI for scoring
        ai_response = await chat_completion(
            messages=[{"role": "user", "content": scoring_prompt}],
            temperature=0.3
        )
        
        # Parse AI response
        response_text = ai_response.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        scores = json.loads(response_text.strip())
        
        behavioral_score = scores.get('overall_score', 50)
        parameter_scores = {
            "problem_solving": scores.get('problem_solving', 50),
            "communication": scores.get('communication', 50),
            "teamwork": scores.get('teamwork', 50),
            "adaptability": scores.get('adaptability', 50),
            "leadership": scores.get('leadership', 50)
        }
        feedback_summary = scores.get('feedback_summary', 'Assessment completed.')
        
    except Exception as e:
        # Default scores if AI fails
        print(f"AI scoring failed: {e}")
        behavioral_score = 60
        parameter_scores = {
            "problem_solving": 60,
            "communication": 60,
            "teamwork": 60,
            "adaptability": 60,
            "leadership": 60
        }
        feedback_summary = "Assessment responses recorded. Detailed analysis pending."
    
    # Get technical score from CV parsing (if available)
    technical_score = None
    if cv_data and cv_data.get('parsed_data'):
        parsed = cv_data['parsed_data']
        # Calculate technical score based on skills, experience, education
        skills = parsed.get('skills', {})
        if isinstance(skills, dict):
            tech_skills = skills.get('technical', [])
        else:
            tech_skills = skills if isinstance(skills, list) else []
        
        experience = parsed.get('experience', [])
        education = parsed.get('education', [])
        certifications = parsed.get('certifications', [])
        
        # Simple scoring algorithm
        skill_score = min(len(tech_skills) * 5, 40)  # Up to 40 points for skills
        exp_score = min(len(experience) * 10, 30)  # Up to 30 points for experience
        edu_score = min(len(education) * 10, 20)  # Up to 20 points for education
        cert_score = min(len(certifications) * 5, 10)  # Up to 10 points for certs
        
        technical_score = skill_score + exp_score + edu_score + cert_score
    
    # If no CV data, use eligibility check score
    if technical_score is None:
        eligibility = application.get('eligibility_details', {})
        matched = len(eligibility.get('matched_skills', []))
        total = matched + len(eligibility.get('missing_skills', []))
        if total > 0:
            technical_score = int((matched / total) * 100)
        else:
            technical_score = 50  # Default
    
    # Calculate combined score (40% behavioral, 60% technical)
    combined_score = (behavioral_score * 0.4) + (technical_score * 0.6)
    
    # Save assessment to behavioral_assessment_scores table
    assessment_data = {
        "application_id": request.application_id,
        "overall_score": behavioral_score,
        "parameter_scores": parameter_scores,
        "feedback_summary": feedback_summary,
        "detailed_feedback": {
            "answers": [{"question": a.question, "answer": a.answer} for a in request.answers],
            "ai_evaluation": parameter_scores
        }
    }
    
    # Try to save to behavioral_assessment_scores table (may not exist)
    try:
        supabase.table('behavioral_assessment_scores').insert(assessment_data).execute()
        print(f"Saved assessment to behavioral_assessment_scores for application {request.application_id}")
    except Exception as e:
        print(f"Note: behavioral_assessment_scores table insert skipped: {e}")
    
    # Update application with scores - this is the critical part
    update_data = {
        "behavioral_score": behavioral_score,
        "technical_score": technical_score,
        "combined_score": combined_score
    }
    
    print(f"Updating application {request.application_id} with scores: {update_data}")
    
    try:
        update_result = supabase.table('applications').update(update_data).eq('id', request.application_id).execute()
        print(f"Application update result: {update_result.data}")
    except Exception as e:
        print(f"ERROR updating application scores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save scores: {str(e)}"
        )
    
    return BehavioralAssessmentResponse(
        success=True,
        message="Behavioral assessment completed successfully",
        behavioral_score=behavioral_score
    )
