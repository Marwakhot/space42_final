"""
AI Chat Router - Endpoints for RAG-powered conversations.
Handles candidate queries and onboarding help.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from dependencies import get_current_user
from services.chat_service import process_candidate_query, process_onboarding_query

router = APIRouter(prefix="/ai", tags=["AI Chat"])


# ============ Request/Response Models ============

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[Dict[str, Any]] = []
    context_used: bool = False


# ============ Endpoints ============

@router.post("/chat", response_model=ChatResponse)
async def candidate_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat endpoint for candidate queries.
    Uses RAG to answer questions about jobs, application process, company info.
    
    Example questions:
    - "What positions are available in engineering?"
    - "What skills do I need for the Software Developer role?"
    - "How do I apply for a job?"
    - "What are the benefits at Space42?"
    """
    try:
        result = await process_candidate_query(
            message=request.message,
            conversation_id=request.conversation_id,
            candidate_id=current_user.get("user_id")
        )
        
        return ChatResponse(
            response=result['response'],
            conversation_id=result['conversation_id'],
            sources=result['sources'],
            context_used=result['context_used']
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post("/onboarding", response_model=ChatResponse)
async def onboarding_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat endpoint for new hire onboarding assistance.
    Uses RAG to answer questions about onboarding tasks, team, policies.
    
    Example questions:
    - "What do I need to complete on my first day?"
    - "Who is on my team?"
    - "How do I set up my development environment?"
    - "Where can I find the company policies?"
    """
    try:
        result = await process_onboarding_query(
            message=request.message,
            conversation_id=request.conversation_id,
            candidate_id=current_user.get("user_id")
        )
        
        return ChatResponse(
            response=result['response'],
            conversation_id=result['conversation_id'],
            sources=result['sources'],
            context_used=result['context_used']
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/chat/{conversation_id}/history")
async def get_chat_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get chat history for a conversation.
    """
    from database import get_supabase_client
    supabase = get_supabase_client()
    
    # Verify access
    conv_result = supabase.table('conversations').select("*").eq('id', conversation_id).execute()
    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv = conv_result.data[0]
    if current_user["user_type"] == "candidate" and str(conv['participant_id']) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get messages directly from conversation record
    return {
        "conversation_id": conversation_id,
        "context_type": conv.get('conversation_type'),
        "messages": conv.get('messages', []) or []
    }


# ============ Assessment Follow-up Questions ============

class AssessmentFollowUpRequest(BaseModel):
    question: str
    answer: str
    question_index: int
    job_title: str = "the position"


class AssessmentFollowUpResponse(BaseModel):
    follow_up_question: str


@router.post("/chat/assessment-followup", response_model=AssessmentFollowUpResponse)
async def get_assessment_followup(
    request: AssessmentFollowUpRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate an AI-powered follow-up question based on the candidate's answer.
    Uses Groq AI to create contextual, relevant follow-up questions.
    """
    from services.ai_service import chat_completion
    
    # Base behavioral questions to reference
    base_questions = [
        "Tell me about a time when you faced a significant challenge at work or in a project. How did you approach it and what was the outcome?",
        "Describe a situation where you had to work closely with someone whose working style was very different from yours. How did you handle it?",
        "Give me an example of when you had to learn a new skill or technology quickly. What was your approach?",
        "Tell me about a time when you made a mistake. How did you handle it and what did you learn?",
        "Describe a situation where you had to make a difficult decision without all the information you needed."
    ]
    
    # Get the next base question if we're not at the end
    next_question_index = request.question_index + 1
    if next_question_index >= len(base_questions):
        # No more questions, return the last one
        return AssessmentFollowUpResponse(follow_up_question=base_questions[-1])
    
    next_base_question = base_questions[next_question_index]
    
    try:
        # Create prompt for Groq AI
        system_prompt = f"""You are Orion, an AI interviewer for {request.job_title} at SPACE42, a leading space technology company.

Your task is to generate a thoughtful follow-up question based on the candidate's previous answer. The follow-up should:
1. Be relevant to the answer they just gave
2. Probe deeper into their experience or skills
3. Stay focused on behavioral assessment (teamwork, problem-solving, adaptability, communication, leadership)
4. Be professional yet conversational
5. Be 1-2 sentences long

If the candidate's answer doesn't provide much to follow up on, transition naturally to the next topic: "{next_base_question}"

Remember: You're assessing real-world behavior, not hypotheticals."""

        user_prompt = f"""Previous question: "{request.question}"

Candidate's answer: "{request.answer}"

Generate a follow-up question that either:
A) Digs deeper into something specific they mentioned
B) Asks about a related aspect of the situation
C) Transitions naturally to ask about: {next_base_question}

Just respond with the follow-up question, nothing else."""

        response = await chat_completion(
            system_prompt=system_prompt,
            user_message=user_prompt,
            temperature=0.7,
            max_tokens=150
        )
        
        follow_up = response.strip().strip('"').strip("'")
        
        # Validate the response is a reasonable question
        if len(follow_up) < 20 or len(follow_up) > 500:
            return AssessmentFollowUpResponse(follow_up_question=next_base_question)
        
        return AssessmentFollowUpResponse(follow_up_question=follow_up)
        
    except Exception as e:
        print(f"Error generating follow-up question: {e}")
        # Fallback to next base question
        return AssessmentFollowUpResponse(follow_up_question=next_base_question)