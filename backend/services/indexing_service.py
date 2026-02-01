"""
Indexing Service - Index content from database into vector store.
Handles FAQs, job roles, onboarding templates, and team directory.
"""
from database import get_supabase_client
from services.ai_service import get_embeddings_batch
from services.vector_store import store_embeddings_batch, delete_by_source, clear_all_embeddings
from typing import List, Dict, Any
import json


async def index_faqs() -> int:
    """
    Index all active FAQs into the vector store.
    
    Returns:
        Number of FAQs indexed
    """
    supabase = get_supabase_client()
    
    # Fetch active FAQs
    result = supabase.table('faq_content').select("*").eq('is_active', True).execute()
    
    if not result.data:
        return 0
    
    # Clear existing FAQ embeddings
    await delete_by_source('faq')
    
    # Prepare content for embedding
    items = []
    texts = []
    for faq in result.data:
        # Combine question and answer for better semantic search
        content = f"Question: {faq['question']}\n\nAnswer: {faq['answer']}"
        texts.append(content)
        items.append({
            "content": content,
            "source_type": "faq",
            "source_id": str(faq['id']),
            "metadata": {
                "question": faq['question'],
                "category": faq.get('category', 'General'),
                "keywords": faq.get('keywords', [])
            }
        })
    
    # Generate embeddings in batch
    embeddings = await get_embeddings_batch(texts)
    
    # Add embeddings to items
    for i, emb in enumerate(embeddings):
        items[i]["embedding"] = emb
    
    # Store in vector database
    count = await store_embeddings_batch(items)
    
    return count


async def index_job_roles() -> int:
    """
    Index all active job roles into the vector store.
    
    Returns:
        Number of job roles indexed
    """
    supabase = get_supabase_client()
    
    # Fetch active jobs
    result = supabase.table('job_roles').select("*").eq('is_active', True).execute()
    
    if not result.data:
        return 0
    
    # Clear existing job embeddings
    await delete_by_source('job_role')
    
    items = []
    texts = []
    for job in result.data:
        # Create rich content for embedding
        skills_text = ""
        if job.get('non_negotiable_skills'):
            skills = job['non_negotiable_skills'] if isinstance(job['non_negotiable_skills'], list) else json.loads(job['non_negotiable_skills'])
            skills_text = f"Required skills: {', '.join(skills)}. "
        if job.get('preferred_skills'):
            pref_skills = job['preferred_skills'] if isinstance(job['preferred_skills'], list) else json.loads(job['preferred_skills'])
            skills_text += f"Preferred skills: {', '.join(pref_skills)}."
        
        content = f"""Job Title: {job['title']}
Department: {job.get('department', 'Not specified')}
Location: {job.get('location', 'Not specified')}
Work Type: {job.get('work_type', 'Not specified')}

Description:
{job.get('description', 'No description available')}

Requirements:
{skills_text}

Experience: {job.get('experience_min', 0)}-{job.get('experience_max', 0)} years"""

        texts.append(content)
        items.append({
            "content": content,
            "source_type": "job_role",
            "source_id": str(job['id']),
            "metadata": {
                "title": job['title'],
                "department": job.get('department'),
                "location": job.get('location'),
                "work_type": job.get('work_type')
            }
        })
    
    embeddings = await get_embeddings_batch(texts)
    
    for i, emb in enumerate(embeddings):
        items[i]["embedding"] = emb
    
    count = await store_embeddings_batch(items)
    
    return count


async def index_onboarding_templates() -> int:
    """
    Index onboarding templates into the vector store.
    
    Returns:
        Number of templates indexed
    """
    supabase = get_supabase_client()
    
    result = supabase.table('onboarding_templates').select("*").eq('is_active', True).execute()
    
    if not result.data:
        return 0
    
    await delete_by_source('onboarding')
    
    items = []
    texts = []
    for template in result.data:
        # Process template items
        template_items = template.get('items', [])
        if isinstance(template_items, str):
            template_items = json.loads(template_items)
        
        tasks_text = ""
        for item in template_items:
            tasks_text += f"- {item.get('title', 'Task')}: {item.get('description', '')}\n"
        
        content = f"""Onboarding Template: {template['template_name']}
Department: {template.get('department', 'All')}
Role Type: {template.get('role_type', 'General')}

Tasks:
{tasks_text}"""

        texts.append(content)
        items.append({
            "content": content,
            "source_type": "onboarding",
            "source_id": str(template['id']),
            "metadata": {
                "template_name": template['template_name'],
                "department": template.get('department'),
                "role_type": template.get('role_type'),
                "category": "onboarding_template"
            }
        })
    
    embeddings = await get_embeddings_batch(texts)
    
    for i, emb in enumerate(embeddings):
        items[i]["embedding"] = emb
    
    count = await store_embeddings_batch(items)
    
    return count


async def index_team_directory() -> int:
    """
    Index team directory for new hire introductions.
    
    Returns:
        Number of team members indexed
    """
    supabase = get_supabase_client()
    
    result = supabase.table('team_directory').select("*").eq('is_active', True).execute()
    
    if not result.data:
        return 0
    
    await delete_by_source('team')
    
    items = []
    texts = []
    for member in result.data:
        expertise = member.get('expertise_areas', [])
        if isinstance(expertise, str):
            expertise = json.loads(expertise)
        
        content = f"""Team Member: {member.get('position', 'Team Member')}
Department: {member.get('department', 'Not specified')}
Team: {member.get('team_name', 'Not specified')}

Bio:
{member.get('bio', 'No bio available')}

Expertise: {', '.join(expertise) if expertise else 'Not specified'}"""

        texts.append(content)
        items.append({
            "content": content,
            "source_type": "team",
            "source_id": str(member['id']),
            "metadata": {
                "name": f"{member.get('position', 'Unknown')}",
                "department": member.get('department'),
                "team": member.get('team_name'),
                "position": member.get('position')
            }
        })
    
    embeddings = await get_embeddings_batch(texts)
    
    for i, emb in enumerate(embeddings):
        items[i]["embedding"] = emb
    
    count = await store_embeddings_batch(items)
    
    return count


async def rebuild_all_indexes() -> Dict[str, int]:
    """
    Rebuild all indexes from scratch.
    
    Returns:
        Dict with counts for each source type
    """
    results = {
        "faqs": await index_faqs(),
        "job_roles": await index_job_roles(),
        "onboarding": await index_onboarding_templates(),
        "team": await index_team_directory()
    }
    
    results["total"] = sum(results.values())
    
    return results
