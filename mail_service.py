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
    
    def _load_cold_email_template(self) -> str:
        """Load the cold email HTML template from file"""
        try:
            template_path = os.path.join('templates', 'coldmain.html')
            with open(template_path, 'r', encoding='utf-8') as file:
                template_content = file.read()
            
            # Use a more robust approach to replace template placeholders
            # First, escape any existing format braces that are not template placeholders
            import re
            
            # Replace template placeholders with format placeholders
            template_content = re.sub(r'\{\{\s*crm_fullname\s*\}\}', '{crm_fullname}', template_content)
            template_content = re.sub(r'\{\{\s*crm_title\s*\}\}', '{crm_title}', template_content)
            template_content = re.sub(r'\{\{\s*crm_email\s*\}\}', '{crm_email}', template_content)
            
            return template_content
            
        except FileNotFoundError:
            logger.error(f"Cold email template file not found: {template_path}")
            return self._get_fallback_cold_email_template()
        except Exception as e:
            logger.error(f"Error loading cold email template: {e}")
            return self._get_fallback_cold_email_template()
    
    def _get_fallback_cold_email_template(self) -> str:
        """Return a fallback cold email template if file loading fails"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Cold Email</title>
        </head>
        <body>
            <h2>Re: Your Post About Hiring Engineers</h2>
            <p>Hi <strong>{crm_fullname}</strong>,</p>
            <p>Hope you're having a productive week!</p>
            <p>We've all been there – drowning in resumes for key roles like <strong>{crm_title}</strong>, trying to find that perfect fit.</p>
            <p>What if there was a way to cut through that clutter quickly and effectively? That's exactly what <strong>Referrals AI</strong> is designed to do.</p>
            <p>Would you be open to a brief chat next week?</p>
            <p>Best,<br>Jha</p>
        </body>
        </html>
        '''
    
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
            },
            'cold_email': {
                'subject': 'Re: Your Post About Hiring Engineers',
                'html': self._load_cold_email_template(),
                'plain': '''
                Re: Your Post About Hiring Engineers

                Hi {crm_fullname},

                Hope you're having a productive week!

                We've all been there – drowning in resumes for key roles like {crm_title}, trying to find that perfect fit. It's a massive time sink, and sometimes the best candidates slip through the cracks.

                What if there was a way to cut through that clutter quickly and effectively? That's exactly what Referrals AI is designed to do. It's an AI-powered tool that pre-vets resumes, turning that overwhelming pile into a manageable list of potential candidates with smart scoring and analysis.

                Benefits:
                - Significantly less time spent on initial resume screening
                - A clearer picture of candidate fit before you even pick up the phone
                - Faster identification of top talent for your {crm_title} openings

                I'd love to show you firsthand how Referrals AI can integrate into your current process and deliver these results.

                Would you be open to a brief chat next week? I can give you a quick overview and explore how it can specifically address your hiring challenges for roles like {crm_title}.

                Thanks for your time, and I look forward to the possibility of connecting.

                Best,
                Jha
                '''
            }
        }
        
        template = templates.get(template_name, templates['default'])
        
        try:
            subject = template['subject'].format(**template_data)
            
            # Handle cold_email template differently to avoid CSS formatting issues
            if template_name == 'cold_email':
                html_content = template['html']
                # Manually replace placeholders in HTML content
                html_content = html_content.replace('{crm_fullname}', template_data.get('crm_fullname', ''))
                html_content = html_content.replace('{crm_title}', template_data.get('crm_title', ''))
                html_content = html_content.replace('{crm_email}', template_data.get('crm_email', ''))
            else:
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

            # print(f"\n\n\nSending email to {to_email} with subject {subject} and content {html_content}\n\n\n")
            
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
