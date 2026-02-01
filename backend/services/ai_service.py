"""
AI Service - Wrapper for Groq (LLM) and FastEmbed (Embeddings).
Replaces OpenAI client to use free/local alternatives.
"""
import os
import asyncio
from typing import List, Optional, Dict, Any
from groq import AsyncGroq
from fastembed import TextEmbedding
from dotenv import load_dotenv

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384 dimensions

# Initialize Clients
groq_client = None
embedding_model = None

def get_groq_client():
    global groq_client
    if not groq_client:
        if not GROQ_API_KEY:
            # Fallback/Error if key missing, though strictly we should just fail or warn
            print("Warning: GROQ_API_KEY not set")
            return None
        groq_client = AsyncGroq(api_key=GROQ_API_KEY)
    return groq_client

def get_embedding_model():
    global embedding_model
    if not embedding_model:
        # FastEmbed loads model locally (downloads on first run)
        embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    return embedding_model


async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding using local FastEmbed model.
    Returns 384-dimensional vector.
    """
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * 384  # Return zero vector matching dimension
    
    model = get_embedding_model()
    # FastEmbed returns generator of numpy arrays, we want list of floats
    # list(model.embed([text]))[0] is a numpy array
    embedding_gen = model.embed([text])
    embedding_list = list(embedding_gen)
    return embedding_list[0].tolist()


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.
    """
    cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
    if not cleaned_texts:
        return []
        
    model = get_embedding_model()
    # model.embed(texts) is a generator
    embeddings = list(model.embed(cleaned_texts))
    return [e.tolist() for e in embeddings]


async def chat_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """
    Generate chat completion using Groq (Llama 3).
    """
    client = get_groq_client()
    if not client:
        return "Error: Groq API Key is missing. Please add GROQ_API_KEY to .env"

    final_messages = []
    if system_prompt:
        final_messages.append({"role": "system", "content": system_prompt})
    
    # Filter messages to only include supported fields (role, content)
    # Groq API rejects extra fields like 'created_at' or 'metadata'
    for msg in messages:
        clean_msg = {
            "role": msg.get("role"),
            "content": msg.get("content")
        }
        final_messages.append(clean_msg)
    
    try:
        completion = await client.chat.completions.create(
            messages=final_messages,
            model="llama-3.1-8b-instant",
            temperature=temperature,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq API Error: {str(e)}")
        return f"I encountered an error generating the response: {str(e)}"


# Helper for RAG
async def chat_completion_with_context(
    user_message: str,
    context: str,
    conversation_history: Optional[List[dict]] = None,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate a response using context from the knowledge base.
    """
    default_system_prompt = """You are a helpful HR assistant for Space42. 
    Use the following context to answer the user's question.
    
    Context:
    {context}
    
    If the answer is not in the context, say you don't know or ask for more details.
    Keep answers professional, friendly, and concise.
    """
    
    final_system_prompt = system_prompt or default_system_prompt
    # Inject context into system prompt
    final_system_prompt = final_system_prompt.format(context=context) if "{context}" in final_system_prompt else f"{final_system_prompt}\n\nContext:\n{context}"
    
    messages = conversation_history or []
    messages.append({"role": "user", "content": user_message})
    
    return await chat_completion(messages, system_prompt=final_system_prompt)
