"""
Email Service for SPACE42 HR Agent
Handles sending personalized emails for various HR events.
Uses aiosmtplib for async email sending and LangChain for AI-generated feedback.
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
import os
from jinja2 import Template

# Try to use Groq (existing) or OpenAI for AI feedback
try:
    from services.ai_service import chat_completion as groq_chat_completion
    USE_GROQ = True
except ImportError:
    USE_GROQ = False

# LangChain imports for OpenAI customization (optional)
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain.chat_models import ChatOpenAI  # type: ignore
        from langchain.prompts import ChatPromptTemplate  # type: ignore
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False

# Email configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "hr@space42.ae")
FROM_NAME = os.getenv("FROM_NAME", "SPACE42 HR Team")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ============ Email Templates ============

REJECTION_EMAIL_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
        .feedback-box { background: #fff; border-left: 4px solid #8b5cf6; padding: 15px; margin: 20px 0; }
        .footer { background: #1f2937; color: #9ca3af; padding: 20px; text-align: center; font-size: 12px; border-radius: 0 0 10px 10px; }
        .cta-button { display: inline-block; background: #8b5cf6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SPACE42</h1>
            <p>Application Update</p>
        </div>
        <div class="content">
            <p>Dear {{ candidate_name }},</p>
            
            <p>Thank you for your interest in the <strong>{{ role_title }}</strong> position at SPACE42 and for taking the time to go through our application process.</p>
            
            <p>After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs for this particular role.</p>
            
            {% if feedback %}
            <div class="feedback-box">
                <strong>💡 Personalized Feedback:</strong>
                <p>{{ feedback }}</p>
            </div>
            {% endif %}
            
            <p>This decision was not easy, as we received many strong applications. We were genuinely impressed by your background and encourage you to apply for future positions that align with your skills and experience.</p>
            
            <p>We will keep your profile in our talent network and reach out if a suitable opportunity arises.</p>
            
            <a href="https://careers.space42.ae" class="cta-button">View Other Opportunities</a>
            
            <p style="margin-top: 30px;">Thank you again for considering SPACE42 as a potential employer. We wish you all the best in your career journey.</p>
            
            <p>Warm regards,<br>
            <strong>The SPACE42 HR Team</strong></p>
        </div>
        <div class="footer">
            <p>SPACE42 | Pioneering the Future of Space Technology</p>
            <p>Abu Dhabi, UAE | careers.space42.ae</p>
        </div>
    </div>
</body>
</html>
""")

