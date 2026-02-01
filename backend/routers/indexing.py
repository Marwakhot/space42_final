"""
Indexing Router - Admin endpoints for managing the knowledge base.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict

from dependencies import require_hr
from services.indexing_service import (
    index_faqs,
    index_job_roles,
    index_onboarding_templates,
    index_team_directory,
    rebuild_all_indexes
)

router = APIRouter(prefix="/indexing", tags=["Knowledge Base Indexing"])


# ============ Endpoints ============

@router.post("/rebuild", status_code=status.HTTP_200_OK)
async def rebuild_knowledge_base():
    """
    Rebuild the entire knowledge base.
    Re-indexes all FAQs, job roles, onboarding templates, and team directory.
    
    This should be run:
    - After initial setup
    - After bulk data changes
    - Periodically to refresh the index
    """
    try:
        results = await rebuild_all_indexes()
        return {
            "status": "success",
            "message": "Knowledge base rebuilt successfully",
            "indexed": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild knowledge base: {str(e)}"
        )


@router.post("/faqs")
async def index_faq_content(
    current_user: dict = Depends(require_hr)
):
    """
    Re-index FAQ content only.
    """
    try:
        count = await index_faqs()
        return {
            "status": "success",
            "message": f"Indexed {count} FAQs"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/jobs")
async def index_job_content(
    current_user: dict = Depends(require_hr)
):
    """
    Re-index job roles only.
    """
    try:
        count = await index_job_roles()
        return {
            "status": "success",
            "message": f"Indexed {count} job roles"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/onboarding")
async def index_onboarding_content(
    current_user: dict = Depends(require_hr)
):
    """
    Re-index onboarding templates only.
    """
    try:
        count = await index_onboarding_templates()
        return {
            "status": "success",
            "message": f"Indexed {count} onboarding templates"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/team")
async def index_team_content(
    current_user: dict = Depends(require_hr)
):
    """
    Re-index team directory only.
    """
    try:
        count = await index_team_directory()
        return {
            "status": "success",
            "message": f"Indexed {count} team members"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status")
async def get_index_status(
    current_user: dict = Depends(require_hr)
):
    """
    Get the current status of the knowledge base.
    """
    from database import get_supabase_client
    supabase = get_supabase_client()
    
    # Count embeddings by source type
    result = supabase.table('embeddings').select("source_type").execute()
    
    counts = {}
    if result.data:
        for item in result.data:
            source_type = item['source_type']
            counts[source_type] = counts.get(source_type, 0) + 1
    
    return {
        "status": "active",
        "indexed_counts": counts,
        "total": sum(counts.values())
    }
