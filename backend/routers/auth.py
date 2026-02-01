"""
Authentication router for user signup, login, and profile management.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone

from database import get_supabase_client
from auth_utils import hash_password, verify_password, create_access_token
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============ Request/Response Models ============

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    location: Optional[str] = None
    years_of_experience: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    user_type: str
    email: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    user_type: str
    created_at: Optional[str] = None
    # Additional fields for HR users
    department: Optional[str] = None
    role: Optional[str] = None
    # Additional fields for candidates
    location: Optional[str] = None
    years_of_experience: Optional[int] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


# ============ Endpoints ============

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest):
    """Register a new candidate account."""
    supabase = get_supabase_client()
    
    # Check if email already exists
    existing = supabase.table('candidates').select("id").eq('email', request.email).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Also check hr_users and admin_users
    hr_existing = supabase.table('hr_users').select("id").eq('email', request.email).execute()
    admin_existing = supabase.table('admin_users').select("id").eq('email', request.email).execute()
    if hr_existing.data or admin_existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new candidate
    password_hash = hash_password(request.password)
    
    new_candidate = {
        "email": request.email,
        "password_hash": password_hash,
        "first_name": request.first_name,
        "last_name": request.last_name,
        "location": request.location,
        "years_of_experience": request.years_of_experience,
        "is_active": True
    }
    
    result = supabase.table('candidates').insert(new_candidate).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )
    
    user = result.data[0]
    token = create_access_token(str(user['id']), "candidate", user['email'])
    
    return AuthResponse(
        access_token=token,
        user_id=str(user['id']),
        user_type="candidate",
        email=user['email']
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login for candidates, HR, or admin users."""
    supabase = get_supabase_client()
    
    # Try to find user in each table
    user = None
    user_type = None
    
    # Check candidates
    result = supabase.table('candidates').select("*").eq('email', request.email).execute()
    if result.data:
        user = result.data[0]
        user_type = "candidate"
    
    # Check hr_users
    if not user:
        result = supabase.table('hr_users').select("*").eq('email', request.email).execute()
        if result.data:
            user = result.data[0]
            user_type = "hr"
    
    # Check admin_users
    if not user:
        result = supabase.table('admin_users').select("*").eq('email', request.email).execute()
        if result.data:
            user = result.data[0]
            user_type = "admin"
    
    # User not found
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if candidate is active
    if user_type == "candidate" and not user.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Update last_login for candidates
    if user_type == "candidate":
        supabase.table('candidates').update({
            "last_login": datetime.now(timezone.utc).isoformat()
        }).eq('id', user['id']).execute()
    
    token = create_access_token(str(user['id']), user_type, user['email'])
    
    return AuthResponse(
        access_token=token,
        user_id=str(user['id']),
        user_type=user_type,
        email=user['email']
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    supabase = get_supabase_client()
    
    user_type = current_user["user_type"]
    user_id = current_user["user_id"]
    
    # Get user from appropriate table
    if user_type == "candidate":
        result = supabase.table('candidates').select("*").eq('id', user_id).execute()
    elif user_type == "hr":
        result = supabase.table('hr_users').select("*").eq('id', user_id).execute()
    elif user_type == "admin":
        result = supabase.table('admin_users').select("*").eq('id', user_id).execute()
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = result.data[0]
    
    response_data = {
        "id": str(user['id']),
        "email": user['email'],
        "first_name": user['first_name'],
        "last_name": user['last_name'],
        "user_type": user_type,
        "created_at": user.get('created_at')
    }
    
    # Add HR-specific fields
    if user_type == "hr":
        response_data["department"] = user.get('department')
        response_data["role"] = user.get('role')
    
    # Add candidate-specific fields
    if user_type == "candidate":
        response_data["location"] = user.get('location')
        response_data["years_of_experience"] = user.get('years_of_experience')
    
    return UserProfileResponse(**response_data)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout current user.
    Note: JWT tokens are stateless, so logout is handled client-side
    by discarding the token. This endpoint confirms the action.
    """
    return {"message": "Successfully logged out", "user_id": current_user["user_id"]}


@router.post("/reset-password")
async def request_password_reset(request: PasswordResetRequest):
    """
    Request a password reset email.
    Note: Email functionality to be implemented separately.
    """
    supabase = get_supabase_client()
    
    # Check if email exists in any table
    candidates = supabase.table('candidates').select("id").eq('email', request.email).execute()
    hr_users = supabase.table('hr_users').select("id").eq('email', request.email).execute()
    admin_users = supabase.table('admin_users').select("id").eq('email', request.email).execute()
    
    if not (candidates.data or hr_users.data or admin_users.data):
        # Don't reveal if email exists or not for security
        pass
    
    # TODO: Send password reset email
    
    return {"message": "If an account exists with this email, a reset link will be sent"}
