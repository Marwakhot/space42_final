"""
CV Parser Service - Extracts structured data from resumes using Groq LLM.
"""
import json
from typing import Dict, Any, List
from services.ai_service import chat_completion


async def parse_resume(resume_text: str) -> Dict[str, Any]:
    """
    Parse resume using Groq LLM to extract structured information.
    
    Args:
        resume_text: Raw text content from the resume/CV
        
    Returns:
        Dictionary with parsed resume data
    """
    prompt = f"""
    Parse the following resume and extract all relevant information in a structured JSON format.
    Extract:
    1. Personal Information (name, email, phone, location)
    2. Skills (technical skills, soft skills, languages)
    3. Work Experience (company, role, duration, responsibilities, achievements)
    4. Education (degree, institution, year, GPA if available)
    5. Certifications
    6. Projects (if any)
    7. Years of experience
    
    Resume Text:
    {resume_text}
    
    Return a JSON object with the following structure:
    {{
        "personal_info": {{
            "name": "...",
            "email": "...",
            "phone": "...",
            "location": "..."
        }},
        "skills": {{
            "technical": ["skill1", "skill2", ...],
            "soft": ["skill1", "skill2", ...],
            "languages": ["language1", ...]
        }},
        "work_experience": [
            {{
                "company": "...",
                "role": "...",
                "duration": "...",
                "responsibilities": ["...", ...],
                "achievements": ["...", ...]
            }}
        ],
        "education": [
            {{
                "degree": "...",
                "institution": "...",
                "year": "...",
                "gpa": "..."
            }}
        ],
        "certifications": ["...", ...],
        "projects": [
            {{
                "name": "...",
                "description": "...",
                "technologies": ["...", ...]
            }}
        ],
        "years_of_experience": ...
    }}
    """
    
    try:
        system_prompt = "You are an expert at parsing resumes and extracting structured information. Always return valid JSON."
        messages = [{"role": "user", "content": prompt}]
        
        result = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Try to extract JSON from the response
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        
        parsed_data = json.loads(result)
        return parsed_data
    except Exception as e:
        print(f"Error parsing resume: {str(e)}")
        # Fallback: return basic structure
        return {
            "personal_info": {},
            "skills": {"technical": [], "soft": [], "languages": []},
            "work_experience": [],
            "education": [],
            "certifications": [],
            "projects": [],
            "years_of_experience": 0
        }


async def fill_application_form(candidate_data: Dict[str, Any], role_description: str) -> Dict[str, Any]:
    """
    Use AI to intelligently fill application form based on resume data.
    
    Args:
        candidate_data: Parsed candidate data from resume
        role_description: Description of the job role
        
    Returns:
        Dictionary with filled application form data
    """
    prompt = f"""
    Based on the following candidate data and role description, fill out an application form.
    
    Candidate Data:
    {json.dumps(candidate_data, indent=2)}
    
    Role Description:
    {role_description}
    
    Create a comprehensive application form response that highlights:
    1. Relevant skills for this role
    2. Relevant work experience
    3. Why the candidate is suitable
    4. Key achievements that match the role requirements
    
    Return a JSON object with:
    {{
        "summary": "Brief summary of candidate suitability",
        "relevant_skills": ["skill1", "skill2", ...],
        "relevant_experience": "...",
        "key_achievements": ["...", ...],
        "motivation": "Why candidate is interested/suitable"
    }}
    """
    
    try:
        system_prompt = "You are an expert at matching candidates to roles and filling application forms."
        messages = [{"role": "user", "content": prompt}]
        
        result = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.5
        )
        
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        
        return json.loads(result)
    except Exception as e:
        print(f"Error filling application form: {str(e)}")
        return {
            "summary": "Application form filled based on resume data",
            "relevant_skills": candidate_data.get("skills", {}).get("technical", []),
            "relevant_experience": "",
            "key_achievements": [],
            "motivation": ""
        }
