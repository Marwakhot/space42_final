-- =====================================================
-- SPACE42 HR Agent - Test Data SQL Script
-- Run this in your Supabase SQL Editor
-- =====================================================

-- =====================================================
-- 1. CREATE HR USERS (for testing HR portal)
-- =====================================================

-- Password for all HR users: TestHR123! (bcrypt hashed)
INSERT INTO hr_users (id, email, password_hash, first_name, last_name, department, role, created_at)
VALUES 
    (gen_random_uuid(), 'hr.admin@space42.ae', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy', 'Fatima', 'Al-Maktoum', 'Human Resources', 'HR Manager', NOW()),
    (gen_random_uuid(), 'talent@space42.ae', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy', 'Ahmed', 'Hassan', 'Human Resources', 'Talent Acquisition', NOW()),
    (gen_random_uuid(), 'recruiter@space42.ae', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy', 'Sarah', 'Johnson', 'Human Resources', 'Recruiter', NOW())
ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- 2. CREATE JOB ROLES
-- =====================================================

INSERT INTO job_roles (id, title, department, description, location, employment_type, experience_min, experience_max, non_negotiable_skills, preferred_skills, is_active, created_at)
VALUES 
    (gen_random_uuid(), 'Satellite Systems Engineer', 'Engineering', 
     'Design and develop satellite communication systems for next-generation space missions. Work with RF systems, payload integration, and ground station interfaces.',
     'Abu Dhabi, UAE', 'Full-time', 5, 10,
     '["RF Engineering", "Systems Integration", "Satellite Communications", "Python"]'::jsonb,
     '["MATLAB", "Antenna Design", "Space Mission Experience"]'::jsonb,
     true, NOW() - INTERVAL '30 days'),
     
    (gen_random_uuid(), 'Space Software Developer', 'Engineering',
     'Develop flight software and ground control systems for satellite operations. Focus on real-time systems and mission-critical applications.',
     'Abu Dhabi, UAE', 'Full-time', 3, 5,
     '["C++", "Python", "Real-time Systems", "Embedded Systems"]'::jsonb,
     '["RTOS", "Space Mission Software", "Flight Software"]'::jsonb,
     true, NOW() - INTERVAL '25 days'),
     
    (gen_random_uuid(), 'Mission Control Specialist', 'Operations',
     'Monitor and control satellite operations from our mission control center. Manage telemetry, execute commands, and ensure mission success.',
     'Abu Dhabi, UAE', 'Full-time', 2, 4,
     '["Operations", "Real-time Monitoring", "Communication Protocols"]'::jsonb,
     '["Satellite Operations", "Ground Systems", "Anomaly Resolution"]'::jsonb,
     true, NOW() - INTERVAL '20 days'),
     
    (gen_random_uuid(), 'Data Scientist - Earth Observation', 'Analytics',
     'Analyze satellite imagery and geospatial data to deliver insights for climate monitoring, urban planning, and defense applications.',
     'Dubai, UAE', 'Full-time', 3, 6,
     '["Python", "Machine Learning", "Remote Sensing", "Data Analysis"]'::jsonb,
     '["TensorFlow", "GIS", "Computer Vision"]'::jsonb,
     true, NOW() - INTERVAL '15 days'),
     
    (gen_random_uuid(), 'Systems Architect', 'Engineering',
     'Lead the architectural design of complex satellite systems. Define system requirements and ensure integration across subsystems.',
     'Abu Dhabi, UAE', 'Full-time', 8, 15,
     '["Systems Engineering", "Architecture Design", "Requirements Management"]'::jsonb,
     '["MBSE", "SysML", "Space Systems"]'::jsonb,
     true, NOW() - INTERVAL '10 days')
ON CONFLICT DO NOTHING;

-- =====================================================
-- 3. CREATE CANDIDATES (Test Users)
-- =====================================================

-- Password for all candidates: Test123! (bcrypt hashed)
INSERT INTO candidates (id, email, password_hash, first_name, last_name, phone, location, years_of_experience, created_at)
VALUES 
    -- Active Applicants
    (gen_random_uuid(), 'sarah.chen@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy', 
     'Sarah', 'Chen', '+971501234567', 'Dubai, UAE', 6, NOW() - INTERVAL '20 days'),
    (gen_random_uuid(), 'marcus.okonkwo@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Marcus', 'Okonkwo', '+971502345678', 'Abu Dhabi, UAE', 4, NOW() - INTERVAL '18 days'),
    (gen_random_uuid(), 'elena.vasquez@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Elena', 'Vasquez', '+971503456789', 'Sharjah, UAE', 5, NOW() - INTERVAL '15 days'),
    (gen_random_uuid(), 'james.wilson@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'James', 'Wilson', '+971504567890', 'Dubai, UAE', 7, NOW() - INTERVAL '12 days'),
    (gen_random_uuid(), 'priya.sharma@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Priya', 'Sharma', '+971505678901', 'Abu Dhabi, UAE', 3, NOW() - INTERVAL '10 days'),
     
    -- Shortlisted Candidates
    (gen_random_uuid(), 'alex.kim@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Alex', 'Kim', '+971506789012', 'Dubai, UAE', 8, NOW() - INTERVAL '25 days'),
    (gen_random_uuid(), 'nina.petrov@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Nina', 'Petrov', '+971507890123', 'Abu Dhabi, UAE', 5, NOW() - INTERVAL '22 days'),
     
    -- Interview Scheduled Candidates  
    (gen_random_uuid(), 'omar.hassan@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Omar', 'Hassan', '+971508901234', 'Dubai, UAE', 4, NOW() - INTERVAL '30 days'),
    (gen_random_uuid(), 'lisa.chen@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Lisa', 'Chen', '+971509012345', 'Abu Dhabi, UAE', 6, NOW() - INTERVAL '28 days'),
     
    -- Offered Candidates
    (gen_random_uuid(), 'aisha.al-nuaimi@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Aisha', 'Al-Nuaimi', '+971510123456', 'Abu Dhabi, UAE', 7, NOW() - INTERVAL '45 days'),
     
    -- Rejected Candidates
    (gen_random_uuid(), 'john.doe@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'John', 'Doe', '+971511234567', 'Dubai, UAE', 2, NOW() - INTERVAL '35 days'),
    (gen_random_uuid(), 'maria.santos@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Maria', 'Santos', '+971512345678', 'Sharjah, UAE', 1, NOW() - INTERVAL '32 days'),
     
    -- Onboarded Employees (accepted offers)
    (gen_random_uuid(), 'ahmed.khalifa@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Ahmed', 'Khalifa', '+971513456789', 'Abu Dhabi, UAE', 9, NOW() - INTERVAL '60 days'),
    (gen_random_uuid(), 'fatima.rahman@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'Fatima', 'Rahman', '+971514567890', 'Dubai, UAE', 5, NOW() - INTERVAL '55 days'),
    (gen_random_uuid(), 'david.chen@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.K5X8xK.qz5G0Hy',
     'David', 'Chen', '+971515678901', 'Abu Dhabi, UAE', 6, NOW() - INTERVAL '50 days')
ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- 4. CREATE CVs FOR CANDIDATES
-- =====================================================

INSERT INTO cvs (id, candidate_id, file_name, file_path, is_primary, parsed_data, parsing_status, uploaded_at)
SELECT 
    gen_random_uuid(),
    c.id,
    c.first_name || '_' || c.last_name || '_CV.pdf',
    '/uploads/' || c.id || '/cv.pdf',
    true,
    CASE 
        WHEN c.email = 'sarah.chen@email.com' THEN 
            '{"skills": {"technical": ["Python", "RF Engineering", "MATLAB", "Satellite Communications", "Systems Integration"], "soft": ["Leadership", "Communication", "Problem Solving"]}, "experience": [{"title": "RF Engineer", "company": "TechSpace Inc", "duration": "4 years"}], "education": [{"degree": "MSc Electrical Engineering", "institution": "MIT"}], "certifications": ["PMP", "AWS Solutions Architect"]}'::jsonb
        WHEN c.email = 'marcus.okonkwo@email.com' THEN
            '{"skills": {"technical": ["C++", "Embedded Systems", "Systems Integration", "Real-time Systems"], "soft": ["Teamwork", "Analytical Thinking"]}, "experience": [{"title": "Embedded Developer", "company": "SpaceTech", "duration": "3 years"}], "education": [{"degree": "BSc Computer Engineering", "institution": "Stanford"}]}'::jsonb
        WHEN c.email = 'alex.kim@email.com' THEN
            '{"skills": {"technical": ["C++", "Python", "Real-time Systems", "Flight Software", "RTOS", "Embedded Systems"], "soft": ["Leadership", "Technical Writing"]}, "experience": [{"title": "Senior Software Engineer", "company": "NASA JPL", "duration": "6 years"}], "education": [{"degree": "PhD Computer Science", "institution": "Caltech"}], "certifications": ["AWS", "CMMI"]}'::jsonb
        WHEN c.email = 'aisha.al-nuaimi@email.com' THEN
            '{"skills": {"technical": ["RF Engineering", "Systems Integration", "Satellite Communications", "Payload Design", "Python", "MATLAB"], "soft": ["Leadership", "Project Management", "Communication"]}, "experience": [{"title": "Lead Systems Engineer", "company": "Yahsat", "duration": "5 years"}], "education": [{"degree": "PhD Aerospace Engineering", "institution": "Imperial College London"}], "certifications": ["PMP", "Six Sigma"]}'::jsonb
        WHEN c.email = 'ahmed.khalifa@email.com' THEN
            '{"skills": {"technical": ["Systems Engineering", "Architecture Design", "Requirements Management", "MBSE", "SysML"], "soft": ["Leadership", "Strategic Thinking", "Mentoring"]}, "experience": [{"title": "Principal Systems Architect", "company": "Airbus Defence", "duration": "8 years"}], "education": [{"degree": "PhD Systems Engineering", "institution": "TU Delft"}], "certifications": ["INCOSE CSEP", "PMP"]}'::jsonb
        ELSE
            '{"skills": {"technical": ["Python", "Data Analysis"], "soft": ["Communication"]}, "experience": [], "education": [{"degree": "BSc", "institution": "University"}]}'::jsonb
    END,
    'completed',
    c.created_at
FROM candidates c
WHERE NOT EXISTS (SELECT 1 FROM cvs WHERE cvs.candidate_id = c.id);

-- =====================================================
-- 5. CREATE APPLICATIONS WITH VARIOUS STATUSES
-- =====================================================

DO $$
DECLARE
    satellite_job_id UUID;
    software_job_id UUID;
    mission_job_id UUID;
    data_job_id UUID;
    architect_job_id UUID;
BEGIN
    SELECT id INTO satellite_job_id FROM job_roles WHERE title = 'Satellite Systems Engineer' LIMIT 1;
    SELECT id INTO software_job_id FROM job_roles WHERE title = 'Space Software Developer' LIMIT 1;
    SELECT id INTO mission_job_id FROM job_roles WHERE title = 'Mission Control Specialist' LIMIT 1;
    SELECT id INTO data_job_id FROM job_roles WHERE title = 'Data Scientist - Earth Observation' LIMIT 1;
    SELECT id INTO architect_job_id FROM job_roles WHERE title = 'Systems Architect' LIMIT 1;

    -- Applied status applications
    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, satellite_job_id, cv.id, 'applied', 75, true, NOW() - INTERVAL '5 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'sarah.chen@email.com'
    ON CONFLICT DO NOTHING;

    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, software_job_id, cv.id, 'applied', 70, true, NOW() - INTERVAL '4 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'marcus.okonkwo@email.com'
    ON CONFLICT DO NOTHING;

    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, satellite_job_id, cv.id, 'applied', 68, true, NOW() - INTERVAL '3 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'elena.vasquez@email.com'
    ON CONFLICT DO NOTHING;

    -- Shortlisted applications (with behavioral scores)
    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, software_job_id, cv.id, 'shortlisted', 92, 88, 89.6, true, NOW() - INTERVAL '15 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'alex.kim@email.com'
    ON CONFLICT DO NOTHING;

    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, software_job_id, cv.id, 'shortlisted', 85, 82, 83.2, true, NOW() - INTERVAL '12 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'nina.petrov@email.com'
    ON CONFLICT DO NOTHING;

    -- Interview scheduled applications
    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, mission_job_id, cv.id, 'interview_scheduled', 78, 85, 82.2, true, NOW() - INTERVAL '20 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'omar.hassan@email.com'
    ON CONFLICT DO NOTHING;

    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, satellite_job_id, cv.id, 'interview_scheduled', 88, 90, 89.2, true, NOW() - INTERVAL '18 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'lisa.chen@email.com'
    ON CONFLICT DO NOTHING;

    -- Offered application
    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, satellite_job_id, cv.id, 'offered', 94, 92, 92.8, true, NOW() - INTERVAL '35 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'aisha.al-nuaimi@email.com'
    ON CONFLICT DO NOTHING;

    -- Rejected applications
    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, software_job_id, cv.id, 'rejected', 45, 55, 51, false, NOW() - INTERVAL '25 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'john.doe@email.com'
    ON CONFLICT DO NOTHING;

    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, mission_job_id, cv.id, 'rejected', 52, 60, 56.8, false, NOW() - INTERVAL '22 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'maria.santos@email.com'
    ON CONFLICT DO NOTHING;

    -- Onboarded employees (offered status)
    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, architect_job_id, cv.id, 'offered', 96, 94, 94.8, true, NOW() - INTERVAL '50 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'ahmed.khalifa@email.com'
    ON CONFLICT DO NOTHING;

    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, data_job_id, cv.id, 'offered', 90, 88, 88.8, true, NOW() - INTERVAL '45 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'fatima.rahman@email.com'
    ON CONFLICT DO NOTHING;

    INSERT INTO applications (id, candidate_id, job_role_id, cv_id, status, technical_score, behavioral_score, combined_score, eligibility_check_passed, applied_date)
    SELECT gen_random_uuid(), c.id, software_job_id, cv.id, 'offered', 88, 85, 86.2, true, NOW() - INTERVAL '40 days'
    FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id WHERE c.email = 'david.chen@email.com'
    ON CONFLICT DO NOTHING;

END $$;

-- =====================================================
-- 6. CREATE BEHAVIORAL ASSESSMENT SCORES
-- =====================================================

INSERT INTO behavioral_assessment_scores (id, application_id, overall_score, communication_score, problem_solving_score, cultural_fit_score, summary, created_at)
SELECT 
    gen_random_uuid(),
    a.id,
    a.behavioral_score,
    CASE WHEN a.behavioral_score >= 90 THEN 92 WHEN a.behavioral_score >= 80 THEN 82 WHEN a.behavioral_score >= 60 THEN 62 ELSE 52 END,
    CASE WHEN a.behavioral_score >= 90 THEN 90 WHEN a.behavioral_score >= 80 THEN 85 WHEN a.behavioral_score >= 60 THEN 65 ELSE 50 END,
    CASE WHEN a.behavioral_score >= 90 THEN 88 WHEN a.behavioral_score >= 80 THEN 80 WHEN a.behavioral_score >= 60 THEN 58 ELSE 48 END,
    CASE 
        WHEN a.behavioral_score >= 90 THEN 
            'Exceptional candidate demonstrating strong leadership potential, excellent communication skills, and outstanding problem-solving abilities. Highly recommended for advancement.'
        WHEN a.behavioral_score >= 80 THEN
            'Strong candidate with good communication skills and solid teamwork abilities. Shows good adaptability and potential for growth.'
        WHEN a.behavioral_score >= 60 THEN
            'Candidate shows potential but may need development in leadership and communication areas. Recommended for roles with mentorship support.'
        ELSE
            'Candidate needs significant development in multiple areas. May be better suited for junior roles with extensive training.'
    END,
    a.applied_date + INTERVAL '2 days'
FROM applications a
WHERE a.behavioral_score IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM behavioral_assessment_scores WHERE application_id = a.id);

-- =====================================================
-- 7. CREATE INTERVIEWS FOR SCHEDULED CANDIDATES
-- =====================================================

INSERT INTO interviews (id, application_id, interview_type, scheduled_date, duration_minutes, location, interviewer_ids, status, created_at)
SELECT 
    gen_random_uuid(),
    a.id,
    'Video Call',
    NOW() + INTERVAL '3 days',
    60,
    'Google Meet',
    '["hr.admin@space42.ae", "talent@space42.ae"]'::jsonb,
    'scheduled',
    NOW()
FROM applications a
WHERE a.status = 'interview_scheduled'
AND NOT EXISTS (SELECT 1 FROM interviews WHERE application_id = a.id);

-- =====================================================
-- 8. CREATE HR FEEDBACK / INTERVIEW NOTES
-- =====================================================

INSERT INTO hr_feedback (id, application_id, hr_user_id, feedback_type, strengths, weaknesses, missing_requirements, role_fit_score, recommendation, additional_notes, created_at)
SELECT 
    gen_random_uuid(),
    a.id,
    (SELECT id FROM hr_users WHERE email = 'hr.admin@space42.ae' LIMIT 1),
    'interview',
    CASE 
        WHEN a.status = 'offered' THEN 'Exceptional technical depth, excellent communication skills, strong leadership potential'
        WHEN a.status = 'shortlisted' THEN 'Good technical foundation, shows enthusiasm and willingness to learn'
        WHEN a.status = 'interview_scheduled' THEN 'Solid experience, good cultural fit potential'
        ELSE 'Some relevant experience, positive attitude'
    END,
    CASE 
        WHEN a.status = 'rejected' THEN 'Limited experience in the specific domain, needs more hands-on project work'
        WHEN a.status = 'applied' THEN 'Could improve on leadership skills'
        ELSE NULL
    END,
    CASE 
        WHEN a.status = 'rejected' THEN 'Missing critical skills: real-time systems experience, spacecraft software'
        ELSE NULL
    END,
    CASE 
        WHEN a.status = 'offered' THEN 9
        WHEN a.status = 'shortlisted' THEN 7
        WHEN a.status = 'interview_scheduled' THEN 7
        WHEN a.status = 'rejected' THEN 4
        ELSE 6
    END,
    CASE 
        WHEN a.status = 'offered' THEN 'hire'
        WHEN a.status IN ('shortlisted', 'interview_scheduled') THEN 'maybe'
        WHEN a.status = 'rejected' THEN 'reject'
        ELSE 'maybe'
    END,
    'Notes from initial interview round.',
    a.applied_date + INTERVAL '5 days'
FROM applications a
WHERE a.status IN ('offered', 'shortlisted', 'interview_scheduled', 'rejected')
AND NOT EXISTS (SELECT 1 FROM hr_feedback WHERE application_id = a.id);

-- =====================================================
-- 9. VERIFY DATA
-- =====================================================

-- Check counts
SELECT 'HR Users' as table_name, COUNT(*) as count FROM hr_users
UNION ALL
SELECT 'Job Roles', COUNT(*) FROM job_roles
UNION ALL
SELECT 'Candidates', COUNT(*) FROM candidates
UNION ALL
SELECT 'CVs', COUNT(*) FROM cvs
UNION ALL
SELECT 'Applications', COUNT(*) FROM applications
UNION ALL
SELECT 'Behavioral Assessments', COUNT(*) FROM behavioral_assessment_scores
UNION ALL
SELECT 'Interviews', COUNT(*) FROM interviews
UNION ALL
SELECT 'HR Feedback/Notes', COUNT(*) FROM hr_feedback;

-- Show application status distribution
SELECT status, COUNT(*) as count 
FROM applications 
GROUP BY status 
ORDER BY count DESC;

-- =====================================================
-- TEST ACCOUNTS SUMMARY
-- =====================================================
/*
HR ACCOUNTS (all passwords: TestHR123!):
- hr.admin@space42.ae (HR Manager)
- talent@space42.ae (Talent Acquisition)
- recruiter@space42.ae (Recruiter)

CANDIDATE ACCOUNTS (all passwords: Test123!):
Applied:
- sarah.chen@email.com
- marcus.okonkwo@email.com
- elena.vasquez@email.com

Shortlisted:
- alex.kim@email.com
- nina.petrov@email.com

Interview Scheduled:
- omar.hassan@email.com
- lisa.chen@email.com

Offered:
- aisha.al-nuaimi@email.com

Rejected:
- john.doe@email.com
- maria.santos@email.com

Onboarded Employees:
- ahmed.khalifa@email.com
- fatima.rahman@email.com
- david.chen@email.com
*/
