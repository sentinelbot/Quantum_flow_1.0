# notification/email_notifier.py
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

logger = logging.getLogger(__name__)

class EmailNotifier:
    """
    Email notification system
    """
    def __init__(self, enabled: bool = False, smtp_server: str = '', smtp_port: int = 587,
               smtp_username: str = '', smtp_password: str = '', from_email: str = ''):
        self.enabled = enabled
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        
        logger.info("Email notifier initialized")
        
    def send_email(self, to_email: str, subject: str, message: str, cc_emails: List[str] = None) -> bool:
        """
        Send email
        
        Args:
            to_email: Recipient email
            subject: Email subject
            message: Email message
            cc_emails: CC recipients
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            logger.info(f"Email notification skipped (disabled): {subject}")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
                
            # Add message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            # Send email
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
                
            server.sendmail(self.from_email, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Email notification sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
            
    def send_html_email(self, to_email: str, subject: str, html_message: str, cc_emails: List[str] = None) -> bool:
        """
        Send HTML email
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_message: HTML email message
            cc_emails: CC recipients
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            logger.info(f"HTML email notification skipped (disabled): {subject}")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
                
            # Add HTML message body
            msg.attach(MIMEText(html_message, 'html'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            # Send email
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
                
            server.sendmail(self.from_email, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"HTML email notification sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending HTML email: {str(e)}")
            return False
            
    def send_test_email(self, to_email: str) -> bool:
        """
        Send test email
        
        Args:
            to_email: Recipient email
            
        Returns:
            bool: True if successful, False otherwise
        """
        subject = "QuantumFlow Trading Bot - Test Email"
        message = (
            "This is a test email from QuantumFlow Trading Bot.\n\n"
            "If you received this email, your email notification settings are working correctly.\n\n"
            "Best regards,\n"
            "QuantumFlow Trading Bot"
        )
        
        return self.send_email(to_email, subject, message)