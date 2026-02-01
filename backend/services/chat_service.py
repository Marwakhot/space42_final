"""
Chat Service - Main chat logic for candidate queries and onboarding help.
"""
from services.rag_engine import generate_faq_response, generate_onboarding_response
from database import get_supabase_client
from typing import List, Dict, Any, Optional
from datetime import datetime

# Helper to fetch and parse conversation history from JSONB
async def get_conversation_history(conversation_id: str) -> List[Dict[str, Any]]:
    supabase = get_supabase_client()
    result = supabase.table('conversations').select("messages").eq('id', conversation_id).execute()
    if result.data and result.data[0]['messages']:
        return result.data[0]['messages']
    return []

# Helper to append messages to conversation
async def append_messages(conversation_id: str, new_messages: List[Dict[str, Any]]):
    supabase = get_supabase_client()
    # 1. Get current messages
    result = supabase.table('conversations').select("messages").eq('id', conversation_id).execute()
    current_messages = []
    if result.data and result.data[0]['messages']:
        current_messages = result.data[0]['messages']
    
    # 2. Append new ones
    updated_messages = current_messages + new_messages
    
    # 3. Update table
    supabase.table('conversations').update({
        "messages": updated_messages
    }).eq('id', conversation_id).execute()


async def process_candidate_query(
    message: str,
    conversation_id: Optional[str] = None,
    candidate_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a candidate's query using RAG.
    """
    supabase = get_supabase_client()
    conversation_history = []
    
    # Get conversation history if exists
    if conversation_id:
        raw_history = await get_conversation_history(conversation_id)
        # Convert to format needed by RAG engine (if needed, or just pass as is)
        # RAG engine expects: [{"role": "user", "content": "..."}]
        # Our JSONB storage will match this format.
        conversation_history = raw_history[-10:] # Last 10 messages for context
    else:
        # Create new conversation
        conv_data = {
            "participant_id": candidate_id,
            "conversation_type": "candidate_query", # Schema calls it 'conversation_type', context_type was wrong
            "status": "active",
            "messages": [],
            "started_at": datetime.utcnow().isoformat()
        }
        conv_result = supabase.table('conversations').insert(conv_data).execute()
        if conv_result.data:
            conversation_id = str(conv_result.data[0]['id'])
    
    # Generate RAG response
    result = await generate_faq_response(message, conversation_history)
    
    # Prepare new messages
    timestamp = datetime.utcnow().isoformat()
    new_messages = [
        {
            "role": "user",
            "content": message,
            "created_at": timestamp
        },
        {
            "role": "assistant",
            "content": result['response'],
            "created_at": timestamp,
            "metadata": {"sources": result['sources']}
        }
    ]
    
    # Store messages
    if conversation_id:
        await append_messages(conversation_id, new_messages)
    
    return {
        "response": result['response'],
        "sources": result['sources'],
        "conversation_id": conversation_id,
        "context_used": result['context_used']
    }


async def process_onboarding_query(
    message: str,
    conversation_id: Optional[str] = None,
    candidate_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a new hire's onboarding question using RAG.
    """
    supabase = get_supabase_client()
    conversation_history = []
    
    # Get conversation history if exists
    if conversation_id:
        raw_history = await get_conversation_history(conversation_id)
        conversation_history = raw_history[-10:]
    else:
        # Create new conversation
        conv_data = {
            "participant_id": candidate_id,
            "conversation_type": "onboarding_help",
            "status": "active",
            "messages": [],
            "started_at": datetime.utcnow().isoformat()
        }
        conv_result = supabase.table('conversations').insert(conv_data).execute()
        if conv_result.data:
            conversation_id = str(conv_result.data[0]['id'])
    
    # Generate RAG response for onboarding
    result = await generate_onboarding_response(message, conversation_history)
    
    # Prepare new messages
    timestamp = datetime.utcnow().isoformat()
    new_messages = [
        {
            "role": "user",
            "content": message,
            "created_at": timestamp
        },
        {
            "role": "assistant",
            "content": result['response'],
            "created_at": timestamp,
            "metadata": {"sources": result['sources']}
        }
    ]
    
    # Store messages
    if conversation_id:
        await append_messages(conversation_id, new_messages)
    
    return {
        "response": result['response'],
        "sources": result['sources'],
        "conversation_id": conversation_id,
        "context_used": result['context_used']
    }
