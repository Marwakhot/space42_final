# SPACE42 HR Agent 🚀

An AI-powered HR management system for SPACE42's recruitment and onboarding processes.

---

## ✨ Key Features

### For Candidates
- **Smart Job Matching** — AI analyzes your CV and shows skill compatibility for each role
- **One-Click Apply** — Upload CV, apply to jobs, track application status
- **AI Behavioral Assessment** — Conversational interview with voice & text support
- **Real-time Status Updates** — Track your application through every stage

### For HR
- **Applicant Rankings** — Candidates ranked by combined technical + behavioral scores
- **Interview Notes** — Add feedback during interviews (used in rejection emails)
- **Bulk Actions** — Shortlist top N candidates or reject others with one click
- **Interview Scheduling** — Schedule and manage interviews with email notifications
- **Talent Orbit** — View rejected candidates for future opportunities

### AI-Powered
- **CV Parsing** — Automatic skill extraction using Groq LLM
- **Semantic Matching** — FAISS vector search for job-candidate matching
- **Dynamic Interviews** — AI generates follow-up questions based on responses
- **Personalized Emails** — AI-generated feedback in rejection/offer emails
- **Voice Mode** — Speech recognition & text-to-speech in assessments

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| Database | Supabase (PostgreSQL) |
| AI/LLM | Groq API |
| Embeddings | FastEmbed + FAISS |
| Auth | JWT Tokens |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js (for `npx serve`)
- Supabase account

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/space42-hr-agent.git
cd space42-hr-agent
```

### 2. Configure Environment

Create `backend/.env`:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=your_secret_key
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Start Backend

```bash
uvicorn main:app --reload --port 8000
```

### 5. Start Frontend (new terminal)

```bash
cd frontend
npx serve -p 3000
```

### 6. Load Test Data (Optional)

1. Open Supabase Dashboard → SQL Editor
2. Paste contents of `test_data.sql`
3. Click Run

---

## 🔗 URLs

| Page | URL |
|------|-----|
| Candidate Portal | http://localhost:3000/index.html |
| Jobs | http://localhost:3000/jobs.html |
| HR Portal | http://localhost:3000/hr-portal.html |
| API Docs | http://localhost:8000/docs |

---

## 👤 Test Accounts

| Role | Email | Password |
|------|-------|----------|
| HR Manager | hr.admin@space42.ae | TestHR123! |
| Candidate | sarah.chen@email.com | Test123! |

---

## 📄 License

MIT License - Built for SPACE42
