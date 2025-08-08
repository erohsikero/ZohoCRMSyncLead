from queue import Empty
from initialize_sdk import initialize_sdk
from zcrmsdk.src.com.zoho.crm.api.record import RecordOperations
from zcrmsdk.src.com.zoho.crm.api.record import GetRecordsParam
from zcrmsdk.src.com.zoho.crm.api import ParameterMap
import psycopg2
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from mail_service import MailService

logger = logging.getLogger(__name__)

class LeadSyncService:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'kishoresuresh'),
            'password': os.getenv('DB_PASSWORD', ''),
            'dbname': os.getenv('DB_NAME', 'crm_sync'),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.sync_stats = {
            'total_leads': 0,
            'new_leads': 0,
            'updated_leads': 0,
            'errors': [],
            'new_leads_details': []  # Store new lead details for email notifications
        }
        self.mail_service = MailService()
        self.notification_emails = self._get_notification_emails()
    
    def _get_notification_emails(self) -> List[str]:
        """Get list of email addresses for notifications"""
        emails_str = os.getenv('NOTIFICATION_EMAILS', '')
        if emails_str:
            return [email.strip() for email in emails_str.split(',') if email.strip()]
        return []
    
    def create_database_table(self):
        """Create the leads table if it doesn't exist"""
        try:
            db = psycopg2.connect(**self.db_config)
            cursor = db.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id VARCHAR(255) PRIMARY KEY,
                    full_name VARCHAR(255),
                    email VARCHAR(255),
                    phone VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on email for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)
            """)
            
            db.commit()
            cursor.close()
            db.close()
            logger.info("Database table created/verified successfully")
            
        except Exception as e:
            logger.error(f"Error creating database table: {e}")
            raise
    
    def get_existing_lead_ids(self) -> set:
        """Get all existing lead IDs from the database"""
        try:
            db = psycopg2.connect(**self.db_config)
            cursor = db.cursor()
            
            cursor.execute("SELECT id FROM leads")
            existing_ids = {row[0] for row in cursor.fetchall()}
            
            cursor.close()
            db.close()
            
            return existing_ids
            
        except Exception as e:
            logger.error(f"Error fetching existing lead IDs: {e}")
            return set()
    
    def fetch_leads_from_zoho(self) -> Optional[List]:
        """Fetch leads from Zoho CRM"""
        try:
            initialize_sdk()
            module_api_name = "Leads"
            param_instance = ParameterMap()
            param_instance.add(GetRecordsParam.page, 1)
            param_instance.add(GetRecordsParam.per_page, 200)

            response = RecordOperations().get_records(module_api_name, param_instance)
            logger.info(f"Response Received from Zoho CRM: {response}")

            if response is None:
                logger.warning("No response received from Zoho CRM.")
                return None

            logger.info(f"Status Code: {response.get_status_code()}")

            if response.get_status_code() == 200:
                record_list = response.get_object().get_data()
                logger.info(f"Successfully fetched {len(record_list) if record_list else 0} leads from Zoho CRM")
                return record_list
            else:
                logger.error(f"Failed to fetch leads. Status code: {response.get_status_code()}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching leads from Zoho CRM: {e}")
            self.sync_stats['errors'].append(f"Zoho API error: {str(e)}")
            return None
    
    def save_to_local_db(self, records: List) -> None:
        """Save leads to local database"""
        if not records:
            logger.info("No records to save")
            return
        
        try:
            # Create table if not exists
            self.create_database_table()
            
            # Get existing lead IDs
            existing_ids = self.get_existing_lead_ids()
            # print(f"Existing lead IDs: {existing_ids}")
            
            db = psycopg2.connect(**self.db_config)
            cursor = db.cursor()
            
            for record in records:
                try:
                    lead_id = record.get_id()
                    # print(f"Processing lead ID: {lead_id}")
                    data = record.get_key_values()
                    full_name = data.get("Full_Name", "")
                    email = data.get("Email", "")
                    phone = data.get("Phone", "")
                    
                    # Track if this is a new or updated lead
                    is_new_lead = str(lead_id) not in existing_ids
                    # print(f"Is new lead: {is_new_lead}")
                    
                    cursor.execute("""
                        INSERT INTO leads (id, full_name, email, phone, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            full_name = EXCLUDED.full_name,
                            email = EXCLUDED.email,
                            phone = EXCLUDED.phone,
                            updated_at = EXCLUDED.updated_at
                    """, (lead_id, full_name, email, phone, datetime.now(), datetime.now()))
                    
                    if is_new_lead:
                        self.sync_stats['new_leads'] += 1
                        # Store new lead details for email notification
                        # print(f"New lead detected Data: {data}")
                        # print(f"New lead detected: {full_name} ({email} {data.get('Designation', '')})")
                        lead_details = {
                            'id': lead_id,
                            'full_name': full_name,
                            'email': email,
                            'phone': phone,
                            'title': data.get("Designation", "Engineer"),  # Get title from CRM
                            'sync_time': datetime.now().isoformat()
                        }

                        self.sync_stats['new_leads_details'].append(lead_details)
                        logger.info(f"New lead detected: {full_name} ({email})")
                    else:
                        self.sync_stats['updated_leads'] += 1
                    
                    self.sync_stats['total_leads'] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing lead {lead_id}: {str(e)}"
                    logger.error(error_msg)
                    self.sync_stats['errors'].append(error_msg)
                    continue

            db.commit()
            cursor.close()
            db.close()
            
            logger.info(f"Successfully saved {self.sync_stats['total_leads']} leads to database")
            
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(error_msg)
            self.sync_stats['errors'].append(error_msg)
            raise
    
    async def send_new_lead_notifications(self):
        """Send email notifications for new leads"""
        if not self.notification_emails:
            logger.info("No notification emails configured")
            return
        
        if not self.sync_stats['new_leads_details']:
            logger.info("No new leads to notify about")
            return
        
        logger.info(f"Sending new lead notifications to {len(self.notification_emails)} recipients")
        
        for new_lead in self.sync_stats['new_leads_details']:
            try:
                # Send individual lead notification
                for email in self.notification_emails:
                    success = await self.mail_service.send_mail(
                        to_email=email,
                        template_name='lead_notification',
                        template_data={
                            'lead_name': new_lead['full_name'],
                            'lead_email': new_lead['email'],
                            'lead_phone': new_lead['phone'],
                            'sync_time': new_lead['sync_time'],
                            'lead_id': new_lead['id']
                        }
                    )
                    
                    if success:
                        logger.info(f"New lead notification sent to {email} for lead: {new_lead['full_name']}")
                    else:
                        logger.error(f"Failed to send new lead notification to {email}")
                        
            except Exception as e:
                logger.error(f"Error sending new lead notification: {e}")
    
    async def send_cold_mail_to_new_lead(self, lead_data: Dict):
        """Send cold email to a new lead using CRM data"""
        try:
            # Extract data from CRM
            crm_fullname = lead_data.get('full_name', '')
            crm_title = lead_data.get('title', 'Engineer')  # Default to Engineer if no title
            crm_email = lead_data.get('email', '')

            print(f"Sending cold email to EMAIL : {crm_email} \n NAME : {crm_fullname} \n TITLE : {crm_title} \n ID : {lead_data.get('id', '')}")
            
            
            if not crm_email:
                logger.error(f"No email address found for lead: {crm_fullname}")
                return False
            
            # Send cold email to the lead
            success = await self.mail_service.send_mail(
                to_email=crm_email,
                template_name='cold_email',
                template_data={
                    'crm_fullname': crm_fullname,
                    'crm_title': crm_title,
                    'crm_email': crm_email
                }
            )
            
            if success:
                logger.info(f"Cold email sent successfully to {crm_email} for lead: {crm_fullname}")
                return True
            else:
                logger.error(f"Failed to send cold email to {crm_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending cold email to lead {lead_data.get('full_name', 'Unknown')}: {e}")
            return False
    
    async def send_sync_summary_email(self):
        """Send sync summary email"""
        if not self.notification_emails:
            return
        
        stats = self.get_sync_statistics()
        
        # Prepare error message for template
        error_message = ""
        if stats['errors']:
            error_message = f"<p><strong>Errors encountered:</strong></p><ul>"
            for error in stats['errors'][:5]:  # Limit to first 5 errors
                error_message += f"<li>{error}</li>"
            error_message += "</ul>"
            if len(stats['errors']) > 5:
                error_message += f"<p>... and {len(stats['errors']) - 5} more errors</p>"
        
        try:
            for email in self.notification_emails:
                success = await self.mail_service.send_mail(
                    to_email=email,
                    template_name='sync_report',
                    template_data={
                        'total_leads': str(stats['total_leads']),
                        'new_leads': str(stats['new_leads']),
                        'updated_leads': str(stats['updated_leads']),
                        'sync_time': stats['sync_time'],
                        'status': stats['status'],
                        'error_message': error_message
                    }
                )
                
                if success:
                    logger.info(f"Sync summary sent to {email}")
                else:
                    logger.error(f"Failed to send sync summary to {email}")
                    
        except Exception as e:
            logger.error(f"Error sending sync summary email: {e}")
    
    def get_sync_statistics(self) -> Dict:
        """Get synchronization statistics"""
        return {
            **self.sync_stats,
            'sync_time': datetime.now().isoformat(),
            'status': 'success' if not self.sync_stats['errors'] else 'partial_success' if self.sync_stats['total_leads'] > 0 else 'failed'
        }

def sync_leads():
    """Main function to sync leads from Zoho CRM to local database"""
    return asyncio.run(async_sync_leads())

async def async_sync_leads():
    """Async version of sync leads with email notifications"""
    sync_service = LeadSyncService()
    
    try:
        logger.info("Starting lead synchronization...")
        
        # Fetch leads from Zoho CRM
        records = sync_service.fetch_leads_from_zoho()
        
        if records:
            # Save to local database
            sync_service.save_to_local_db(records)
            
            # Send email notifications for new leads
            # await sync_service.send_new_lead_notifications()
            
            # Send cold emails to new leads
            for new_lead in sync_service.sync_stats['new_leads_details']:
                if new_lead['email'] != '':
                    print(f"Sending cold email to {new_lead['email']} ID: {new_lead['id']} TITLE: {new_lead['title']}")
                    await sync_service.send_cold_mail_to_new_lead(new_lead)
                    break
                else:
                    print(f"No email address found for lead: {new_lead['id']}")
            
            # Send sync summary email
            await sync_service.send_sync_summary_email()
            
            # Get statistics
            stats = sync_service.get_sync_statistics()
            logger.info(f"Lead sync completed: {stats}")
            
            return stats
        else:
            logger.warning("No records to synchronize")
            # Still send summary email even if no records
            await sync_service.send_sync_summary_email()
            return sync_service.get_sync_statistics()
            
    except Exception as e:
        error_msg = f"Lead synchronization failed: {str(e)}"
        logger.error(error_msg)
        sync_service.sync_stats['errors'].append(error_msg)
        
        # Send error notification
        try:
            await sync_service.send_sync_summary_email()
        except Exception as email_error:
            logger.error(f"Failed to send error notification email: {email_error}")
        
        return sync_service.get_sync_statistics()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = sync_leads()
    print(f"Leads synchronization completed: {result}")