import os
import logging
from typing import Dict, Any, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent
import json

logger = logging.getLogger(__name__)

class MailService:
    """
    Mail service class for sending emails using SendGrid
    """
    
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY environment variable not set")
            self.sendgrid_client = None
        else:
            self.sendgrid_client = SendGridAPIClient(api_key=self.api_key)
        
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@example.com')
        self.from_name = os.getenv('FROM_NAME', 'CRM Sync Service')
    
    def get_email_template(self, template_name: str, template_data: Dict[str, Any] = None) -> tuple:
        """
        Get email template content based on template name
        Returns: (subject, html_content, plain_content)
        """
        if template_data is None:
            template_data = {}
        
        templates = {
            'default': {
                'subject': 'Default Email from CRM Sync Service',
                'html': '''
                <html>
                <body>
                    <h2>Hello from CRM Sync Service!</h2>
                    <p>This is a default email template.</p>
                    <p>Message: {message}</p>
                    <p>Best regards,<br>CRM Sync Team</p>
                </body>
                </html>
                ''',
                'plain': '''
                Hello from CRM Sync Service!
                
                This is a default email template.
                Message: {message}
                
                Best regards,
                CRM Sync Team
                '''
            },
            'lead_notification': {
                'subject': 'New Lead Notification - {lead_name}',
                'html': '''
                <html>
                <body>
                    <h2>New Lead Added</h2>
                    <p>A new lead has been synchronized from Zoho CRM:</p>
                    <ul>
                        <li><strong>Name:</strong> {lead_name}</li>
                        <li><strong>Email:</strong> {lead_email}</li>
                        <li><strong>Phone:</strong> {lead_phone}</li>
                        <li><strong>Sync Time:</strong> {sync_time}</li>
                    </ul>
                    <p>Please follow up with this lead as soon as possible.</p>
                    <p>Best regards,<br>CRM Sync Team</p>
                </body>
                </html>
                ''',
                'plain': '''
                New Lead Added
                
                A new lead has been synchronized from Zoho CRM:
                
                Name: {lead_name}
                Email: {lead_email}
                Phone: {lead_phone}
                Sync Time: {sync_time}
                
                Please follow up with this lead as soon as possible.
                
                Best regards,
                CRM Sync Team
                '''
            },
            'sync_report': {
                'subject': 'Daily Lead Sync Report',
                'html': '''
                <html>
                <body>
                    <h2>Daily Lead Sync Report</h2>
                    <p>The daily lead synchronization has been completed.</p>
                    <ul>
                        <li><strong>Total Leads Processed:</strong> {total_leads}</li>
                        <li><strong>New Leads Added:</strong> {new_leads}</li>
                        <li><strong>Updated Leads:</strong> {updated_leads}</li>
                        <li><strong>Sync Time:</strong> {sync_time}</li>
                        <li><strong>Status:</strong> {status}</li>
                    </ul>
                    {error_message}
                    <p>Best regards,<br>CRM Sync Team</p>
                </body>
                </html>
                ''',
                'plain': '''
                Daily Lead Sync Report
                
                The daily lead synchronization has been completed.
                
                Total Leads Processed: {total_leads}
                New Leads Added: {new_leads}
                Updated Leads: {updated_leads}
                Sync Time: {sync_time}
                Status: {status}
                
                {error_message}
                
                Best regards,
                CRM Sync Team
                '''
            }
        }
        
        template = templates.get(template_name, templates['default'])
        
        try:
            subject = template['subject'].format(**template_data)
            html_content = template['html'].format(**template_data)
            plain_content = template['plain'].format(**template_data)
            
            return subject, html_content, plain_content
        except KeyError as e:
            logger.error(f"Missing template data key: {e}")
            # Fallback to default template
            return self.get_email_template('default', {'message': f'Template error: missing key {e}'})
    
    async def send_mail(
        self, 
        to_email: str, 
        subject: Optional[str] = None,
        template_name: str = 'default', 
        template_data: Dict[str, Any] = None,
        html_content: Optional[str] = None,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Send email using SendGrid
        
        Args:
            to_email: Recipient email address
            subject: Email subject (optional if using template)
            template_name: Name of the email template
            template_data: Data to populate the template
            html_content: Custom HTML content (overrides template)
            plain_content: Custom plain text content (overrides template)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        
        if not self.sendgrid_client:
            logger.error("SendGrid client not initialized. Check SENDGRID_API_KEY environment variable.")
            return False
        
        try:
            # Get template content if custom content not provided
            if not html_content or not plain_content or not subject:
                template_subject, template_html, template_plain = self.get_email_template(template_name, template_data)
                
                subject = subject or template_subject
                html_content = html_content or template_html
                plain_content = plain_content or template_plain
            
            # Create the email
            message = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(plain_content),
                html_content=HtmlContent(html_content)
            )
            
            # Send the email
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully to {to_email}. Status: {response.status_code}")
                return True
            else:
                logger.error(f"Failed to send email to {to_email}. Status: {response.status_code}, Body: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    async def send_bulk_mail(
        self, 
        recipients: list, 
        template_name: str = 'default', 
        template_data: Dict[str, Any] = None
    ) -> Dict[str, int]:
        """
        Send email to multiple recipients
        
        Args:
            recipients: List of email addresses
            template_name: Name of the email template
            template_data: Data to populate the template
            
        Returns:
            dict: Summary of sent/failed emails
        """
        
        results = {'sent': 0, 'failed': 0}
        
        for email in recipients:
            success = await self.send_mail(
                to_email=email,
                template_name=template_name,
                template_data=template_data
            )
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"Bulk email results: {results}")
        return results
