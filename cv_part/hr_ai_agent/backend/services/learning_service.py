from sqlalchemy.orm import Session
from database import HRFeedback, Application, AIImprovement
from typing import Dict, Any
import json


def record_learning_data(
    db: Session,
    application_id: int,
    hr_feedback_id: int,
    ai_score: float,
    hr_score: float,
    feedback_text: str,
    followup_questions: list
):
    """
    Record learning data from HR feedback for reinforcement learning
    """
    learning_data = {
        "ai_score": ai_score,
        "hr_score": hr_score,
        "score_difference": hr_score - ai_score,
        "feedback": feedback_text,
        "followup_questions": followup_questions,
        "timestamp": str(db.query(Application).filter(Application.id == application_id).first().created_at)
    }
    
    improvement = AIImprovement(
        application_id=application_id,
        hr_feedback_id=hr_feedback_id,
        learning_data=learning_data
    )
    
    db.add(improvement)
    db.commit()
    return improvement


def get_learning_insights(db: Session) -> Dict[str, Any]:
    """
    Analyze learning data to provide insights for improving AI
    """
    improvements = db.query(AIImprovement).all()
    
    if not improvements:
        return {"message": "No learning data available yet"}
    
    score_differences = []
    common_feedback_themes = []
    
    for imp in improvements:
        data = imp.learning_data
        score_differences.append(data.get("score_difference", 0))
        if data.get("feedback"):
            common_feedback_themes.append(data["feedback"])
    
    avg_score_difference = sum(score_differences) / len(score_differences) if score_differences else 0
    
    return {
        "total_feedback_records": len(improvements),
        "average_score_difference": avg_score_difference,
        "ai_tends_to": "overestimate" if avg_score_difference < 0 else "underestimate" if avg_score_difference > 0 else "match",
        "common_feedback_themes": common_feedback_themes[:5]  # Top 5
    }
