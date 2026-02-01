# Running Space42 HR Agent Locally

## Prerequisites

1. **Python 3.8+** installed
2. **Supabase credentials** (URL, Service Key, Anon Key)
3. **GROQ API Key** (for AI chat features)
4. **Node.js** (optional, for serving frontend - or use Python's HTTP server)

## Step 1: Setup Backend

### 1.1 Install Dependencies

```powershell
# Navigate to backend folder
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Create .env File

Create a `.env` file in the `backend` folder with:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
SUPABASE_ANON_KEY=your_anon_key
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=your-secret-key-change-in-production
```

### 1.3 Start Backend Server

```powershell
# Make sure you're in the backend folder with venv activated
python main.py
```

Or using uvicorn directly:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will run on:** `http://localhost:8000`

You can test it by visiting: `http://localhost:8000` or `http://localhost:8000/health`

---

## Step 2: Setup Frontend

### Option A: Using Python HTTP Server (Simple)

```powershell
# Navigate to frontend folder
cd frontend

# Python 3
python -m http.server 3000

# Or Python 2
python -m SimpleHTTPServer 3000
```

### Option B: Using Node.js http-server

```powershell
# Install http-server globally (one time)
npm install -g http-server

# Navigate to frontend folder
cd frontend

# Start server
http-server -p 3000
```

### Option C: Using Live Server (VS Code Extension)

1. Install "Live Server" extension in VS Code
2. Right-click on `index.html` → "Open with Live Server"

**Frontend will run on:** `http://localhost:3000`

---

## Step 3: Verify Setup

1. **Backend Health Check:**
   - Open: `http://localhost:8000/health`
   - Should return: `{"status": "ok", "database": "connected"}`

2. **Frontend:**
   - Open: `http://localhost:3000`
   - Should see the login page

3. **API Connection:**
   - Check browser console (F12) for any connection errors
   - The frontend should connect to `http://localhost:8000`

---

## Quick Start Commands (All-in-One)

### Terminal 1 - Backend:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### Terminal 2 - Frontend:
```powershell
cd frontend
python -m http.server 3000
```

---

## Testing User Side

1. Open: `http://localhost:3000`
2. **Sign up** as a new candidate
3. Browse jobs at: `http://localhost:3000/jobs.html`
4. Check application status at: `http://localhost:3000/status.html`

---

## Testing HR Side

1. **Create HR User** (you'll need to do this in Supabase or via API)
   - Or sign up and manually change `user_type` to `'hr'` in database
   
2. Open: `http://localhost:3000/hr-portal.html`
3. **Login** with HR credentials
4. View applications, manage jobs, etc.

---

## Troubleshooting

### Backend Issues:

**Port 8000 already in use:**
```powershell
# Change port in main.py or use:
uvicorn main:app --reload --port 8001
```

**Missing dependencies:**
```powershell
pip install -r requirements.txt
```

**Environment variables not loading:**
- Make sure `.env` file is in `backend` folder
- Check file is named exactly `.env` (not `.env.txt`)

### Frontend Issues:

**CORS errors:**
- Backend CORS is already configured for `*` origins
- Make sure backend is running on port 8000

**API connection failed:**
- Check `frontend/api.js` - `API_BASE_URL` should be `http://localhost:8000`
- Make sure backend is running

**Port 3000 already in use:**
```powershell
# Use different port
python -m http.server 3001
```

---

## API Documentation

Once backend is running, visit:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
