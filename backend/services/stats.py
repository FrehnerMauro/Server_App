from datetime import datetime, timedelta, timezone, date
from collections import defaultdict
from typing import Dict, Any, List
from backend.common.store import Database, now_ms

db = Database("state.db")

# ------------------ Hilfsfunktionen ------------------

def _to_local_date_from_ts(ts: int, tz_offset_min: int) -> date:
    """Konvertiert Timestamp in lokales Datum (Sekunden oder Millisekunden)."""
    if ts > 10**12:
        ts = ts // 1000
    tz = timezone(timedelta(minutes=tz_offset_min))
    return datetime.fromtimestamp(int(ts), tz).date()

def _normalize_weekdays(raw: List[int | str] | None) -> List[int]:
    """Normalisiert Wochentage auf 0..6."""
    if not raw:
        return []
    out: List[int] = []
    for x in raw:
        try:
            i = int(x)
            if 0 <= i <= 6:
                out.append(i)
            elif 1 <= i <= 7:
                out.append(0 if i == 7 else i - 1)
        except Exception:
            continue
    return sorted(set(out))

def _is_due_day(d: date, start_date: date, end_date: date, faellige: List[int]) -> bool:
    """Gibt True zurück, wenn Tag aktiv und im Zeitraum."""
    if not (start_date <= d <= end_date):
        return False
    return True if not faellige else (d.weekday() in faellige)

# ------------------ Kernfunktion ------------------

def challenge_update_stats(cid: int, tz_offset_minutes: int = 0) -> Dict[str, Any]:
    """Aktualisiert Tagesstatistik einer Challenge."""
    ch = db.query_one("SELECT * FROM challenges WHERE id=?", (cid,))
    if not ch:
        return {"error": "challenge_not_found", "challengeId": cid}

    start_at = ch.get("startAt")
    dauer = ch.get("dauerTage")
    erlaubte_fails = ch.get("erlaubteFailsTage")
    faellige_raw = ch.get("faelligeWochentage")
    faellige = _normalize_weekdays((faellige_raw or "").split(",") if isinstance(faellige_raw, str) else faellige_raw)

    tz = timezone(timedelta(minutes=tz_offset_minutes))
    now_dt = datetime.now(tz)
    today = now_dt.date()
    yesterday = today - timedelta(days=1)
    start_date = _to_local_date_from_ts(int(start_at), tz_offset_minutes)
    end_date = start_date + timedelta(days=int(dauer) - 1)

    due_today = _is_due_day(today, start_date, end_date, faellige)
    due_yesterday = _is_due_day(yesterday, start_date, end_date, faellige)

    members = db.query("SELECT user_id FROM challenge_members WHERE challenge_id=?", (cid,))
    member_ids = [m["user_id"] for m in members]

    logs = db.query("SELECT user_id, timestamp FROM challenge_logs WHERE challenge_id=?", (cid,))
    confirmed_yesterday = defaultdict(bool)
    for l in logs:
        uid = l["user_id"]
        ts = l["timestamp"]
        if not ts:
            continue
        log_day = _to_local_date_from_ts(int(ts), tz_offset_minutes)
        if log_day == yesterday:
            confirmed_yesterday[uid] = True

    updated_users: Dict[str, Any] = {}

    for uid in member_ids:
        st = db.query_one("""
            SELECT * FROM challenge_stats
            WHERE challenge_id=? AND user_id=?
        """, (cid, uid))

        if not st:
            st = {
                "challenge_id": cid,
                "user_id": uid,
                "conf_count": 0,
                "fail_count": 0,
                "streak": 0,
                "neg_streak": 0,
                "blocked": "run",
                "last_computed": None
            }
            db.insert("challenge_stats", st)

        conf = int(st["conf_count"])
        fail = int(st["fail_count"])
        streak = int(st["streak"])
        neg_streak = int(st["neg_streak"])
        blocked = st["blocked"] or "run"
        last_computed = st["last_computed"]

        # Nur einmal pro Tag aktualisieren
        if last_computed != today.isoformat():
            if blocked == "run" and due_yesterday:
                if confirmed_yesterday.get(uid):
                    conf += 1
                    streak += 1
                    neg_streak = 0
                else:
                    fail += 1
                    streak = 0
                    neg_streak += 1

            if erlaubte_fails is not None and fail >= int(erlaubte_fails):
                blocked = "gesperrt"
            if dauer is not None and conf >= int(dauer):
                blocked = "completed"

            db.update("challenge_stats", {
                "conf_count": conf,
                "fail_count": fail,
                "streak": streak,
                "neg_streak": neg_streak,
                "blocked": blocked,
                "last_computed": today.isoformat()
            }, where="challenge_id=? AND user_id=?", params=(cid, uid))

        updated_users[uid] = {
            "conf_count": conf,
            "fail_count": fail,
            "streak": streak,
            "neg_streak": neg_streak,
            "blocked": blocked,
            "due_today": due_today
        }

    return {"challengeId": cid, "perUser": updated_users, "today": {"pending": due_today}}

def init_challenge_members(cid: int, tz_offset_minutes: int = 0) -> Dict[str, Any]:
    """Initialisiert challenge_stats-Einträge für alle Teilnehmer."""
    members = db.query("SELECT user_id FROM challenge_members WHERE challenge_id=?", (cid,))
    tz = timezone(timedelta(minutes=tz_offset_minutes))
    today = datetime.now(tz).date()

    updated = {}
    for m in members:
        uid = m["user_id"]
        now = now_ms()
        db.insert("challenge_stats", {
        "challenge_id": cid,
    "user_id": uid,
    "conf_count": 0,
    "fail_count": 0,
    "streak": 0,
    "neg_streak": 0,
    "blocked": "run",
    "last_computed": today.isoformat(),
    "created_at": now,
    "updated_at": now
}, conflict_cols=["challenge_id", "user_id"])
    return {"challengeId": cid, "perUser": updated}