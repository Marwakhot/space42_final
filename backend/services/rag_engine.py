"""
RAG Engine - Retrieval Augmented Generation core logic.
Combines vector search with LLM generation for grounded responses.
"""
from services.ai_service import get_embedding, chat_completion_with_context
from services.vector_store import search_similar
from typing import List, Dict, Any, Optional


async def retrieve_context(
    query: str,
    source_types: Optional[List[str]] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context for a query.
    
    Args:
        query: User's question
        source_types: Filter by types (e.g., ['faq', 'onboarding'])
        top_k: Number of results
    
    Returns:
        List of relevant document chunks with metadata
    """
    # Generate query embedding
    query_embedding = await get_embedding(query)
    
    # Search vector store
    results = await search_similar(
        query_embedding=query_embedding,
        top_k=top_k,
        source_types=source_types,
        threshold=0.35  # Lower threshold for local embeddings
    )
    
    return results


def format_context(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a context string for the LLM.
    
    Args:
        documents: Retrieved documents from vector search
    
    Returns:
        Formatted context string
    """
    if not documents:
        return "No relevant information found in the knowledge base."
    
    context_parts = []
    for i, doc in enumerate(documents, 1):
        metadata = doc.get('metadata', {})
        source_type = doc.get('source_type', 'unknown')
        content = doc.get('content', '')
        
        # Add source info
        if source_type == 'faq':
            header = f"[FAQ - {metadata.get('category', 'General')}]"
        elif source_type == 'job_role':
            header = f"[Job: {metadata.get('title', 'Unknown')}]"
        elif source_type == 'onboarding':
            header = f"[Onboarding - {metadata.get('category', 'General')}]"
        elif source_type == 'team':
            header = f"[Team Member: {metadata.get('name', 'Unknown')}]"
        else:
            header = f"[{source_type}]"
        
        context_parts.append(f"{header}\n{content}")
    
    return "\n\n---\n\n".join(context_parts)


async def generate_response(
    query: str,
    source_types: Optional[List[str]] = None,
    conversation_history: Optional[List[dict]] = None,
    custom_system_prompt: Optional[str] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Generate a RAG response: retrieve context then generate answer.
    
    Args:
        query: User's question
        source_types: Filter sources
        conversation_history: Previous messages
        custom_system_prompt: Override default prompt
        top_k: Number of context chunks
    
    Returns:
        {response, sources, context_used}
    """
    # Step 1: Retrieve relevant context
    documents = await retrieve_context(query, source_types, top_k)
    
    # Step 2: Format context
    context = format_context(documents)
    
    # Step 3: Generate response
    response = await chat_completion_with_context(
        user_message=query,
        context=context,
        conversation_history=conversation_history,
        system_prompt=custom_system_prompt
    )
    
    # Step 4: Extract sources for transparency
    sources = []
    for doc in documents:
        sources.append({
            "type": doc.get('source_type'),
            "id": doc.get('source_id'),
            "title": doc.get('metadata', {}).get('title', doc.get('metadata', {}).get('question', 'Unknown')),
            "similarity": doc.get('similarity', 0)
        })
    
    return {
        "response": response,
        "sources": sources,
        "context_used": len(documents) > 0
    }


async def generate_faq_response(
    query: str,
    conversation_history: Optional[List[dict]] = None
) -> Dict[str, Any]:
    """
    Generate response for candidate FAQ queries.
    Searches FAQs, job roles, and general company info.
    """
    system_prompt = """You are a helpful HR assistant for Space42.
Your role is to help candidates with questions about:
- Job positions and requirements
- Application process
- Company culture and benefits
- Interview preparation

Answer using ONLY the provided context. If you don't have the information, 
suggest they contact hr@space42.com for more details.

Be friendly, professional, and encouraging to candidates.

CONTEXT:
{context}"""

    return await generate_response(
        query=query,
        source_types=['faq', 'job_role'],
        conversation_history=conversation_history,
        custom_system_prompt=system_prompt
    )


async def generate_onboarding_response(
    query: str,
    conversation_history: Optional[List[dict]] = None
) -> Dict[str, Any]:
    """
    Generate response for new hire onboarding questions.
    Searches onboarding templates, team directory, and FAQs.
    """
    system_prompt = """You are the Space42 onboarding assistant, helping new hires navigate their first days.
You can help with:
- Onboarding tasks and documentation
- Team introductions
- Company policies and processes
- Tools and systems access

Answer using ONLY the provided context. For tasks not in your knowledge, 
direct them to their manager or HR contact.

Be warm, welcoming, and supportive of new team members!

CONTEXT:
{context}"""

    return await generate_response(
        query=query,
        source_types=['onboarding', 'team', 'faq'],
        conversation_history=conversation_history,
        custom_system_prompt=system_prompt
    )
