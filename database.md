-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.admin_users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email character varying NOT NULL UNIQUE,
  password_hash character varying NOT NULL,
  first_name character varying NOT NULL,
  last_name character varying NOT NULL,
  created_at timestamp without time zone DEFAULT now(),
  is_active boolean DEFAULT true,
  CONSTRAINT admin_users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.applications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  candidate_id uuid NOT NULL,
  job_role_id uuid NOT NULL,
  cv_id uuid NOT NULL,
  status character varying DEFAULT 'applied'::character varying,
  applied_date timestamp without time zone DEFAULT now(),
  cover_letter text,
  technical_score numeric,
  behavioral_score numeric,
  combined_score numeric,
  rank_in_role integer,
  eligibility_check_passed boolean,
  eligibility_details jsonb,
  ai_evaluation_completed_at timestamp without time zone,
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT applications_pkey PRIMARY KEY (id),
  CONSTRAINT applications_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id),
  CONSTRAINT applications_job_role_id_fkey FOREIGN KEY (job_role_id) REFERENCES public.job_roles(id),
  CONSTRAINT applications_cv_id_fkey FOREIGN KEY (cv_id) REFERENCES public.cvs(id)
);
CREATE TABLE public.behavioral_assessment_scores (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid UNIQUE,
  application_id uuid,
  overall_score numeric,
  communication_score numeric,
  problem_solving_score numeric,
  cultural_fit_score numeric,
  summary text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT behavioral_assessment_scores_pkey PRIMARY KEY (id),
  CONSTRAINT behavioral_assessment_scores_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id),
  CONSTRAINT behavioral_assessment_scores_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id)
);
CREATE TABLE public.candidates (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email character varying NOT NULL UNIQUE,
  password_hash character varying NOT NULL,
  first_name character varying NOT NULL,
  last_name character varying NOT NULL,
  phone character varying,
  location character varying,
  years_of_experience integer,
  current_company character varying,
  current_position character varying,
  linkedin_url character varying,
  portfolio_url character varying,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  last_login timestamp without time zone,
  is_active boolean DEFAULT true,
  CONSTRAINT candidates_pkey PRIMARY KEY (id)
);
CREATE TABLE public.conversations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_type character varying,
  participant_id uuid,
  messages jsonb,
  status character varying DEFAULT 'active'::character varying,
  started_at timestamp without time zone DEFAULT now(),
  completed_at timestamp without time zone,
  CONSTRAINT conversations_pkey PRIMARY KEY (id)
);
CREATE TABLE public.cvs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  candidate_id uuid NOT NULL,
  file_name character varying NOT NULL,
  file_path character varying NOT NULL,
  file_size integer,
  file_type character varying,
  is_primary boolean DEFAULT false,
  parsed_data jsonb,
  parsing_status character varying DEFAULT 'pending'::character varying,
  parsing_completed_at timestamp without time zone,
  uploaded_at timestamp without time zone DEFAULT now(),
  CONSTRAINT cvs_pkey PRIMARY KEY (id),
  CONSTRAINT cvs_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id)
);
CREATE TABLE public.embeddings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  content text NOT NULL,
  embedding USER-DEFINED,
  metadata jsonb DEFAULT '{}'::jsonb,
  source_type character varying NOT NULL,
  source_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT embeddings_pkey PRIMARY KEY (id)
);
CREATE TABLE public.faq_content (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  category character varying NOT NULL,
  question text NOT NULL,
  answer text NOT NULL,
  keywords jsonb,
  related_job_role_id uuid,
  related_department character varying,
  is_active boolean DEFAULT true,
  view_count integer DEFAULT 0,
  helpful_count integer DEFAULT 0,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT faq_content_pkey PRIMARY KEY (id),
  CONSTRAINT faq_content_related_job_role_id_fkey FOREIGN KEY (related_job_role_id) REFERENCES public.job_roles(id)
);
CREATE TABLE public.hr_feedback (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  application_id uuid NOT NULL,
  interview_id uuid,
  hr_user_id uuid NOT NULL,
  feedback_type character varying NOT NULL,
  strengths text,
  weaknesses text,
  missing_requirements text,
  role_fit_score integer,
  recommendation character varying,
  additional_notes text,
  is_used_for_training boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT hr_feedback_pkey PRIMARY KEY (id),
  CONSTRAINT hr_feedback_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id),
  CONSTRAINT hr_feedback_interview_id_fkey FOREIGN KEY (interview_id) REFERENCES public.interviews(id),
  CONSTRAINT hr_feedback_hr_user_id_fkey FOREIGN KEY (hr_user_id) REFERENCES public.hr_users(id)
);
CREATE TABLE public.hr_users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email character varying NOT NULL UNIQUE,
  password_hash character varying NOT NULL,
  first_name character varying NOT NULL,
  last_name character varying NOT NULL,
  department character varying,
  role character varying,
  created_at timestamp without time zone DEFAULT now(),
  is_active boolean DEFAULT true,
  CONSTRAINT hr_users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.interviews (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  application_id uuid NOT NULL,
  interview_type character varying NOT NULL,
  scheduled_date timestamp without time zone,
  duration_minutes integer DEFAULT 60,
  location character varying,
  interviewer_ids jsonb,
  status character varying DEFAULT 'scheduled'::character varying,
  reschedule_count integer DEFAULT 0,
  reschedule_reason text,
  completion_notes text,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT interviews_pkey PRIMARY KEY (id),
  CONSTRAINT interviews_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id)
);
CREATE TABLE public.job_roles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title character varying NOT NULL,
  department character varying NOT NULL,
  description text,
  responsibilities text,
  location character varying,
  work_type character varying,
  employment_type character varying,
  salary_min numeric,
  salary_max numeric,
  currency character varying DEFAULT 'AED'::character varying,
  experience_min integer,
  experience_max integer,
  non_negotiable_skills jsonb,
  preferred_skills jsonb,
  is_active boolean DEFAULT true,
  openings_count integer DEFAULT 1,
  posted_date date DEFAULT CURRENT_DATE,
  closing_date date,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT job_roles_pkey PRIMARY KEY (id)
);
CREATE TABLE public.new_hire_onboarding (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  candidate_id uuid NOT NULL UNIQUE,
  application_id uuid NOT NULL UNIQUE,
  template_id uuid NOT NULL,
  start_date date NOT NULL,
  expected_completion_date date,
  actual_completion_date date,
  status character varying DEFAULT 'in_progress'::character varying,
  completion_percentage numeric DEFAULT 0.00,
  progress jsonb NOT NULL DEFAULT '[]'::jsonb,
  manager_hr_id uuid,
  department character varying,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT new_hire_onboarding_pkey PRIMARY KEY (id),
  CONSTRAINT new_hire_onboarding_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id),
  CONSTRAINT new_hire_onboarding_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id),
  CONSTRAINT new_hire_onboarding_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.onboarding_templates(id),
  CONSTRAINT new_hire_onboarding_manager_hr_id_fkey FOREIGN KEY (manager_hr_id) REFERENCES public.hr_users(id)
);
CREATE TABLE public.notifications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  user_type character varying NOT NULL,
  notification_type character varying NOT NULL,
  title character varying NOT NULL,
  message text NOT NULL,
  reference_type character varying,
  reference_id uuid,
  priority character varying DEFAULT 'normal'::character varying,
  is_read boolean DEFAULT false,
  is_email_sent boolean DEFAULT false,
  created_at timestamp without time zone DEFAULT now(),
  read_at timestamp without time zone,
  email_sent_at timestamp without time zone,
  CONSTRAINT notifications_pkey PRIMARY KEY (id)
);
CREATE TABLE public.onboarding_templates (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  template_name character varying NOT NULL,
  department character varying,
  role_type character varying,
  description text,
  items jsonb NOT NULL,
  is_active boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT onboarding_templates_pkey PRIMARY KEY (id)
);
CREATE TABLE public.team_directory (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  user_type character varying NOT NULL,
  department character varying NOT NULL,
  team_name character varying,
  position character varying NOT NULL,
  manager_id uuid,
  bio text,
  expertise_areas jsonb,
  profile_photo_url character varying,
  work_location character varying,
  is_active boolean DEFAULT true,
  joined_date date,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT team_directory_pkey PRIMARY KEY (id)
);