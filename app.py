import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import List, Dict, Any
import asyncio
from dotenv import load_dotenv

from sync_leads import sync_leads
from mail_service import MailService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up the application...")
    
    # Start the scheduler
    scheduler.start()
    
    # Schedule lead sync to run daily at 2 AM
    scheduler.add_job(
        func=sync_leads_job,
        trigger=CronTrigger(hour=2, minute=0),  # Run daily at 2 AM
        id='sync_leads_daily',
        name='Sync leads from Zoho CRM daily',
        replace_existing=True
    )
    
    logger.info("Scheduler started and jobs configured")
    
    yield
    
    # Shutdown
    logger.info("Shutting down the application...")
    scheduler.shutdown()

app = FastAPI(
    title="Zoho CRM Lead Sync Application",
    description="A web application to sync leads from Zoho CRM and send emails",
    version="1.0.0",
    lifespan=lifespan
)

# Templates and static files
templates = Jinja2Templates(directory="templates")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Initialize mail service
mail_service = MailService()

def sync_leads_job():
    """Background job to sync leads"""
    try:
        logger.info("Starting scheduled lead sync...")
        sync_leads()
        logger.info("Lead sync completed successfully")
    except Exception as e:
        logger.error(f"Error during scheduled lead sync: {e}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/sync-leads")
async def manual_sync_leads(background_tasks: BackgroundTasks):
    """Manually trigger lead synchronization"""
    try:
        background_tasks.add_task(sync_leads)
        return {"message": "Lead synchronization started in background"}
    except Exception as e:
        logger.error(f"Error starting manual sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sync-status")
async def get_sync_status():
    """Get the status of scheduled jobs"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "current_time": datetime.now().isoformat()
    }

@app.post("/send-email")
async def send_email(
    email: str,
    subject: str,
    template_name: str = "default",
    template_data: Dict[str, Any] = None
):
    """Send email using SendGrid"""
    try:
        if template_data is None:
            template_data = {}
        
        success = await mail_service.send_mail(
            to_email=email,
            subject=subject,
            template_name=template_name,
            template_data=template_data
        )
        
        if success:
            return {"message": "Email sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler.running
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
