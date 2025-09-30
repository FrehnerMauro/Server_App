# backend/services/stats.py
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, Any, List
from backend.common.store import state, save, now_ms

# ------------------ kleine Helfer ------------------
# --- Backwards-compatible alias for older imports/routes ---
def update_stats_for_challenge_today(cid: int, tz_offset_minutes: int = 0):
    """Compat wrapper: keeps old import path working."""
    return challenge_update_stats(cid, tz_offset_minutes)
def _to_local_date_from_ts(ts: int, tz_offset_min: int) -> datetime.date:
    """Akzeptiert Sekunden oder Millisekunden."""
    if ts > 10**12:  # ms
        ts = ts // 1000
    tz = timezone(timedelta(minutes=tz_offset_min))
    return datetime.fromtimestamp(int(ts), tz).date()

def _is_due_day(d: datetime.date, start_date: datetime.date, end_date: datetime.date, faellige: List[int]) -> bool:
    return start_date <= d <= end_date and (d.weekday() in (faellige or []))

def _next_calendar_day(d: datetime.date) -> datetime.date:
    return d + timedelta(days=1)

# ------------------ Kernfunktion ------------------
# backend/services/stats.py

def challenge_update_stats(cid: int, tz_offset_minutes: int = 0) -> Dict[str, Any]:
    st = state()
    ch = st.get("challenges", {}).get(str(cid))
    if not ch:
        return {"error": "challenge_not_found", "challengeId": cid}

    start_at = ch.get("startAt")
    dauer = ch.get("dauerTage") or ch.get("days")
    faellige = ch.get("faelligeWochentage") or []
    erlaubte_fails = ch.get("erlaubteFailsTage")

    if not start_at:
        return {"error": "startAt_missing", "challengeId": cid}
    if not isinstance(faellige, list):
        return {"error": "faelligeWochentage_missing", "challengeId": cid}

    tz = timezone(timedelta(minutes=tz_offset_minutes))
    today = datetime.now(tz).date()
    start_date = _to_local_date_from_ts(int(start_at), tz_offset_minutes)
    end_date = start_date + timedelta(days=int(dauer) - 1) if dauer else today

    members = [m["userId"] for m in st.get("challenge_members", []) if m.get("challengeId") == cid]

    logs = st.get("challenge_logs", {}).get(str(cid), [])
    confirms_today = defaultdict(bool)
    for l in logs:
        uid = l.get("userId") or l.get("user_id")
        ts = l.get("timestamp")
        if uid is None or ts is None:
            continue
        if _to_local_date_from_ts(int(ts), tz_offset_minutes) == today:
            confirms_today[int(uid)] = True

    stats_all = st.setdefault("challenge_stats", {}).setdefault(str(cid), {})
    per_user = stats_all.setdefault("perUser", {})

    updated_users: Dict[str, Any] = {}

    for uid in members:
        key = str(uid)
        pu = per_user.get(key) or {
            "conf_count": 0,
            "fail_count": 0,
            "streak": 0,
            "neg_streak": 0,
            "blocked": "none",       # "none" | "gesperrt" | "completed"
            "state": "pending"       # "pending" | "nicht_pending"
        }

        blocked = str(pu.get("blocked", "none"))

        # Heutigen Zustand bestimmen
        if _is_due_day(today, start_date, end_date, faellige):
            today_state = "erledigt" if confirms_today.get(uid) else "pending"
        else:
            today_state = "nicht_pending"

        # Zähler anpassen, falls nicht bereits finaler Blockade/Abschluss
        conf_count = int(pu.get("conf_count", 0))
        fail_count = int(pu.get("fail_count", 0))
        streak     = int(pu.get("streak", 0))
        neg_streak = int(pu.get("neg_streak", 0))

        if blocked not in ("completed", "gesperrt"):
            if today_state == "pending":
                fail_count += 1
                streak = 0
                neg_streak += 1
            elif today_state == "erledigt":
                conf_count += 1
                streak += 1
                neg_streak = 0
            # "nicht_pending" -> keine Änderung

            # Blockierungs-/Abschlusslogik
            if erlaubte_fails is not None and fail_count >= int(erlaubte_fails):
                blocked = "gesperrt"
            if dauer is not None and conf_count >= int(dauer):
                blocked = "completed"

        # Mapping für das neue Today-Objekt (genau wie dein Swift-Modell)
        if blocked == "gesperrt":
            status_label = "gesperrt"
        elif blocked == "completed":
            status_label = "Abgeschlossen"
        else:
            status_label = "offen"

        today_obj = {
            "status": status_label,                  # "offen" | "gesperrt" | "Abgeschlossen"
            "pending": (today_state == "pending"),   # true/false
            "erledigt": (today_state == "erledigt")  # true/false
        }

        # State für den nächsten Tag (nur Info/Zukunft)
        tomorrow = _next_calendar_day(today)
        next_state = "pending" if _is_due_day(tomorrow, start_date, end_date, faellige) else "nicht_pending"

        # Speichern
        pu.update({
            "conf_count": conf_count,
            "fail_count": fail_count,
            "streak":     streak,
            "neg_streak": neg_streak,
            "blocked":    blocked,
            "state":      next_state,
            "lastComputedAt": now_ms(),
            # optional: für Debug/Transparenz kannst du beides behalten:
            "lastTodayState": today_state,
            # NEU: dein gewünschtes Objekt
            "today": today_obj
        })

        per_user[key] = pu
        updated_users[key] = pu

    # Aggregierter Tagesstatus (optional, unverändert)
    any_due_today = _is_due_day(today, start_date, end_date, faellige)
    if any_due_today:
        any_pending = any(u.get("today", {}).get("pending") for u in updated_users.values())
        any_done    = any(u.get("today", {}).get("erledigt") for u in updated_users.values())
        if any_done and not any_pending:
            stats_all["today"] = {"status": "done", "pending": False}
        elif any_pending:
            stats_all["today"] = {"status": "pending", "pending": True}
        else:
            stats_all["today"] = {"status": "not_pending", "pending": False}
    else:
        stats_all["today"] = {"status": "not_pending", "pending": False}

    save()
    return {
        "challengeId": cid,
        "perUser": updated_users,
        "today": stats_all.get("today", {})
    }