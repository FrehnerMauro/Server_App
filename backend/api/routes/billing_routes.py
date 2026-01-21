"""
Billing API Routes - Admin endpoints for billing management.
"""
from flask import Blueprint, request, jsonify

from backend.core.logging import get_logger
from backend.services.billing_service import BillingService
from backend.api.decorators import require_auth, require_admin

logger = get_logger(__name__)

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")
billing_service = BillingService()


@billing_bp.route("/credits/<int:user_id>", methods=["GET"])
@require_auth
def get_user_credits(user_id: int):
    """
    Get user credits and billing status.
    
    Args:
        user_id: User ID
    
    Returns:
        JSON mit credits, billing_status, subscription_tier
    """
    try:
        # Check if user is viewing own credits or is admin
        current_user = request.user
        if current_user["id"] != user_id and not current_user.get("is_admin"):
            return jsonify({"error": "Unauthorized"}), 403
        
        credits_info = billing_service.get_user_credits(user_id)
        
        if not credits_info:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(credits_info), 200
    
    except Exception as e:
        logger.error(f"Error getting user credits: {str(e)}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/credits/<int:user_id>/add", methods=["POST"])
@require_admin
def add_credits(user_id: int):
    """
    Add credits to user account (ADMIN ONLY).
    
    Args:
        user_id: User ID
        Body: {"amount": <float>, "description": <string>}
    
    Returns:
        Updated credit info
    """
    try:
        data = request.get_json()
        amount = data.get("amount")
        description = data.get("description", "Admin credit adjustment")
        
        if amount is None:
            return jsonify({"error": "Missing 'amount' field"}), 400
        
        result = billing_service.add_credits(user_id, amount, description)
        
        if "error" in result:
            return jsonify(result), 400
        
        logger.info(f"Admin added {amount} credits to user {user_id}")
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error adding credits: {str(e)}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/credits/<int:user_id>/deduct", methods=["POST"])
@require_admin
def deduct_credits(user_id: int):
    """
    Deduct credits for event (ADMIN ONLY).
    
    Args:
        user_id: User ID
        Body: {"event_type": <string>}
    
    Returns:
        Updated credit info
    """
    try:
        data = request.get_json()
        event_type = data.get("event_type")
        
        if not event_type:
            return jsonify({"error": "Missing 'event_type' field"}), 400
        
        result = billing_service.deduct_credits(user_id, event_type)
        
        if "error" in result:
            return jsonify(result), 400
        
        logger.info(f"Deducted credits for {event_type} from user {user_id}")
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error deducting credits: {str(e)}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/history/<int:user_id>", methods=["GET"])
@require_auth
def get_billing_history(user_id: int):
    """
    Get billing history for user.
    
    Args:
        user_id: User ID
        Query: limit=<int> (default: 50)
    
    Returns:
        List of billing events
    """
    try:
        # Check if user is viewing own history or is admin
        current_user = request.user
        if current_user["id"] != user_id and not current_user.get("is_admin"):
            return jsonify({"error": "Unauthorized"}), 403
        
        limit = request.args.get("limit", 50, type=int)
        
        history = billing_service.get_billing_history(user_id, limit)
        
        return jsonify({
            "user_id": user_id,
            "events": history
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting billing history: {str(e)}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/admin/pricing", methods=["GET"])
@require_admin
def get_pricing_config():
    """
    Get pricing configuration (ADMIN ONLY).
    
    Returns:
        Current pricing configuration
    """
    try:
        return jsonify({
            "pricing": billing_service.PRICING,
            "thresholds": {
                "suspend": billing_service.SUSPEND_THRESHOLD,
                "warning": billing_service.WARNING_THRESHOLD
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting pricing: {str(e)}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/admin/billing-cycle", methods=["POST"])
@require_admin
def trigger_billing_cycle():
    """
    Manually trigger daily billing cycle (ADMIN ONLY).
    
    Returns:
        Billing cycle statistics
    """
    try:
        result = billing_service.daily_billing()
        
        logger.info(f"Manual billing cycle triggered: {result}")
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error triggering billing cycle: {str(e)}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/admin/scheduler/jobs", methods=["GET"])
@require_admin
def get_scheduler_jobs():
    """
    Get all scheduled jobs info (ADMIN ONLY).
    
    Returns:
        List of active jobs
    """
    try:
        from backend.tasks import get_scheduler
        scheduler = get_scheduler()
        
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time),
                "trigger": str(job.trigger)
            })
        
        return jsonify({
            "scheduler_running": scheduler.scheduler.running,
            "jobs": jobs
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting scheduler jobs: {str(e)}")
        return jsonify({"error": str(e)}), 500
