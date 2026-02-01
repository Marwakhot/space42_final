"""
CV Matching Service - Combines semantic (FAISS) and rule-based matching for CV-to-role matching.
"""
from typing import List, Dict, Any, Tuple, Optional
from services.cv_faiss_store import match_candidate_to_roles
from services.ai_service import chat_completion
from database import get_supabase_client
import json


def calculate_match_score(
    candidate_skills: List[str],
    non_negotiable_skills: List[str],
    good_to_have_skills: List[str],
    candidate_experience: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Calculate match score based on skills and experience (rule-based).
    
    Args:
        candidate_skills: List of candidate's technical skills
        non_negotiable_skills: Required skills for the role
        good_to_have_skills: Preferred skills for the role
        candidate_experience: Candidate's experience data
        
    Returns:
        Tuple of (score, reason)
    """
    # Normalize to lowercase for comparison
    candidate_skills_lower = [s.lower() for s in candidate_skills]
    non_negotiable_lower = [s.lower() for s in non_negotiable_skills]
    good_to_have_lower = [s.lower() for s in good_to_have_skills]
    
    # Count matching non-negotiable skills (must have all)
    matching_non_negotiable = sum(
        1 for skill in non_negotiable_lower 
        if any(cs in skill or skill in cs for cs in candidate_skills_lower)
    )
    non_negotiable_score = (
        (matching_non_negotiable / len(non_negotiable_skills)) * 50 
        if non_negotiable_skills else 0
    )
    
    # Count matching good-to-have skills
    matching_good_to_have = sum(
        1 for skill in good_to_have_lower 
        if any(cs in skill or skill in cs for cs in candidate_skills_lower)
    )
    good_to_have_score = (
        (matching_good_to_have / len(good_to_have_skills)) * 30 
        if good_to_have_skills else 0
    )
    
    # Experience bonus (20 points max)
    years_exp = candidate_experience.get("years_of_experience", 0)
    experience_score = min(years_exp / 10 * 20, 20)
    
    total_score = non_negotiable_score + good_to_have_score + experience_score
    
    # Collect matched and missing skills for display
    matched_non_negotiable = []
    missing_non_negotiable = []
    matched_preferred = []
    
    # Check non-negotiable skills
    for skill in non_negotiable_skills:
        skill_lower = skill.lower()
        if any(cs in skill_lower or skill_lower in cs for cs in candidate_skills_lower):
            matched_non_negotiable.append(skill)
        else:
            missing_non_negotiable.append(skill)
            
    # Check preferred skills
    for skill in good_to_have_skills:
        skill_lower = skill.lower()
        if any(cs in skill_lower or skill_lower in cs for cs in candidate_skills_lower):
            matched_preferred.append(skill)
    
    # Generate reason
    reason = (
        f"Matched {matching_non_negotiable}/{len(non_negotiable_skills)} required skills, "
        f"{matching_good_to_have}/{len(good_to_have_skills)} preferred skills, "
        f"{years_exp} years of experience"
    )
            
    return total_score, reason, matched_non_negotiable, matched_preferred, missing_non_negotiable


async def find_matching_roles(
    candidate_id: str,
    resume_text: Optional[str] = None,
    parsed_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Find all roles that match a candidate's profile using both semantic and rule-based matching.
    
    Args:
        candidate_id: ID of the candidate
        resume_text: Raw resume text (for semantic matching)
        parsed_data: Parsed resume data (for rule-based matching)
        
    Returns:
        List of matched roles with scores and reasons
    """
    supabase = get_supabase_client()
    matched_roles = []
    
    # Get all active job roles
    result = supabase.table('job_roles').select("*").eq('is_active', True).execute()
    
    if not result.data:
        return []
    
    active_roles = result.data
    
    # Try semantic matching first (if resume text available)
    semantic_matches = []
    if resume_text:
        try:
            semantic_matches = match_candidate_to_roles(resume_text, k=min(5, len(active_roles)))
            # Convert to dict for easy lookup
            semantic_match_map = {
                match["role_id"]: match for match in semantic_matches
            }
        except Exception as e:
            print(f"Error in semantic matching: {e}")
            semantic_match_map = {}
    else:
        semantic_match_map = {}
    
    # Rule-based matching (if parsed data available)
    if parsed_data:
        candidate_skills = parsed_data.get("skills", {}).get("technical", [])
        candidate_experience = {
            "years_of_experience": parsed_data.get("years_of_experience", 0),
            "work_experience": parsed_data.get("work_experience", []),
        }
        
        for role in active_roles:
            role_id = str(role['id'])
            
            # Get skills from role
            non_negotiable = role.get('non_negotiable_skills', [])
            good_to_have = role.get('preferred_skills', [])
            
            # Parse JSON if needed
            if isinstance(non_negotiable, str):
                non_negotiable = json.loads(non_negotiable) if non_negotiable else []
            if isinstance(good_to_have, str):
                good_to_have = json.loads(good_to_have) if good_to_have else []
            
            # Calculate rule-based score
            score, reason, matched_non_negotiable, matched_preferred, missing_non_negotiable = calculate_match_score(
                candidate_skills,
                non_negotiable,
                good_to_have,
                candidate_experience
            )
            
            # Check if candidate has all required skills
            has_all_required = len(missing_non_negotiable) == 0
            
            # Combine semantic and rule-based scores
            semantic_match = semantic_match_map.get(role_id)
            if semantic_match:
                # Weighted combination: 40% semantic, 60% rule-based
                combined_score = (semantic_match["match_score"] * 0.4) + (score * 0.6)
                reason = f"Semantic: {semantic_match['match_score']:.1f}%, Rule-based: {score:.1f}% - {reason}"
            else:
                combined_score = score
            
            # Include ALL roles (not just matches) so user can see what's missing
            matched_roles.append({
                "role_id": role_id,
                "role_title": role['title'],
                "department": role.get('department'),
                "location": role.get('location'),
                "work_type": role.get('work_type'),
                "salary_max": role.get('salary_max'),
                "currency": role.get('currency'),
                "match_score": round(combined_score, 2),
                "reason": reason,
                "semantic_score": semantic_match["match_score"] if semantic_match else None,
                "rule_based_score": score,
                "matched_non_negotiable_skills": matched_non_negotiable,
                "matched_preferred_skills": matched_preferred,
                "missing_non_negotiable_skills": missing_non_negotiable,
                "has_all_required_skills": has_all_required,
                "is_eligible": has_all_required and combined_score >= 50
            })
    else:
        # Only semantic matching if no parsed data - still return all roles
        semantic_role_map = {match["role_id"]: match for match in semantic_matches}
        
        for role in active_roles:
            role_id = str(role['id'])
            semantic_match = semantic_role_map.get(role_id)
            
            if semantic_match:
                matched_roles.append({
                    "role_id": role_id,
                    "role_title": role['title'],
                    "department": role.get('department'),
                    "location": role.get('location'),
                    "work_type": role.get('work_type'),
                    "salary_max": role.get('salary_max'),
                    "currency": role.get('currency'),
                    "match_score": round(semantic_match["match_score"], 2),
                    "reason": semantic_match.get("reason", "Semantic match"),
                    "semantic_score": semantic_match["match_score"],
                    "rule_based_score": None,
                    "matched_non_negotiable_skills": [],
                    "matched_preferred_skills": [],
                    "missing_non_negotiable_skills": role.get('non_negotiable_skills', []),
                    "has_all_required_skills": False,
                    "is_eligible": semantic_match["match_score"] >= 50
                })
            else:
                # No match data - still include the role
                non_negotiable = role.get('non_negotiable_skills', [])
                if isinstance(non_negotiable, str):
                    non_negotiable = json.loads(non_negotiable) if non_negotiable else []
                
                matched_roles.append({
                    "role_id": role_id,
                    "role_title": role['title'],
                    "department": role.get('department'),
                    "location": role.get('location'),
                    "work_type": role.get('work_type'),
                    "salary_max": role.get('salary_max'),
                    "currency": role.get('currency'),
                    "match_score": 0,
                    "reason": "No CV data for matching",
                    "semantic_score": None,
                    "rule_based_score": None,
                    "matched_non_negotiable_skills": [],
                    "matched_preferred_skills": [],
                    "missing_non_negotiable_skills": non_negotiable,
                    "has_all_required_skills": False,
                    "is_eligible": False
                })
    
    # Sort by score descending
    matched_roles.sort(key=lambda x: x["match_score"], reverse=True)
    
    return matched_roles


async def generate_ai_summary(
    candidate_data: Dict[str, Any],
    role_data: Dict[str, Any],
    match_score: float
) -> str:
    """
    Generate AI summary for candidate-role match using Groq.
    
    Args:
        candidate_data: Parsed candidate data
        role_data: Job role data
        match_score: Calculated match score
        
    Returns:
        AI-generated summary text
    """
    prompt = f"""
    Generate a comprehensive summary for HR about a candidate's suitability for a role.
    
    Candidate Data:
    {json.dumps(candidate_data, indent=2)}
    
    Role:
    Title: {role_data.get('title', 'Unknown')}
    Department: {role_data.get('department', 'Unknown')}
    Description: {role_data.get('description', 'No description')}
    Required Skills: {role_data.get('non_negotiable_skills', [])}
    Preferred Skills: {role_data.get('preferred_skills', [])}
    
    Match Score: {match_score}/100
    
    Provide a summary (200-300 words) covering:
    1. Candidate's key strengths relevant to the role
    2. Relevant experience and achievements
    3. Skills match analysis
    4. Potential concerns or gaps
    5. Overall recommendation
    """
    
    try:
        system_prompt = "You are an expert HR analyst providing candidate assessments."
        messages = [{"role": "user", "content": prompt}]
        
        summary = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.5
        )
        
        return summary
    except Exception as e:
        print(f"Error generating AI summary: {e}")
        return f"Candidate shows {match_score}% match with required skills and experience."
