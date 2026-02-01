import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import settings
from jinja2 import Template


async def send_rejection_email(
    candidate_email: str,
    candidate_name: str,
    role_title: str,
    feedback: Optional[str] = None
) -> bool:
    """
    Send rejection email to candidate with feedback
    """
    if not settings.smtp_server or not settings.email_from:
        print(f"Email not configured. Would send to {candidate_email}: Rejection for {role_title}")
        if feedback:
            print(f"Feedback: {feedback}")
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["From"] = settings.email_from
        message["To"] = candidate_email
        message["Subject"] = f"Application Update - {role_title}"
        
        email_template = Template("""
        <html>
        <body>
            <p>Dear {{ candidate_name }},</p>
            
            <p>Thank you for your interest in the {{ role_title }} position at our company.</p>
            
            <p>After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.</p>
            
            {% if feedback %}
            <p><strong>Feedback:</strong></p>
            <p>{{ feedback }}</p>
            {% endif %}
            
            <p>We appreciate the time you invested in the application process and wish you the best in your career endeavors.</p>
            
            <p>Best regards,<br>
            HR Team</p>
        </body>
        </html>
        """)
        
        html_content = email_template.render(
            candidate_name=candidate_name,
            role_title=role_title,
            feedback=feedback
        )
        
        text_content = f"""
        Dear {candidate_name},
        
        Thank you for your interest in the {role_title} position.
        
        After careful consideration, we have decided to move forward with other candidates.
        
        {f'Feedback: {feedback}' if feedback else ''}
        
        Best regards,
        HR Team
        """
        
        message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))
        
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_server,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=True
        )
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
