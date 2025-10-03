# backend/services/stats.py

from datetime import datetime, timedelta, timezone, date  # date hinzugefuegt
from collections import defaultdict                      # <- getrennt!
from typing import Dict, Any, List
from backend.common.store import state, save, now_ms

# ------------------ kleine Helfer ------------------

def update_stats_for_challenge_today(cid: int, tz_offset_minutes: int = 0):
    return challenge_update_stats(cid, tz_offset_minutes)

def _to_local_date_from_ts(ts: int, tz_offset_min: int) -> date:
    """Akzeptiert Sekunden oder Millisekunden."""
    if ts > 10**12:  # ms
        ts = ts // 1000
    tz = timezone(timedelta(minutes=tz_offset_min))
    return datetime.fromtimestamp(int(ts), tz).date()

def _normalize_weekdays(faellige: List[int | str] | None) -> List[int]:
    """
    Normalisiert Wochentage auf Python-Index (0=Mo ... 6=So).
    Erlaubt Strings und 1..7. 7 wird zu 0 (So->0), falls du 1=Mo ... 7=So benutzt.
    """
    if not faellige:
        return []  # leer -> spaeter als 'jeder Tag' interpretiert
    out: List[int] = []
    for x in faellige:
        try:
            i = int(x)
        except Exception:
            continue
        # akzeptiere 0..6 direkt, oder 1..7 Mapping
        if 0 <= i <= 6:
            out.append(i)
        elif 1 <= i <= 7:
            out.append(0 if i == 7 else i - 1)
    return sorted(set(out))

def _is_due_day(d: date, start_date: date, end_date: date, faellige: List[int]) -> bool:
    """Ist d innerhalb des Challenge-Zeitraums und ein faelliger Wochentag?
    Leere Liste bedeutet: JEDER Tag ist aktiv.
    """
    if not (start_date <= d <= end_date):
        return False
    return True if not faellige else (d.weekday() in faellige)

def _next_calendar_day(d: date) -> date:
    return d + timedelta(days=1)

# ------------------ Kernfunktion ------------------

def challenge_update_stats(cid: int, tz_offset_minutes: int = 0) -> Dict[str, Any]:
    st = state()
    ch = st.get("challenges", {}).get(str(cid))
    if not ch:
        return {"error": "challenge_not_found", "challengeId": cid}

    start_at = ch.get("startAt")
    dauer = ch.get("dauerTage") or ch.get("days")
    faellige_raw = ch.get("faelligeWochentage") or []
    erlaubte_fails = ch.get("erlaubteFailsTage")

    if not start_at:
        return {"error": "startAt_missing", "challengeId": cid}
    if not isinstance(faellige_raw, list):
        return {"error": "faelligeWochentage_missing", "challengeId": cid}

    faellige = _normalize_weekdays(faellige_raw)

    tz = timezone(timedelta(minutes=tz_offset_minutes))
    today_dt = datetime.now(tz)
    today = today_dt.date()
    today_iso = today.isoformat()

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
            "blocked": "none",         # "none" | "run" | "gesperrt" | "completed"
            "state": "pending",        # "pending" | "not_pending"
            "lastTodayState": "not_done",  # "done" | "not_done" | "not_pending"
            # optional fuer Idempotenz:
            # "lastComputedDate": None
        }

        blocked = str(pu.get("blocked", "none"))

        # Heutiger Aktivitaetsstatus (nur HEUTE, nicht morgen!)
        is_due_today = _is_due_day(today, start_date, end_date, faellige)
        state_today = "pending" if is_due_today else "not_pending"

        # Heutiger Erledigungsstatus
        if is_due_today:
            today_state = "done" if confirms_today.get(uid) else "not_done"
        else:
            today_state = "not_pending"

        # Zaehler idempotent nur einmal pro Kalendertag anpassen
        last_computed_date = pu.get("lastComputedDate")
        conf_count = int(pu.get("conf_count", 0))
        fail_count = int(pu.get("fail_count", 0))
        streak     = int(pu.get("streak", 0))
        neg_streak = int(pu.get("neg_streak", 0))

        if blocked not in ("completed", "gesperrt"):
            # sobald aktiv, als 'run' markieren
            if blocked == "none":
                blocked = "run"

            if last_computed_date != today_iso:
                if today_state == "not_done":
                    fail_count += 1
                    streak = 0
                    neg_streak += 1
                elif today_state == "done":
                    conf_count += 1
                    streak += 1
                    neg_streak = 0
                # not_pending -> keine Aenderung

                # Blockierungs-/Abschlusslogik
                if erlaubte_fails is not None and fail_count >= int(erlaubte_fails):
                    blocked = "gesperrt"
                if dauer is not None and conf_count >= int(dauer):
                    blocked = "completed"

        # Today-Objekt (heute)
        today_obj = {
            "blocked": blocked,
            "state": today_state,                 # "done" | "not_done" | "not_pending"
            "pending": (today_state == "not_done"),
            "done": (today_state == "done")
        }

        # Achtung: STATE SPEICHERN WIR JETZT ALS HEUTE (nicht morgen!)
        next_state = state_today

        pu.update({
            "conf_count": conf_count,
            "fail_count": fail_count,
            "streak":     streak,
            "neg_streak": neg_streak,
            "blocked":    blocked,
            "state":      next_state,             # heutig: "pending" | "not_pending"
            "lastComputedAt": now_ms(),
            "lastComputedDate": today_iso,        # fuer Idempotenz
            "lastTodayState": today_state,        # "done" | "not_done" | "not_pending"
            "today": today_obj
        })

        per_user[key] = pu
        updated_users[key] = pu

    # Aggregierter Tagesstatus (heute)
    any_due_today = _is_due_day(today, start_date, end_date, faellige)
    if any_due_today:
        any_pending = any(u.get("today", {}).get("pending") for u in updated_users.values())
        any_done    = any(u.get("today", {}).get("done") for u in updated_users.values())
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
    
    
    
    # --- Challenge initialisieren: alles auf Anfang + heutigem Pending-Status ---

