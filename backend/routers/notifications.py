"""
Notifications router for managing user notifications.
Handles notification retrieval and read status.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from database import get_supabase_client
from dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============ Constants ============

NOTIFICATION_TYPES = [
    "application_status",
    "interview_scheduled",
    "interview_reminder",
    "document_required",
    "offer_received",
    "onboarding_task",
    "general"
]

PRIORITIES = ["low", "normal", "high", "urgent"]


# ============ Response Models ============

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    user_type: str
    notification_type: str
    title: str
    message: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    priority: str = "normal"
    is_read: bool = False
    read_at: Optional[str] = None
    created_at: Optional[str] = None


class UnreadCountResponse(BaseModel):
    unread_count: int


# ============ Endpoints ============

@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False, description="Show only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Max notifications to return"),
    current_user: dict = Depends(get_current_user)
):
    """
    List notifications for the current user.
    """
    supabase = get_supabase_client()
    user_id = current_user["user_id"]
    user_type = current_user["user_type"]
    
    query = supabase.table('notifications').select("*").eq('user_id', user_id).eq('user_type', user_type)
    
    if unread_only:
        query = query.eq('is_read', False)
    
    result = query.order('created_at', desc=True).limit(limit).execute()
    
    return [NotificationResponse(
        id=str(n['id']),
        user_id=str(n['user_id']),
        user_type=n['user_type'],
        notification_type=n['notification_type'],
        title=n['title'],
        message=n['message'],
        reference_type=n.get('reference_type'),
        reference_id=str(n['reference_id']) if n.get('reference_id') else None,
        priority=n.get('priority', 'normal'),
        is_read=n.get('is_read', False),
        read_at=n.get('read_at'),
        created_at=n.get('created_at')
    ) for n in result.data]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: dict = Depends(get_current_user)
):
    """
    Get count of unread notifications for the current user.
    """
    supabase = get_supabase_client()
    user_id = current_user["user_id"]
    user_type = current_user["user_type"]
    
    result = supabase.table('notifications').select("id", count="exact").eq('user_id', user_id).eq('user_type', user_type).eq('is_read', False).execute()
    
    return UnreadCountResponse(unread_count=result.count or 0)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a notification as read.
    """
    supabase = get_supabase_client()
    user_id = current_user["user_id"]
    user_type = current_user["user_type"]
    
    # Check if notification exists and belongs to user
    existing = supabase.table('notifications').select("*").eq('id', notification_id).eq('user_id', user_id).eq('user_type', user_type).execute()
    
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Mark as read
    result = supabase.table('notifications').update({
        "is_read": True,
        "read_at": datetime.now(timezone.utc).isoformat()
    }).eq('id', notification_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification"
        )
    
    n = result.data[0]
    
    return NotificationResponse(
        id=str(n['id']),
        user_id=str(n['user_id']),
        user_type=n['user_type'],
        notification_type=n['notification_type'],
        title=n['title'],
        message=n['message'],
        reference_type=n.get('reference_type'),
        reference_id=str(n['reference_id']) if n.get('reference_id') else None,
        priority=n.get('priority', 'normal'),
        is_read=n.get('is_read', False),
        read_at=n.get('read_at'),
        created_at=n.get('created_at')
    )


@router.put("/read-all")
async def mark_all_as_read(
    current_user: dict = Depends(get_current_user)
):
    """
    Mark all notifications as read for the current user.
    """
    supabase = get_supabase_client()
    user_id = current_user["user_id"]
    user_type = current_user["user_type"]
    
    supabase.table('notifications').update({
        "is_read": True,
        "read_at": datetime.now(timezone.utc).isoformat()
    }).eq('user_id', user_id).eq('user_type', user_type).eq('is_read', False).execute()
    
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a notification.
    """
    supabase = get_supabase_client()
    user_id = current_user["user_id"]
    user_type = current_user["user_type"]
    
    # Check if notification exists and belongs to user
    existing = supabase.table('notifications').select("id").eq('id', notification_id).eq('user_id', user_id).eq('user_type', user_type).execute()
    
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    supabase.table('notifications').delete().eq('id', notification_id).execute()
    
    return {"message": "Notification deleted", "notification_id": notification_id}


class NotificationCreate(BaseModel):
    user_id: str
    user_type: str
    notification_type: str
    title: str
    message: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    priority: str = "normal"


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    request: NotificationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new notification manually.
    Only Admins or HR can create notifications directly.
    """
    if current_user["user_type"] not in ["admin", "hr"]:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or HR can send notifications"
        )
        
    supabase = get_supabase_client()
    
    # Validate notification type
    if request.notification_type not in NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification type. Must be one of: {', '.join(NOTIFICATION_TYPES)}"
        )

    new_notification = {
        "user_id": request.user_id,
        "user_type": request.user_type,
        "notification_type": request.notification_type,
        "title": request.title,
        "message": request.message,
        "reference_type": request.reference_type,
        "reference_id": request.reference_id,
        "priority": request.priority,
        "is_read": False
    }
    
    result = supabase.table('notifications').insert(new_notification).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification"
        )
        
    n = result.data[0]
    
    return NotificationResponse(
        id=str(n['id']),
        user_id=str(n['user_id']),
        user_type=n['user_type'],
        notification_type=n['notification_type'],
        title=n['title'],
        message=n['message'],
        reference_type=n.get('reference_type'),
        reference_id=str(n['reference_id']) if n.get('reference_id') else None,
        priority=n.get('priority', 'normal'),
        is_read=n.get('is_read', False),
        read_at=n.get('read_at'),
        created_at=n.get('created_at')
    )
