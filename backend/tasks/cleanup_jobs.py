"""
Cleanup Jobs - Automatic cleanup of pending/expired requests and notifications.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from backend.core.logging import get_logger
from backend.common.store import Database

logger = get_logger(__name__)


def cleanup_old_pending_requests(days: int = 30) -> Dict[str, Any]:
    """
    Automatically rejects friend requests and challenge invites older than X days.
    
    Args:
        days: Days before marking as expired (default: 30)
    
    Returns:
        Statistics of cleaned up requests
    """
    try:
        db = Database()
        cutoff_time = int((time.time() - (days * 86400)) * 1000)  # Convert to milliseconds
        now = int(time.time() * 1000)
        
        logger.info(f"Starting cleanup of pending requests older than {days} days...")
        
        con, cur = db.begin_transaction()
        
        # Auto-reject pending friend requests
        cur.execute(
            """SELECT id, user_id, friend_id FROM user_friends 
               WHERE status = %s AND created_at < %s""",
            ("pending", cutoff_time)
        )
        friend_reqs = cur.fetchall()
        
        rejected_friends = 0
        for req in friend_reqs:
            req_id, user_id, friend_id = req[0], req[1], req[2]
            cur.execute(
                """UPDATE user_friends SET status = %s, updated_at = %s WHERE id = %s""",
                ("declined", now, req_id)
            )
            rejected_friends += 1
            logger.debug(f"Auto-rejected friend request {req_id}")
        
        # Auto-decline pending challenge invites
        cur.execute(
            """SELECT id, user_id, challenge_id FROM challenge_invites 
               WHERE status = %s AND created_at < %s""",
            ("pending", cutoff_time)
        )
        challenge_invites = cur.fetchall()
        
        declined_invites = 0
        for invite in challenge_invites:
            invite_id, user_id, challenge_id = invite[0], invite[1], invite[2]
            cur.execute(
                """UPDATE challenge_invites SET status = %s, updated_at = %s WHERE id = %s""",
                ("declined", now, invite_id)
            )
            declined_invites += 1
            logger.debug(f"Auto-declined challenge invite {invite_id}")
        
        db.commit(con)
        
        result = {
            "auto_rejected_friends": rejected_friends,
            "auto_declined_invites": declined_invites,
            "total_cleaned": rejected_friends + declined_invites,
            "timestamp": now
        }
        
        logger.info(f"Cleanup completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error in cleanup_old_pending_requests: {str(e)}")
        return {"error": str(e)}


def cleanup_old_notifications(days: int = 90) -> Dict[str, Any]:
    """
    Deletes old read notifications after X days.
    
    Args:
        days: Days before deletion (default: 90)
    
    Returns:
        Statistics of deleted notifications
    """
    try:
        db = Database()
        cutoff_time = int((time.time() - (days * 86400)) * 1000)
        now = int(time.time() * 1000)
        
        logger.info(f"Starting cleanup of notifications older than {days} days...")
        
        con, cur = db.begin_transaction()
        
        # Delete old read notifications
        cur.execute(
            """SELECT COUNT(*) FROM notifications 
               WHERE read = 1 AND created_at < %s""",
            (cutoff_time,)
        )
        count_result = cur.fetchone()
        old_notifications = count_result[0] if count_result else 0
        
        if old_notifications > 0:
            cur.execute(
                """DELETE FROM notifications 
                   WHERE read = 1 AND created_at < %s""",
                (cutoff_time,)
            )
            logger.info(f"Deleted {old_notifications} old read notifications")
        
        db.commit(con)
        
        result = {
            "deleted_notifications": old_notifications,
            "timestamp": now
        }
        
        logger.info(f"Notification cleanup completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications: {str(e)}")
        return {"error": str(e)}


def cleanup_failed_challenges(days: int = 7) -> Dict[str, Any]:
    """
    Marks challenges as failed if user hasn't confirmed in X days.
    
    Args:
        days: Days of inactivity before marking as failed (default: 7)
    
    Returns:
        Statistics of failed challenges
    """
    try:
        db = Database()
        cutoff_time = int((time.time() - (days * 86400)) * 1000)
        now = int(time.time() * 1000)
        
        logger.info(f"Starting cleanup of failed challenges (no update for {days} days)...")
        
        con, cur = db.begin_transaction()
        
        # Find challenge_stats with no updates
        cur.execute(
            """SELECT cs.id, cs.challenge_id, cs.user_id FROM challenge_stats cs
               JOIN challenges c ON cs.challenge_id = c.id
               WHERE c.status = %s AND cs.updated_at < %s AND cs.blocked = %s""",
            ("active", cutoff_time, "run")
        )
        failed_stats = cur.fetchall()
        
        failed_count = 0
        for stat in failed_stats:
            stat_id, challenge_id, user_id = stat[0], stat[1], stat[2]
            
            # Update challenge_stats to mark as blocked/failed
            cur.execute(
                """UPDATE challenge_stats SET blocked = %s, updated_at = %s WHERE id = %s""",
                ("failed", now, stat_id)
            )
            failed_count += 1
            logger.debug(f"Marked challenge {challenge_id} for user {user_id} as failed")
        
        db.commit(con)
        
        result = {
            "marked_failed": failed_count,
            "timestamp": now
        }
        
        logger.info(f"Failed challenges cleanup completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error in cleanup_failed_challenges: {str(e)}")
        return {"error": str(e)}


def health_check() -> Dict[str, Any]:
    """
    Health check - verifies database connectivity and counts pending items.
    
    Returns:
        Health status and statistics
    """
    try:
        db = Database()
        con, cur = db.begin_transaction()
        
        # Test database connection
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        
        # Count pending items
        cur.execute(
            "SELECT COUNT(*) FROM user_friends WHERE status = %s",
            ("pending",)
        )
        pending_friends = cur.fetchone()[0]
        
        cur.execute(
            "SELECT COUNT(*) FROM challenge_invites WHERE status = %s",
            ("pending",)
        )
        pending_invites = cur.fetchone()[0]
        
        cur.execute(
            "SELECT COUNT(*) FROM notifications WHERE read = %s",
            (0,)
        )
        unread_notifications = cur.fetchone()[0]
        
        db.commit(con)
        
        return {
            "status": "healthy",
            "timestamp": int(time.time() * 1000),
            "stats": {
                "total_users": user_count,
                "pending_friend_requests": pending_friends,
                "pending_invites": pending_invites,
                "unread_notifications": unread_notifications
            },
            "errors": []
        }
    
    except Exception as e:
        logger.error(f"Error in health_check: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": int(time.time() * 1000),
            "errors": [str(e)]
        }


def update_challenge_stats() -> Dict[str, Any]:
    """
    Update existing challenge stats from database.
    Simply refreshes and syncs already existing statistics.
    
    Returns:
        Statistics of updated challenges
    """
    try:
        db = Database()
        now = int(time.time() * 1000)
        
        logger.info("Starting challenge stats update job...")
        
        con, cur = db.begin_transaction()
        
        # Update all challenge stats - simply refresh timestamps and sync
        cur.execute(
            """UPDATE challenge_stats SET updated_at = %s""",
            (now,)
        )
        updated_count = cur.rowcount
        
        # Also refresh challenge last_updated
        cur.execute(
            """UPDATE challenges SET updated_at = %s WHERE status IN (%s, %s)""",
            (now, "active", "completed")
        )
        challenge_count = cur.rowcount
        
        db.commit(con)
        
        logger.info(f"Challenge stats update completed: {updated_count} stats, {challenge_count} challenges refreshed")
        
        return {
            "status": "success",
            "stats_updated": updated_count,
            "challenges_updated": challenge_count,
            "timestamp": now
        }
        
    except Exception as e:
        logger.error(f"Error in update_challenge_stats: {str(e)}")
        return {
            "status": "error",
            "total_updated": 0,
            "error": str(e)
        }
