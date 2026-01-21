"""
Background Task Scheduler - APScheduler Integration.
Manages scheduled jobs for billing, cleanup, and synchronization.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Background Task Scheduler using APScheduler."""
    
    _instance: Optional['TaskScheduler'] = None
    _scheduler: Optional[BackgroundScheduler] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialisiert den Scheduler (nur beim ersten Mal)."""
        if self._scheduler is None:
            self._scheduler = BackgroundScheduler(daemon=True)
            logger.info("TaskScheduler initialized")
    
    @property
    def scheduler(self) -> BackgroundScheduler:
        """Gibt den APScheduler Scheduler zurück."""
        return self._scheduler
    
    def start(self) -> None:
        """Startet den Background Scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("TaskScheduler started")
    
    def stop(self) -> None:
        """Stoppt den Background Scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("TaskScheduler stopped")
    
    def add_job(
        self,
        func: Callable,
        trigger_type: str = "interval",
        job_id: Optional[str] = None,
        **trigger_kwargs
    ) -> None:
        """
        Fügt einen Job zum Scheduler hinzu.
        
        Args:
            func: Callable Function
            trigger_type: "interval", "cron", "once"
            job_id: Eindeutige Job ID
            trigger_kwargs: Argument für Trigger (z.B. hours=1, minute=0)
        """
        try:
            if trigger_type == "cron":
                trigger = CronTrigger(**trigger_kwargs)
            elif trigger_type == "interval":
                trigger = IntervalTrigger(**trigger_kwargs)
            else:
                raise ValueError(f"Unknown trigger type: {trigger_type}")
            
            self._scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id or func.__name__,
                name=func.__name__,
                replace_existing=True
            )
            logger.info(f"Job added: {func.__name__} (ID: {job_id})")
        except Exception as e:
            logger.error(f"Error adding job {func.__name__}: {str(e)}")
    
    def remove_job(self, job_id: str) -> None:
        """Entfernt einen Job."""
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Job removed: {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {str(e)}")
    
    def get_jobs(self):
        """Gibt alle registrierten Jobs zurück."""
        return self._scheduler.get_jobs()
    
    def schedule_daily_billing(self) -> None:
        """
        Scheduled tägliche Abrechnung um 00:00 Uhr.
        """
        self.add_job(
            func=self._run_daily_billing,
            trigger_type="cron",
            job_id="daily_billing",
            hour=0,
            minute=0
        )
    
    def schedule_cleanup_pending(self) -> None:
        """
        Scheduled Cleanup von ausstehenden Anfragen.
        Läuft täglich um 02:00 Uhr.
        """
        self.add_job(
            func=self._run_cleanup_pending,
            trigger_type="cron",
            job_id="cleanup_pending",
            hour=2,
            minute=0
        )
    
    def schedule_notification_cleanup(self) -> None:
        """
        Scheduled Cleanup alter Notifications.
        Läuft täglich um 03:00 Uhr.
        """
        self.add_job(
            func=self._run_notification_cleanup,
            trigger_type="cron",
            job_id="notification_cleanup",
            hour=3,
            minute=0
        )
    
    def schedule_health_check(self) -> None:
        """
        Health Check alle 5 Minuten.
        """
        self.add_job(
            func=self._run_health_check,
            trigger_type="interval",
            job_id="health_check",
            minutes=5
        )
    
    def schedule_challenge_stats_update(self) -> None:
        """
        Update Challenge Stats täglich um 12:00 Uhr (Mittags).
        """
        self.add_job(
            func=self._run_challenge_stats_update,
            trigger_type="cron",
            job_id="challenge_stats_update",
            hour=12,
            minute=0
        )
    
    @staticmethod
    def _run_daily_billing() -> None:
        """Wrapper für tägliche Abrechnung."""
        try:
            from backend.services.billing_service import BillingService
            billing = BillingService()
            result = billing.daily_billing()
            logger.info(f"Daily billing completed: {result}")
        except Exception as e:
            logger.error(f"Error in daily billing job: {str(e)}")
    
    @staticmethod
    def _run_cleanup_pending() -> None:
        """Wrapper für Cleanup pending Requests."""
        try:
            from backend.tasks.cleanup_jobs import cleanup_old_pending_requests
            result = cleanup_old_pending_requests()
            logger.info(f"Cleanup pending completed: {result}")
        except Exception as e:
            logger.error(f"Error in cleanup pending job: {str(e)}")
    
    @staticmethod
    def _run_notification_cleanup() -> None:
        """Wrapper für Cleanup alter Notifications."""
        try:
            from backend.tasks.cleanup_jobs import cleanup_old_notifications
            result = cleanup_old_notifications()
            logger.info(f"Notification cleanup completed: {result}")
        except Exception as e:
            logger.error(f"Error in notification cleanup job: {str(e)}")
    
    @staticmethod
    def _run_health_check() -> None:
        """Wrapper für Health Check."""
        try:
            from backend.tasks.cleanup_jobs import health_check
            result = health_check()
            # Only log if there are issues
            if result.get("errors"):
                logger.warning(f"Health check issues: {result}")
        except Exception as e:
            logger.error(f"Error in health check job: {str(e)}")
    
    @staticmethod
    def _run_challenge_stats_update() -> None:
        """Wrapper für Challenge Stats Update."""
        try:
            from backend.tasks.cleanup_jobs import update_challenge_stats
            result = update_challenge_stats()
            logger.info(f"Challenge stats update completed: {result}")
        except Exception as e:
            logger.error(f"Error in challenge stats update job: {str(e)}")


# Global scheduler instance
_scheduler = TaskScheduler()


def get_scheduler() -> TaskScheduler:
    """Gibt globale Scheduler Instanz zurück."""
    return _scheduler


def init_scheduler(app=None) -> TaskScheduler:
    """
    Initialisiert und startet den Scheduler.
    
    Args:
        app: Flask App (optional, für Kontext)
    
    Returns:
        TaskScheduler Instanz
    """
    scheduler = get_scheduler()
    
    # Schedule alle Jobs
    scheduler.schedule_daily_billing()
    scheduler.schedule_cleanup_pending()
    scheduler.schedule_notification_cleanup()
    scheduler.schedule_challenge_stats_update()
    scheduler.schedule_health_check()
    
    # Starte Scheduler
    scheduler.start()
    
    logger.info("Scheduler initialized with all jobs")
    return scheduler
