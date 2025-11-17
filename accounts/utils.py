from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(user_email, code, purpose="verification"):
    """
    Helper function to send OTP via email
    """
    subject = f"Your OTP Code - {purpose.title()}"
    message = f"""
    Hello,
    
    Your OTP code is: {code}
    
    This code will expire in 10 minutes.
    
    If you did not request this code, please ignore this email.
    
    Best regards,
    Global Creole Society Team
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False
