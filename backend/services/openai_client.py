"""
OpenAI client wrapper for embeddings and chat completions.
"""
from openai import OpenAI
from config import OPENAI_API_KEY
from typing import List, Optional
import json


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Model configurations
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
EMBEDDING_DIMENSION = 1536


async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for a text string.
    Returns a 1536-dimensional vector.
    """
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * EMBEDDING_DIMENSION
    
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single API call.
    More efficient for bulk indexing.
    """
    cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
    # Filter empty strings and track indices
    non_empty = [(i, t) for i, t in enumerate(cleaned_texts) if t]
    
    if not non_empty:
        return [[0.0] * EMBEDDING_DIMENSION] * len(texts)
    
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[t for _, t in non_empty]
    )
    
    # Map results back to original indices
    result = [[0.0] * EMBEDDING_DIMENSION] * len(texts)
    for idx, (orig_idx, _) in enumerate(non_empty):
        result[orig_idx] = response.data[idx].embedding
    
    return result


async def chat_completion(
    messages: List[dict],
    system_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Generate chat completion with OpenAI.
    
    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."}
        system_prompt: System instructions
        temperature: Creativity (0-1)
        max_tokens: Max response length
    
    Returns:
        AI response text
    """
    full_messages = [{"role": "system", "content": system_prompt}]
    full_messages.extend(messages)
    
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=full_messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content


async def chat_completion_with_context(
    user_message: str,
    context: str,
    conversation_history: Optional[List[dict]] = None,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate a response using retrieved RAG context.
    
    Args:
        user_message: Current user question
        context: Retrieved knowledge base content
        conversation_history: Previous messages
        system_prompt: Custom system instructions
    
    Returns:
        AI response grounded in the context
    """
    default_prompt = """You are a helpful HR assistant for Space42, a technology company.
Answer questions accurately using ONLY the provided context.
If the context doesn't contain enough information to answer, say so honestly.
Be friendly, professional, and concise.

CONTEXT:
{context}

INSTRUCTIONS:
- Use the context above to answer the user's question
- If you're not sure, say "I don't have that information"
- Be helpful and suggest related topics if relevant
- Keep responses concise but complete"""

    final_prompt = system_prompt or default_prompt.format(context=context)
    
    messages = conversation_history or []
    messages.append({"role": "user", "content": user_message})
    
    return await chat_completion(messages, final_prompt)
