from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Message
from models import db, JobApplication, User
from datetime import datetime, timedelta, timezone
import os
import logging

logger = logging.getLogger(__name__)

def check_and_send_reminders(app, mail):
    """
    Checks for job applications that need follow-up and sends email reminders.
    Runs within the Flask application context.
    """
    with app.app_context():
        logger.info("Running scheduled job: check_and_send_reminders")
        
        # Threshold: 7 days ago
        threshold_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Find applications that are 'Applied' or 'Interviewing'
        # And haven't been updated/reminded in the last 7 days
        stale_apps = JobApplication.query.filter(
            JobApplication.status.in_(['Applied', 'Interviewing']),
            JobApplication.applied_at <= threshold_date
        ).all()

        reminders_sent = 0
        
        for app_record in stale_apps:
            # Check if we already reminded them recently
            if app_record.last_reminded_at and app_record.last_reminded_at > threshold_date:
                continue

            user = User.query.get(app_record.user_id)
            if not user or not user.email:
                continue

            # Send Email
            try:
                msg = Message(
                    subject=f"Action Required: Follow up on your application at {app_record.company}",
                    recipients=[user.email],
                    body=f"Hi {user.name},\n\n"
                         f"It has been over 7 days since your last update for the '{app_record.role}' role at {app_record.company}.\n\n"
                         f"Current Status: {app_record.status}\n\n"
                         f"Consider sending a polite follow-up email to the recruiter or hiring manager to reiterate your interest and check on the status of your application.\n\n"
                         f"Best of luck!\n"
                         f"Your CVNova AI Companion"
                )
                mail.send(msg)
                
                # Update last reminded timestamp
                app_record.last_reminded_at = datetime.now(timezone.utc)
                db.session.commit()
                
                reminders_sent += 1
                logger.info(f"Sent reminder to {user.email} for {app_record.company}")
                
            except Exception as e:
                logger.error(f"Failed to send email to {user.email}: {str(e)}")
                db.session.rollback()

        logger.info(f"Finished check_and_send_reminders. Sent {reminders_sent} emails.")


def init_scheduler(app, mail):
    """Initializes and starts the background scheduler."""
    scheduler = BackgroundScheduler(daemon=True)
    
    # Schedule the job to run every day at 9:00 AM
    # For testing, we also allow the job to be triggered manually.
    scheduler.add_job(func=check_and_send_reminders, args=[app, mail], trigger="cron", hour=9, minute=0)
    
    scheduler.start()
    logger.info("APScheduler started successfully.")
    return scheduler
