import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config

class EmailService:
    # Ambil dari Config (bukan hardcoded)
    SMTP_HOST = Config.SMTP_HOST
    SMTP_PORT = Config.SMTP_PORT
    SMTP_USER = Config.SMTP_USER
    SMTP_PASSWORD = Config.SMTP_PASSWORD
    FROM_EMAIL = Config.SMTP_FROM_EMAIL
    APP_NAME = "Bug Bounty"
    
    @staticmethod
    def send_reset_password_email(to_email: str, reset_token: str, frontend_url: str = None):
        """Send password reset email"""
        if not frontend_url:
            frontend_url = "https://fountguard.com/reset-password"
        
        reset_link = f"{frontend_url}?token={reset_token}"
        
        subject = "Reset Your Password"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1a237e; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; background-color: #f5f5f5; }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #1a237e;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .warning {{ color: #d32f2f; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{EmailService.APP_NAME}</h2>
                </div>
                <div class="content">
                    <h3>Hello,</h3>
                    <p>We received a request to reset your password.</p>
                    <p>Click the button below to create a new password:</p>
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </div>
                    <p><strong>This link will expire in 20 minutes.</strong></p>
                    <p class="warning">⚠️ If you did not request a password reset, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>Thank you,<br>{EmailService.APP_NAME}</p>
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_body = f"""
        Hello,
        
        We received a request to reset your password.
        
        Click the link below to create a new password:
        {reset_link}
        
        This link will expire in 20 minutes.
        
        If you did not request a password reset, you can safely ignore this email.
        
        Thank you,
        {EmailService.APP_NAME}
        """
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = EmailService.FROM_EMAIL
            msg['To'] = to_email
            
            part1 = MIMEText(plain_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            server = smtplib.SMTP(EmailService.SMTP_HOST, EmailService.SMTP_PORT)
            server.starttls()
            server.login(EmailService.SMTP_USER, EmailService.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

def send_reset_password_email(to_email: str, reset_token: str, frontend_url: str = None):
    """Wrapper function for send_reset_password_email"""
    return EmailService.send_reset_password_email(to_email, reset_token, frontend_url)