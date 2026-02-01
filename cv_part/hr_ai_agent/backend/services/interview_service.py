from typing import List, Dict, Any
from openai import OpenAI
from config import settings
import json

client = OpenAI(api_key=settings.openai_api_key)


def generate_interview_questions(
    interview_type: str,
    candidate_data: Dict[str, Any],
    role_description: str,
    role_skills: List[str]
) -> List[Dict[str, Any]]:
    """
    Generate interview questions based on type (technical or behavioral)
    """
    if interview_type == "technical":
        prompt = f"""
        Generate 5 technical interview questions for a candidate applying for this role.
        
        Role Description: {role_description}
        Required Skills: {role_skills}
        Candidate Background: {json.dumps(candidate_data, indent=2)}
        
        Create questions that:
        1. Test technical knowledge relevant to the role
        2. Include scenario-based questions
        3. Mix of short answer and multiple choice questions
        4. Are appropriate for the candidate's experience level
        
        Return a JSON array of questions, each with:
        {{
            "question": "...",
            "type": "short_answer" or "multiple_choice",
            "options": ["option1", "option2", ...] (only for multiple_choice),
            "correct_answer": "..." (for scoring)
        }}
        """
    else:  # behavioral
        prompt = f"""
        Generate 5 behavioral interview questions for a candidate applying for this role.
        
        Role Description: {role_description}
        Candidate Background: {json.dumps(candidate_data, indent=2)}
        
        Create questions that:
        1. Test soft skills, teamwork, problem-solving
        2. Include scenario-based questions
        3. Mix of short answer and multiple choice questions
        4. Assess cultural fit and work style
        
        Return a JSON array of questions, each with:
        {{
            "question": "...",
            "type": "short_answer" or "multiple_choice",
            "options": ["option1", "option2", ...] (only for multiple_choice),
            "evaluation_criteria": "What to look for in the answer"
        }}
        """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert at creating interview questions. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        
        questions = json.loads(result)
        # Add question IDs
        for i, q in enumerate(questions):
            q["id"] = i + 1
        return questions
    except Exception as e:
        # Fallback questions
        if interview_type == "technical":
            return [
                {
                    "id": 1,
                    "question": "Describe your experience with the technologies required for this role.",
                    "type": "short_answer",
                    "evaluation_criteria": "Relevance and depth of experience"
                },
                {
                    "id": 2,
                    "question": "How would you approach solving a complex technical problem?",
                    "type": "short_answer",
                    "evaluation_criteria": "Problem-solving methodology"
                }
            ]
        else:
            return [
                {
                    "id": 1,
                    "question": "Tell us about a time you worked in a team to solve a difficult problem.",
                    "type": "short_answer",
                    "evaluation_criteria": "Teamwork and communication"
                },
                {
                    "id": 2,
                    "question": "How do you handle tight deadlines and pressure?",
                    "type": "short_answer",
                    "evaluation_criteria": "Stress management"
                }
            ]


def evaluate_interview_answers(
    interview_type: str,
    questions: List[Dict[str, Any]],
    answers: List[Dict[str, Any]],
    candidate_data: Dict[str, Any]
) -> float:
    """
    Evaluate interview answers and return a score (0-100)
    """
    prompt = f"""
    Evaluate interview answers for a {interview_type} interview.
    
    Questions and Answers:
    {json.dumps([{"question": q["question"], "answer": next((a["answer"] for a in answers if a.get("question_id") == q.get("id")), "No answer")} for q in questions], indent=2)}
    
    Candidate Background:
    {json.dumps(candidate_data, indent=2)}
    
    For each answer, evaluate:
    1. Relevance and accuracy
    2. Depth of understanding
    3. Communication clarity
    4. Alignment with role requirements
    
    Return a JSON object with:
    {{
        "overall_score": 0-100,
        "question_scores": [score1, score2, ...],
        "feedback": "Overall feedback on the interview"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert interviewer evaluating candidate responses. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result = response.choices[0].message.content
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        
        evaluation = json.loads(result)
        return evaluation.get("overall_score", 50)
    except Exception as e:
        # Fallback: simple scoring
        return 70.0
