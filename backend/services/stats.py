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
    
    print("faellige (raw):", faellige)
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
    now_dt = datetime.now(tz)
    today = now_dt.date()
    today_iso = today.isoformat()
    yesterday = today - timedelta(days=1)

    start_date = _to_local_date_from_ts(int(start_at), tz_offset_minutes)
    end_date = start_date + timedelta(days=int(dauer) - 1) if dauer else today

    # Mitglieder der Challenge
    members = [m["userId"] for m in st.get("challenge_members", []) if m.get("challengeId") == cid]

    # Logs -> erledigt GESTERN (lokales Datum)
    logs = st.get("challenge_logs", {}).get(str(cid), [])
    confirmed_yesterday = defaultdict(bool)
    for l in logs:
        uid = l.get("userId") or l.get("user_id")
        ts = l.get("timestamp")
        if uid is None or ts is None:
            continue
        log_day = _to_local_date_from_ts(int(ts), tz_offset_minutes)
        if log_day == yesterday:
            confirmed_yesterday[int(uid)] = True

    stats_all = st.setdefault("challenge_stats", {}).setdefault(str(cid), {})
    per_user = stats_all.setdefault("perUser", {})
    updated_users: Dict[str, Any] = {}

    # Faelligkeit gestern/heute
    due_yesterday = _is_due_day(yesterday, start_date, end_date, faellige)
    due_today     = _is_due_day(today,     start_date, end_date, faellige)

    for uid in members:
        key = str(uid)
        pu = per_user.get(key) or {
            "conf_count": 0,
            "fail_count": 0,
            "streak": 0,
            "neg_streak": 0,
            "blocked": "none",
            # "state": "pending" | "not_pending"
            # "lastTodayState": "done"|"not_done"|"not_pending"
            # "lastComputedDate": None
        }

        blocked = str(pu.get("blocked", "none"))

        # NUR aktive User rechnen
        if blocked != "run":
            # Fuer nicht-aktive: nichts rechnen (auf Wunsch)
            # Optional: heutigen Anzeigezustand setzen (kommentiert, falls gar nichts gewuenscht)
            # pu.update({
            #     "state": "pending" if due_today else "not_pending",
            #     "today": {
            #         "blocked": blocked,
            #         "state": "not_done" if due_today else "not_pending",
            #         "pending": bool(due_today),
            #         "done": False,
            #     },
            #     "lastComputedAt": now_ms(),
            #     "lastComputedDate": today_iso,
            # })
            per_user[key] = pu
            continue

        # ---- AUSWERTUNG GESTERN (NUR fail_count-Logik) ----
        fail_count = int(pu.get("fail_count", 0))

        if due_yesterday:
            # Gestern war faellig
            if not confirmed_yesterday.get(uid):
                # pending & NICHT erledigt -> Fail +1
                fail_count += 1
                last_today_state = "not_done"
            else:
                # pending & erledigt -> kein conf_count-Update hier; nur State-Doku
                last_today_state = "done"
        else:
            # Gestern war NICHT faellig
            if confirmed_yesterday.get(uid):
                # nicht_pending & erledigt -> Fail -1 (falls vorher als Fail lief)
                fail_count = max(0, fail_count - 1)
                last_today_state = "done"
            else:
                # nicht_pending & nicht erledigt -> keine Aenderung
                last_today_state = "not_pending"

        # Sperr-/Abschlusspruefung (nur Fail-Grenze)
        if erlaubte_fails is not None and fail_count >= int(erlaubte_fails):
            blocked = "gesperrt"

        # Werte zurueckschreiben
        pu.update({
            # conf_count/streak/neg_streak bleiben UNBERUEHRT in diesem Recalc
            "fail_count": fail_count,
            "blocked": blocked,
            "lastTodayState": last_today_state,
        })

        # ---- HEUTE initialisieren (neuer Tag) ----
        pu.update({
            "state": "pending" if due_today else "not_pending",
            "today": {
                "blocked": blocked,
                "state": "not_done" if due_today else "not_pending",
                "pending": bool(due_today),
                "done": False,
            },
            "lastComputedAt": now_ms(),
            "lastComputedDate": today_iso,
        })

        per_user[key] = pu
        updated_users[key] = pu

    # Aggregierter HEUTE-Status
    if due_today:
        any_pending = any(u.get("today", {}).get("pending") for u in updated_users.values())
        stats_all["today"] = {"status": "pending" if any_pending else "not_pending", "pending": bool(any_pending)}
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