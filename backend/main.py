from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import get_supabase_client
from routers.auth import router as auth_router
from routers.jobs import router as jobs_router
from routers.applications import router as applications_router
from routers.cvs import router as cvs_router
from routers.interviews import router as interviews_router
from routers.feedback import router as feedback_router
from routers.notifications import router as notifications_router
from routers.candidates import router as candidates_router
from routers.onboarding import router as onboarding_router
from routers.team import router as team_router
from routers.onboarding_templates import router as onboarding_templates_router
from routers.faq import router as faq_router
from routers.conversations import router as conversations_router
from routers.assessments import router as assessments_router
from routers.ai_chat import router as ai_chat_router
from routers.indexing import router as indexing_router

app = FastAPI(title="Space42 HR Agent API")

# Register routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(cvs_router)
app.include_router(interviews_router)
app.include_router(feedback_router)
app.include_router(notifications_router)
app.include_router(candidates_router)
app.include_router(onboarding_router)
app.include_router(team_router)
app.include_router(onboarding_templates_router)
app.include_router(faq_router)
app.include_router(conversations_router)
app.include_router(assessments_router)
app.include_router(ai_chat_router)
app.include_router(indexing_router)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],  # Add production URLs here
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Space42 HR Agent API", "status": "running"}

@app.get("/health")
def health_check():
    """Check if API and database are working"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('job_roles').select("count", count="exact").execute()
        return {
            "status": "healthy",
            "database": "connected",
            "job_roles_count": response.count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)