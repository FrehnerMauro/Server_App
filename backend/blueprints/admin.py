from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.services.stats import update_stats_for_challenge_today
from backend.common.store import state

bp = Blueprint("admin", __name__)

@bp.post("/admin/run-daily-stats")
@auth_required
def run_daily_stats():
    tz = int(request.args.get("tzOffsetMinutes", request.json.get("tzOffsetMinutes", 0) if request.is_json else 0))
    st = state()
    for cid in list(st["challenges"].keys()):
        update_stats_for_challenge_today(int(cid), tz)
    return jsonify({"ok": True})

@bp.post("/admin/update-daily-stats")
@auth_required
def update_daily_stats():
    return run_daily_stats()

@bp.post("/admin/challenges/<int:cid>/run-daily-stats")
@auth_required
def run_daily_one(cid: int):
    tz = int(request.args.get("tzOffsetMinutes", request.json.get("tzOffsetMinutes", 0) if request.is_json else 0))
    update_stats_for_challenge_today(cid, tz)
    return jsonify({"ok": True})

@bp.post("/admin/challenges/<int:cid>/update-daily-stats")
@auth_required
def update_daily_one(cid: int):
    return run_daily_one(cid)