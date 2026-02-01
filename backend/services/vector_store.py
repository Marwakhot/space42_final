"""
Vector store service using Supabase pgvector for similarity search.
"""
from database import get_supabase_client
from typing import List, Optional, Dict, Any
from uuid import uuid4
import json


async def store_embedding(
    content: str,
    embedding: List[float],
    source_type: str,
    source_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Store a document chunk with its embedding.
    
    Args:
        content: The text content
        embedding: Vector embedding (1536 dimensions)
        source_type: Type of source ('faq', 'job_role', 'onboarding', 'team')
        source_id: ID of the source record
        metadata: Additional metadata (title, category, etc.)
    
    Returns:
        ID of the created embedding record
    """
    supabase = get_supabase_client()
    
    record = {
        "content": content,
        "embedding": embedding,
        "source_type": source_type,
        "source_id": source_id,
        "metadata": metadata or {}
    }
    
    result = supabase.table('embeddings').insert(record).execute()
    
    if result.data:
        return str(result.data[0]['id'])
    return None


async def store_embeddings_batch(
    items: List[Dict[str, Any]]
) -> int:
    """
    Store multiple embeddings in batch.
    
    Args:
        items: List of {content, embedding, source_type, source_id, metadata}
    
    Returns:
        Number of records inserted
    """
    supabase = get_supabase_client()
    
    records = [{
        "content": item["content"],
        "embedding": item["embedding"],
        "source_type": item["source_type"],
        "source_id": item.get("source_id"),
        "metadata": item.get("metadata", {})
    } for item in items]
    
    result = supabase.table('embeddings').insert(records).execute()
    
    return len(result.data) if result.data else 0


async def search_similar(
    query_embedding: List[float],
    top_k: int = 5,
    source_types: Optional[List[str]] = None,
    threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Find similar documents using cosine similarity.
    
    Args:
        query_embedding: Query vector
        top_k: Number of results to return
        source_types: Filter by source types (e.g., ['faq', 'job_role'])
        threshold: Minimum similarity score (0-1)
    
    Returns:
        List of matching documents with similarity scores
    """
    supabase = get_supabase_client()
    
    # Build the RPC call for vector similarity search
    # Using Supabase's match_embeddings function (we'll need to create this)
    params = {
        "query_embedding": query_embedding,
        "match_threshold": threshold,
        "match_count": top_k
    }
    
    if source_types:
        params["filter_source_types"] = source_types
    
    # Call the RPC function
    result = supabase.rpc('match_embeddings', params).execute()
    
    if result.data:
        return result.data
    return []


async def delete_by_source(source_type: str, source_id: Optional[str] = None) -> int:
    """
    Delete embeddings by source.
    
    Args:
        source_type: Type of source to delete
        source_id: Specific source ID (if None, deletes all of that type)
    
    Returns:
        Number of records deleted
    """
    supabase = get_supabase_client()
    
    query = supabase.table('embeddings').delete().eq('source_type', source_type)
    
    if source_id:
        query = query.eq('source_id', source_id)
    
    result = query.execute()
    
    return len(result.data) if result.data else 0


async def clear_all_embeddings() -> int:
    """
    Clear all embeddings from the vector store.
    Use with caution - primarily for testing/reindexing.
    """
    supabase = get_supabase_client()
    
    # Delete all records
    result = supabase.table('embeddings').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    
    return len(result.data) if result.data else 0
