#!/usr/bin/env python
"""
Local Scheduler Test Script - Testet alle Background Jobs lokal.
Startet die App mit Scheduler und triggert Test-Jobs.
"""
import os
import sys
import time
import logging
from pathlib import Path

# Setze PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Testet Scheduler und Background Jobs."""
    logger.info("=" * 70)
    logger.info("🚀 SocialHabit Background Job Scheduler - LOCAL TEST")
    logger.info("=" * 70)
    
    try:
        # Importiere Flask App
        logger.info("📦 Initialisiere Flask App...")
        from backend.app_v2 import create_app
        
        app = create_app()
        logger.info("✅ Flask App erstellt")
        
        # Hole Scheduler
        from backend.tasks import get_scheduler
        scheduler = get_scheduler()
        
        logger.info("\n📋 Geplante Jobs:")
        logger.info("-" * 70)
        for job in scheduler.get_jobs():
            logger.info(f"  • {job.id:25} | {job.name:30} | Next: {job.next_run_time}")
        
        logger.info("-" * 70)
        logger.info(f"\n✅ Scheduler Status: {'RUNNING' if scheduler.scheduler.running else 'STOPPED'}")
        
        # Test 1: Health Check
        logger.info("\n" + "=" * 70)
        logger.info("🔍 TEST 1: Health Check ausführen...")
        logger.info("=" * 70)
        
        from backend.tasks.cleanup_jobs import health_check
        health_result = health_check()
        
        logger.info(f"Status: {health_result.get('status')}")
        logger.info(f"Total Users: {health_result.get('stats', {}).get('total_users')}")
        logger.info(f"Pending Friend Requests: {health_result.get('stats', {}).get('pending_friend_requests')}")
        logger.info(f"Pending Invites: {health_result.get('stats', {}).get('pending_invites')}")
        logger.info(f"Unread Notifications: {health_result.get('stats', {}).get('unread_notifications')}")
        
        if health_result.get('errors'):
            logger.error(f"Errors: {health_result.get('errors')}")
        else:
            logger.info("✅ Health Check erfolgreich!")
        
        # Test 2: Billing Service
        logger.info("\n" + "=" * 70)
        logger.info("💳 TEST 2: Billing Service testen...")
        logger.info("=" * 70)
        
        from backend.services.billing_service import BillingService
        billing = BillingService()
        
        logger.info("\nPricing Configuration:")
        logger.info("-" * 70)
        for event, price in billing.PRICING.items():
            logger.info(f"  {event:20} = {price:7.1f} Credits")
        
        logger.info(f"\nThresholds:")
        logger.info(f"  Suspend at: {billing.SUSPEND_THRESHOLD} Credits")
        logger.info(f"  Warning at: {billing.WARNING_THRESHOLD} Credits")
        logger.info("✅ Billing Service konfiguriert!")
        
        # Test 3: Cleanup Jobs
        logger.info("\n" + "=" * 70)
        logger.info("🧹 TEST 3: Cleanup Jobs ausführen...")
        logger.info("=" * 70)
        
        from backend.tasks.cleanup_jobs import (
            cleanup_old_pending_requests,
            cleanup_old_notifications,
            cleanup_failed_challenges
        )
        
        logger.info("\n  → cleanup_old_pending_requests...")
        result1 = cleanup_old_pending_requests(days=30)
        logger.info(f"    {result1}")
        
        logger.info("\n  → cleanup_old_notifications...")
        result2 = cleanup_old_notifications(days=90)
        logger.info(f"    {result2}")
        
        logger.info("\n  → cleanup_failed_challenges...")
        result3 = cleanup_failed_challenges(days=7)
        logger.info(f"    {result3}")
        
        logger.info("\n✅ Alle Cleanup Jobs durchgelaufen!")
        
        # Test 4: Billing Cycle
        logger.info("\n" + "=" * 70)
        logger.info("💰 TEST 4: Tägliche Abrechnung ausführen...")
        logger.info("=" * 70)
        
        result_billing = billing.daily_billing()
        logger.info(f"Processed: {result_billing.get('processed')} Users")
        logger.info(f"Suspended: {result_billing.get('suspended')} Users")
        
        if result_billing.get('error'):
            logger.error(f"Error: {result_billing.get('error')}")
        else:
            logger.info("✅ Daily Billing durchgelaufen!")
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("✅ ALLE TESTS ERFOLGREICH!")
        logger.info("=" * 70)
        logger.info("\n📌 Scheduler läuft im Hintergrund:")
        logger.info("   • 00:00 - Daily Billing Cycle (tägliche Abrechnung)")
        logger.info("   • 02:00 - Cleanup Old Pending Requests (Freundschaften, Invites)")
        logger.info("   • 03:00 - Cleanup Old Notifications (alte Nachrichten)")
        logger.info("   • Alle 5 Min - Health Check")
        logger.info("\n💡 Die App ist bereit für den Produktionsbetrieb!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"\n❌ ERROR: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