INTERVIEW_EMAIL_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
        .details-box { background: #fff; border: 1px solid #22c55e; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .detail-row { display: flex; margin: 10px 0; }
        .detail-icon { width: 30px; font-size: 18px; }
        .footer { background: #1f2937; color: #9ca3af; padding: 20px; text-align: center; font-size: 12px; border-radius: 0 0 10px 10px; }
        .cta-button { display: inline-block; background: #22c55e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 5px; }
        .tips-box { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Interview Scheduled!</h1>
            <p>SPACE42</p>
        </div>
        <div class="content">
            <p>Dear {{ candidate_name }},</p>
            
            <p>Great news! We are pleased to invite you for an interview for the <strong>{{ role_title }}</strong> position at SPACE42.</p>
            
            <div class="details-box">
                <h3 style="margin-top: 0; color: #16a34a;">📋 Interview Details</h3>
                <div class="detail-row">
                    <span class="detail-icon">📅</span>
                    <span><strong>Date & Time:</strong> {{ interview_date }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-icon">📍</span>
                    <span><strong>Type:</strong> {{ interview_type }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-icon">👤</span>
                    <span><strong>With:</strong> {{ interviewer }}</span>
                </div>
                {% if meeting_link %}
                <div class="detail-row">
                    <span class="detail-icon">🔗</span>
                    <span><strong>Meeting Link:</strong> <a href="{{ meeting_link }}">{{ meeting_link }}</a></span>
                </div>
                {% endif %}
            </div>
            
            {% if meeting_link %}
            <a href="{{ meeting_link }}" class="cta-button">Join Interview</a>
            {% endif %}
            
            <div class="tips-box">
                <strong>💡 Tips for your interview:</strong>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Research SPACE42 and our mission in space technology</li>
                    <li>Prepare examples from your experience that demonstrate your skills</li>
                    <li>Have questions ready about the role and team</li>
                    {% if interview_type == 'Video Call' %}
                    <li>Test your video/audio setup beforehand</li>
                    {% endif %}
                </ul>
            </div>
            
            <p>Please confirm your attendance by replying to this email. If you need to reschedule, let us know at least 24 hours in advance.</p>
            
            <p>We look forward to speaking with you!</p>
            
            <p>Best regards,<br>
            <strong>The SPACE42 HR Team</strong></p>
        </div>
        <div class="footer">
            <p>SPACE42 | Pioneering the Future of Space Technology</p>
            <p>Abu Dhabi, UAE | careers.space42.ae</p>
        </div>
    </div>
</body>
</html>
""")

OFFER_EMAIL_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
        .congrats-box { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }
        .steps-box { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .footer { background: #1f2937; color: #9ca3af; padding: 20px; text-align: center; font-size: 12px; border-radius: 0 0 10px 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Congratulations!</h1>
            <p>Job Offer from SPACE42</p>
        </div>
        <div class="content">
            <p>Dear {{ candidate_name }},</p>
            
            <div class="congrats-box">
                <h2 style="margin: 0; color: #92400e;">Welcome to the SPACE42 Family!</h2>
                <p style="margin: 10px 0 0 0;">We are thrilled to offer you the position of</p>
                <h3 style="margin: 5px 0; color: #1f2937;">{{ role_title }}</h3>
            </div>
            
            <p>After a thorough evaluation process, we were very impressed by your skills, experience, and the passion you demonstrated throughout our conversations. We believe you will be a valuable addition to our team as we continue to push the boundaries of space technology.</p>
            
            <div class="steps-box">
                <h3 style="margin-top: 0;">📋 Next Steps</h3>
                <ol>
                    <li>Review the detailed offer letter (attached/to follow)</li>
                    <li>Complete the background verification process</li>
                    <li>Sign and return the offer acceptance</li>
                    <li>Coordinate your start date with HR</li>
                </ol>
            </div>
            
            <p>Please respond within <strong>5 business days</strong> to confirm your acceptance. If you have any questions about the offer or SPACE42, don't hesitate to reach out.</p>
            
            <p>We can't wait to have you on board!</p>
            
            <p>Warm regards,<br>
            <strong>The SPACE42 HR Team</strong></p>
        </div>
        <div class="footer">
            <p>SPACE42 | Pioneering the Future of Space Technology</p>
            <p>Abu Dhabi, UAE | careers.space42.ae</p>
        </div>
    </div>
</body>
</html>
""")


# ============ AI Feedback Generation ============

async def generate_ai_rejection_feedback(
    candidate_name: str,
    role_title: str,
    candidate_resume: str = "",
    role_description: str = "",
    feedback_summary: str = ""
) -> str:
    """
    Use AI to generate personalized feedback for rejection.
    Tries Groq first (existing), then OpenAI via LangChain.
    """
    # If we have assessment feedback, use it as base
    if feedback_summary:
        return feedback_summary
    
    prompt_text = f"""
    You are a kind and professional HR Manager at SPACE42, a leading space technology company.
    Write a 1-2 sentence personalized feedback for a candidate named {candidate_name} 
    who is being rejected for the {role_title} position.
    
    Role Description: {role_description[:500] if role_description else 'Not provided'}
    Candidate Background: {candidate_resume[:500] if candidate_resume else 'Not provided'}
    
    Focus on one specific area where they could improve or where their background didn't 
    quite align with this specific role. Be encouraging and constructive.
    
    Feedback:
    """
    
    # Try Groq first (existing SPACE42 setup)
    if USE_GROQ:
        try:
            response = await groq_chat_completion(
                system_prompt="You are a compassionate HR professional providing constructive feedback.",
                user_message=prompt_text,
                temperature=0.7,
                max_tokens=150
            )
            return response.strip()
        except Exception as e:
            print(f"Groq feedback generation failed: {e}")
    
    # Try OpenAI via LangChain
    if LANGCHAIN_AVAILABLE and OPENAI_API_KEY:
        try:
            llm = ChatOpenAI(
                openai_api_key=OPENAI_API_KEY,
                model_name="gpt-4o",
                temperature=0.7
            )
            
            prompt = ChatPromptTemplate.from_template("""
            You are a kind and professional HR Manager at SPACE42.
            Write a 1-2 sentence personalized feedback for a candidate named {candidate_name} 
            who is being rejected for the {role_title} position.
            
            Role Description: {role_description}
            Candidate Background: {candidate_resume}
            
            Focus on one specific area where they could improve. Be encouraging.
            
            Feedback:
            """)
            
            messages = prompt.format_messages(
                candidate_name=candidate_name,
                role_title=role_title,
                role_description=role_description[:500] if role_description else "Not provided",
                candidate_resume=candidate_resume[:500] if candidate_resume else "Not provided"
            )
            
            response = await llm.apredict_messages(messages)
            return response.content.strip()
        except Exception as e:
            print(f"OpenAI feedback generation failed: {e}")
    
    # Default fallback
    return "We have decided to move forward with candidates whose qualifications more closely match our current needs for this specific role. We encourage you to continue developing your skills and apply for future opportunities."


# ============ Email Sending Functions ============

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = ""
) -> bool:
    """
    Send an email using aiosmtplib.
    Returns True if successful, False otherwise.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"\n{'='*60}")
        print(f"📧 EMAIL SIMULATION (SMTP not configured)")
        print(f"{'='*60}")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Preview: {text_content[:300] if text_content else html_content[:300]}...")
        print(f"{'='*60}\n")
        return True  # Simulate success when no SMTP configured
    
    try:
        message = MIMEMultipart("alternative")
        message["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        # Attach both plain text and HTML versions
        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=True
        )
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False


async def send_rejection_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    candidate_skills: list = None,
    feedback_summary: str = None,
    role_description: str = "",
    candidate_resume: str = ""
) -> bool:
    """
    Send a personalized rejection email to a candidate.
    """
    # Generate AI feedback
    feedback = await generate_ai_rejection_feedback(
        candidate_name=candidate_name,
        role_title=job_title,
        candidate_resume=candidate_resume,
        role_description=role_description,
        feedback_summary=feedback_summary
    )
    
    # Render HTML template
    html_content = REJECTION_EMAIL_TEMPLATE.render(
        candidate_name=candidate_name,
        role_title=job_title,
        feedback=feedback
    )
    
    # Plain text version
    text_content = f"""
Dear {candidate_name},

Thank you for your interest in the {job_title} position at SPACE42.

After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.

{f'Feedback: {feedback}' if feedback else ''}

We appreciate the time you invested and wish you the best in your career.

Best regards,
The SPACE42 HR Team
    """
    
    return await send_email(
        to_email=candidate_email,
        subject=f"Application Update - {job_title} | SPACE42",
        html_content=html_content,
        text_content=text_content
    )


async def send_interview_scheduled_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    interview_date: str,
    interview_type: str,
    interviewer: str,
    meeting_link: str = None
) -> bool:
    """
    Send interview scheduling confirmation email.
    """
    html_content = INTERVIEW_EMAIL_TEMPLATE.render(
        candidate_name=candidate_name,
        role_title=job_title,
        interview_date=interview_date,
        interview_type=interview_type,
        interviewer=interviewer,
        meeting_link=meeting_link
    )
    
    text_content = f"""
Dear {candidate_name},

Great news! We are pleased to invite you for an interview for the {job_title} position at SPACE42.

Interview Details:
- Date & Time: {interview_date}
- Type: {interview_type}
- With: {interviewer}
{f'- Meeting Link: {meeting_link}' if meeting_link else ''}

Please confirm your attendance by replying to this email.

Best regards,
The SPACE42 HR Team
    """
    
    return await send_email(
        to_email=candidate_email,
        subject=f"🎉 Interview Scheduled: {job_title} | SPACE42",
        html_content=html_content,
        text_content=text_content
    )


async def send_offer_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str
) -> bool:
    """
    Send job offer email.
    """
    html_content = OFFER_EMAIL_TEMPLATE.render(
        candidate_name=candidate_name,
        role_title=job_title
    )
    
    text_content = f"""
Dear {candidate_name},

Congratulations!

On behalf of the entire team at SPACE42, I am thrilled to extend an offer for the position of {job_title}.

We were very impressed by your skills and believe you will be a valuable addition to our team.

Next Steps:
1. Review the detailed offer letter
2. Complete background verification
3. Sign and return the offer acceptance
4. Coordinate your start date with HR

Please respond within 5 business days.

Welcome to the SPACE42 family!

Best regards,
The SPACE42 HR Team
    """
    
    return await send_email(
        to_email=candidate_email,
        subject=f"🎉 Job Offer: {job_title} | SPACE42",
        html_content=html_content,
        text_content=text_content
    )


# ============ Bulk Operations ============

async def bulk_send_rejections(
    application_ids: List[str],
    exclude_application_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Send rejection emails to multiple candidates.
    Used when accepting one candidate and rejecting others.
    """
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    results = {"total": 0, "sent": 0, "failed": 0}
    
    for app_id in application_ids:
        if exclude_application_id and app_id == exclude_application_id:
            continue
            
        results["total"] += 1
        
        try:
            # Get application details
            app_result = supabase.table('applications').select("*").eq('id', app_id).execute()
            if not app_result.data:
                results["failed"] += 1
                continue
                
            app = app_result.data[0]
            
            # Get candidate details
            candidate_result = supabase.table('candidates').select("*").eq('id', app['candidate_id']).execute()
            if not candidate_result.data:
                results["failed"] += 1
                continue
                
            candidate = candidate_result.data[0]
            
            # Get job details
            job_result = supabase.table('job_roles').select("*").eq('id', app['job_role_id']).execute()
            job = job_result.data[0] if job_result.data else {}
            
            # Get CV/resume text if available
            resume_text = ""
            if app.get('cv_id'):
                cv_result = supabase.table('cvs').select("parsed_data").eq('id', app['cv_id']).execute()
                if cv_result.data and cv_result.data[0].get('parsed_data'):
                    parsed = cv_result.data[0]['parsed_data']
                    skills = parsed.get('skills', {})
                    if isinstance(skills, dict):
                        resume_text = ", ".join(skills.get('technical', []))
            
            # Get feedback from multiple sources
            feedback_parts = []
            
            # 1. Get HR notes/feedback
            try:
                hr_feedback_result = supabase.table('hr_feedback').select(
                    "weaknesses, missing_requirements"
                ).eq('application_id', app_id).order('created_at', desc=True).execute()
                
                if hr_feedback_result.data:
                    for fb in hr_feedback_result.data:
                        if fb.get('weaknesses'):
                            feedback_parts.append(f"Areas for improvement: {fb['weaknesses']}")
                        if fb.get('missing_requirements'):
                            feedback_parts.append(f"Skills to develop: {fb['missing_requirements']}")
            except:
                pass
            
            # 2. Get behavioral assessment feedback
            try:
                assessment_result = supabase.table('behavioral_assessment_scores').select(
                    "summary"
                ).eq('application_id', app_id).limit(1).execute()
                if assessment_result.data and assessment_result.data[0].get('summary'):
                    feedback_parts.append(assessment_result.data[0]['summary'])
            except:
                pass
            
            feedback_summary = ". ".join(feedback_parts[:2]) if feedback_parts else None
            
            # Update application status
            supabase.table('applications').update({
                "status": "rejected"
            }).eq('id', app_id).execute()
            
            # Get candidate name
            candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
            if not candidate_name:
                candidate_name = candidate['email'].split('@')[0]
            
            # Send rejection email
            success = await send_rejection_email(
                candidate_email=candidate['email'],
                candidate_name=candidate_name,
                job_title=job.get('title', 'the position'),
                feedback_summary=feedback_summary,
                role_description=job.get('description', ''),
                candidate_resume=resume_text
            )
            
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1
                
        except Exception as e:
            print(f"Error processing rejection for {app_id}: {e}")
            results["failed"] += 1
    
    return results
