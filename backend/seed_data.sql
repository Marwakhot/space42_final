-- =====================================================
-- SPACE42 HR AGENT - SEED DATA
-- Run this in Supabase SQL Editor to populate sample data
-- =====================================================

-- 1. HR ADMIN USER
-- Password: admin123
INSERT INTO hr_users (email, password_hash, first_name, last_name, department, role)
VALUES (
    'hr@space42.com',
    '$2b$12$MRSfMtFU5M/QRPDL0pcNneuFee9sdnhnpQ6h.2K9THvhh89YrEJG6',
    'HR',
    'Admin',
    'Human Resources',
    'HR Manager'
) ON CONFLICT (email) DO NOTHING;

-- 2. SAMPLE CONTENT (FAQs)
INSERT INTO faq_content (category, question, answer, keywords, is_active)
VALUES 
(
    'General', 
    'What is the remote work policy?', 
    'Space42 offers a hybrid work model. Employees can work remotely up to 3 days a week, with 2 days required in the office for collaboration.', 
    '["remote", "wfh", "hybrid", "office"]',
    true
),
(
    'Benefits', 
    'What health insurance do you offer?', 
    'We provide comprehensive health insurance covering medical, dental, and vision for all full-time employees and their dependents.', 
    '["health", "insurance", "dental", "vision"]',
    true
),
(
    'Application', 
    'How long does the hiring process take?', 
    'The typical hiring process takes 2-3 weeks from application to offer. This includes an initial screening, a technical assessment, and a final behavioral interview.', 
    '["hiring", "timeline", "process"]',
    true
);

-- 3. SAMPLE JOBS
INSERT INTO job_roles (
    title, department, description, location, work_type, 
    salary_min, salary_max, currency, experience_min, experience_max,
    non_negotiable_skills, preferred_skills, is_active
)
VALUES (
    'Senior AI Engineer',
    'Engineering',
    'We are looking for an experienced AI Engineer to lead our RAG implementation. You will work with LLMs, vector databases, and Python backend systems.',
    'Dubai, UAE',
    'Hybrid',
    25000, 40000, 'AED',
    5, 8,
    '["Python", "NLP", "PyTorch", "FastAPI"]',
    '["LangChain", "Supabase", "React"]',
    true
);

-- 4. ONBOARDING TEMPLATES
INSERT INTO onboarding_templates (template_name, department, role_type, items, is_active)
VALUES (
    'Engineering Onboarding',
    'Engineering',
    'Technical',
    '[
        {"title": "Setup Laptop", "description": "Request access to GitHub and setup dev environment", "category": "tools", "due_days": 1},
        {"title": "Meet the Team", "description": "Schedule 1:1s with your squad", "category": "social", "due_days": 3},
        {"title": "Read Tech Docs", "description": "Review the API documentation in Confluence", "category": "learning", "due_days": 5}
    ]',
    true
);

-- 5. TEAM DIRECTORY
INSERT INTO team_directory (user_type, department, position, team_name, bio, expertise_areas, is_active)
VALUES (
    'employee',
    'Engineering',
    'CTO',
    'Leadership',
    'Leading the tech vision at Space42. Passionate about AI agents and automation.',
    '["AI Strategy", "System Architecture", "Leadership"]',
    true
);