def init_challenge_members(cid: int, tz_offset_minutes: int = 0) -> Dict[str, Any]:
    st = state()
    ch = st.get("challenges", {}).get(str(cid))
    if not ch:
        return {"error": "challenge_not_found", "challengeId": cid}

    start_at = ch.get("startAt")
    dauer = ch.get("dauerTage") or ch.get("days")
    faellige_raw = ch.get("faelligeWochentage") or []
    faellige = _normalize_weekdays(faellige_raw)

    tz = timezone(timedelta(minutes=tz_offset_minutes))
    today = datetime.now(tz).date()

    start_date = _to_local_date_from_ts(int(start_at), tz_offset_minutes) if start_at else today
    end_date = start_date + timedelta(days=int(dauer) - 1) if dauer else today

    # alle Member holen
    members = [m["userId"] for m in st.get("challenge_members", []) if m.get("challengeId") == cid]

    stats_all = st.setdefault("challenge_stats", {}).setdefault(str(cid), {})
    per_user = stats_all.setdefault("perUser", {})

    updated_users: Dict[str, Any] = {}
    for uid in members:
        key = str(uid)

        # bereits vorhandene Stats holen oder Basis erstellen
        pu = per_user.get(key, {
            "conf_count": 0,
            "fail_count": 0,
            "streak": 0,
            "neg_streak": 0,
            "blocked": "run"
        })

        # heute prüfen: ist ein faelliger Tag?
        is_due_today = _is_due_day(today, start_date, end_date, faellige)
        today_state = "not_done" if is_due_today else "not_pending"

        # nur den heutigen Status überschreiben – Zähler bleiben erhalten
        pu.update({
            "blocked": "run",
            "state": "pending" if is_due_today else "not_pending",
            "lastTodayState": today_state,
            "lastComputedAt": now_ms(),
            "lastComputedDate": today.isoformat(),
            "today": {
                "blocked": "run",
                "state": today_state,
                "pending": (today_state == "not_done"),
                "done": False
            }
        })

        per_user[key] = pu
        updated_users[key] = pu

    # Aggregatstatus für heute
    if _is_due_day(today, start_date, end_date, faellige):
        stats_all["today"] = {"status": "pending", "pending": True}
    else:
        stats_all["today"] = {"status": "not_pending", "pending": False}

    save()
    return {"challengeId": cid, "perUser": updated_users, "today": stats_all["today"]}