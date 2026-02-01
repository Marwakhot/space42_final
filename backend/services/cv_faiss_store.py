"""
CV FAISS Store - FAISS vector store for semantic CV-to-role matching using FastEmbed.
"""
import os
import asyncio
import json
from typing import List, Dict, Optional, Any
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.ai_service import get_embedding, get_embeddings_batch
from database import get_supabase_client

# FAISS requires synchronous embeddings, so we'll create a wrapper
class FastEmbedEmbeddings:
    """Wrapper to make FastEmbed work with LangChain FAISS."""
    
    def __init__(self):
        self.embedding_dim = 384
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Synchronous embedding for documents (runs async in a separate thread)."""
        import concurrent.futures
        
        def run_in_new_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(get_embeddings_batch(texts))
            finally:
                loop.close()
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop)
            return future.result()
    
    def embed_query(self, text: str) -> List[float]:
        """Synchronous embedding for query (runs async in a separate thread)."""
        import concurrent.futures
        
        def run_in_new_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(get_embedding(text))
            finally:
                loop.close()
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop)
            return future.result()


# Global FAISS store instance
_VECTORSTORE: Optional[FAISS] = None
_EMBEDDINGS = FastEmbedEmbeddings()

# Path for storing FAISS index
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "cv_vector_store")


def get_text_splitter(chunk_size: int = 1000, chunk_overlap: int = 100):
    """Get text splitter for chunking documents."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def initialize_cv_vector_store(rebuild: bool = False) -> FAISS:
    """
    Initialize or load FAISS vector store for CV-to-role matching.
    
    Args:
        rebuild: If True, rebuild the vector store from scratch
        
    Returns:
        FAISS vector store instance
    """
    global _VECTORSTORE
    
    if _VECTORSTORE and not rebuild:
        return _VECTORSTORE
    
    # Try to load existing store
    if os.path.exists(VECTOR_STORE_PATH) and not rebuild:
        try:
            _VECTORSTORE = FAISS.load_local(
                VECTOR_STORE_PATH,
                _EMBEDDINGS,
                allow_dangerous_deserialization=True,
            )
            return _VECTORSTORE
        except Exception as e:
            print(f"Error loading FAISS store: {e}, rebuilding...")
    
    # Build new store from job roles in database
    supabase = get_supabase_client()
    result = supabase.table('job_roles').select("*").eq('is_active', True).execute()
    
    documents = []
    if result.data:
        for job in result.data:
            # Build role content
            non_negotiable = job.get('non_negotiable_skills', [])
            preferred = job.get('preferred_skills', [])
            
            if isinstance(non_negotiable, str):
                non_negotiable = json.loads(non_negotiable) if non_negotiable else []
            if isinstance(preferred, str):
                preferred = json.loads(preferred) if preferred else []
            
            content = (
                f"Role: {job['title']}\n"
                f"Department: {job.get('department', 'Not specified')}\n"
                f"Description: {job.get('description', '')}\n"
                f"Required Skills: {', '.join(non_negotiable)}\n"
                f"Preferred Skills: {', '.join(preferred)}\n"
            )
            
            doc = Document(
                page_content=content,
                metadata={
                    "type": "role",
                    "role_id": str(job['id']),
                    "role_title": job['title'],
                    "source": "db",
                },
            )
            documents.append(doc)
    
    # Split documents into chunks
    if documents:
        splitter = get_text_splitter()
        chunks = splitter.split_documents(documents)
    else:
        # Create empty store with init document
        chunks = [Document(page_content="Init", metadata={"type": "init"})]
    
    # Build FAISS store
    _VECTORSTORE = FAISS.from_documents(chunks, _EMBEDDINGS)
    
    # Save to disk
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    _VECTORSTORE.save_local(VECTOR_STORE_PATH)
    
    return _VECTORSTORE


def get_cv_vector_store() -> FAISS:
    """Get or initialize the CV vector store."""
    return initialize_cv_vector_store(rebuild=False)


def add_resume_to_vector_store(
    resume_text: str,
    candidate_id: str,
    source: str = "uploaded_resume"
) -> None:
    """
    Add a resume to the FAISS vector store for semantic matching.
    
    Args:
        resume_text: Text content of the resume
        candidate_id: ID of the candidate
        source: Source identifier
    """
    vectorstore = get_cv_vector_store()
    
    doc = Document(
        page_content=resume_text,
        metadata={
            "type": "resume",
            "candidate_id": candidate_id,
            "source": source,
        },
    )
    
    # Split into chunks
    splitter = get_text_splitter()
    chunks = splitter.split_documents([doc])
    
    # Add to vector store
    vectorstore.add_documents(chunks)
    
    # Save updated store
    vectorstore.save_local(VECTOR_STORE_PATH)


def add_role_to_vector_store(job_data: Dict[str, Any]) -> None:
    """
    Add or update a job role in the FAISS vector store.
    
    Args:
        job_data: Job role data from database
    """
    vectorstore = get_cv_vector_store()
    
    non_negotiable = job_data.get('non_negotiable_skills', [])
    preferred = job_data.get('preferred_skills', [])
    
    if isinstance(non_negotiable, str):
        non_negotiable = json.loads(non_negotiable) if non_negotiable else []
    if isinstance(preferred, str):
        preferred = json.loads(preferred) if preferred else []
    
    content = (
        f"Role: {job_data['title']}\n"
        f"Department: {job_data.get('department', 'Not specified')}\n"
        f"Description: {job_data.get('description', '')}\n"
        f"Required Skills: {', '.join(non_negotiable)}\n"
        f"Preferred Skills: {', '.join(preferred)}\n"
    )
    
    doc = Document(
        page_content=content,
        metadata={
            "type": "role",
            "role_id": str(job_data['id']),
            "role_title": job_data['title'],
            "source": "db",
        },
    )
    
    # Split and add
    splitter = get_text_splitter()
    chunks = splitter.split_documents([doc])
    vectorstore.add_documents(chunks)
    
    # Save updated store
    vectorstore.save_local(VECTOR_STORE_PATH)


def match_candidate_to_roles(
    candidate_resume_text: str,
    k: int = 5
) -> List[Dict[str, Any]]:
    """
    Find matching roles for a candidate using semantic similarity.
    
    Args:
        candidate_resume_text: Resume text of the candidate
        k: Number of top matches to return
        
    Returns:
        List of matched roles with scores
    """
    vectorstore = get_cv_vector_store()
    
    try:
        # Search for similar roles
        results_with_score = vectorstore.similarity_search_with_score(
            candidate_resume_text,
            k=k,
            filter={"type": "role"},
        )
        
        matches = []
        for doc, distance in results_with_score:
            # Convert distance to similarity score (0-100)
            # FAISS uses L2 distance, lower is better
            similarity = 1 / (1 + float(distance))
            score = round(similarity * 100, 2)
            
            matches.append({
                "role_id": doc.metadata.get("role_id"),
                "role_title": doc.metadata.get("role_title"),
                "match_score": score,
                "reason": "Semantic match based on resume embeddings.",
            })
        
        return matches
    except Exception as e:
        print(f"Error in semantic matching: {e}")
        return []


def rebuild_cv_vector_store() -> int:
    """
    Rebuild the CV vector store from all active job roles.
    
    Returns:
        Number of roles indexed
    """
    global _VECTORSTORE
    _VECTORSTORE = None
    
    vectorstore = initialize_cv_vector_store(rebuild=True)
    
    # Count roles in store (approximate)
    supabase = get_supabase_client()
    result = supabase.table('job_roles').select("id").eq('is_active', True).execute()
    
    return len(result.data) if result.data else 0
