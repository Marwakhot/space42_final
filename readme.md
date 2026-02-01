# Space42 HR Agent

An advanced HR agent for Space42, featuring WebGL visual effects and AI-powered recruitment workflows.

## Project Structure

- **frontend/**: Static website (HTML/CSS/JS) with Aurora/Orb effects.
- **backend/**: Python FastAPI server for logic, database, and AI.

## Deployment Guide

We use a "Dual Deployment" strategy for best performance on free tiers:
1. **Frontend -> Vercel** (Best for static sites)
2. **Backend -> Render** (Best for Python services)

### Step 1: Deploy Backend (Render)
1. Push this repo to GitHub.
2. Go to [Render](https://render.com) -> New Blueprint -> Connect Repo.
3. Render will use `render.yaml` to set up the Python service.
4. **Environment Variables**: Make sure to add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, etc. in the Render dashboard.
5. Once deployed, copy your **Backend URL** (e.g., `https://space42-backend.onrender.com`).

### Step 2: Configure Frontend
1. Open `frontend/api.js`.
2. Update the `API_BASE_URL` line:
   ```javascript
   const API_BASE_URL = 'https://YOUR-RENDER-BACKEND-URL.onrender.com';
   ```
3. Push the change to GitHub.

### Step 3: Deploy Frontend (Vercel)
1. Go to [Vercel](https://vercel.com) -> Add New Project -> Connect Repo.
2. Vercel will use `vercel.json` to deploy the `frontend` folder.
3. Visit your live site!