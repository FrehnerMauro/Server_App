from flask import Blueprint, request, jsonify
from backend.common.store import Database, now_ms
from datetime import datetime, timedelta, timezone, date
from typing import Dict, Any, List

db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")
bp = Blueprint("stats", __name__, url_prefix="/stats")

# ============================================================
# Hilfsfunktionen
# ============================================================

def _to_local_date_from_ts(ts: int, tz_offset_min: int) -> date:
    """Konvertiert Timestamp in lokales Datum."""
    if ts is None:
        return date.today()
    if ts > 10**12:  # falls ms
        ts //= 1000
    tz = timezone(timedelta(minutes=tz_offset_min))
    return datetime.fromtimestamp(int(ts), tz).date()

def _normalize_weekdays(raw: List[int | str] | None) -> List[int]:
    """Normalisiert gespeicherte Wochentage (0–6)."""
    if not raw:
        return []
    result = []
    for x in raw:
        try:
            i = int(x)
            if 0 <= i <= 6:
                result.append(i)
        except Exception:
            continue
    return sorted(set(result))

def _is_due_day(d: date, start_date: date, end_date: date, faellige: List[int]) -> bool:
    """True, wenn der Tag im Zeitraum liegt und fällig ist."""
    if not (start_date <= d <= end_date):
        return False
    return True if not faellige else (d.weekday() in faellige)

# ============================================================
# Kernlogik: Challenge Stats Update
# ============================================================
def challenge_update_stats(cid: int, tz_offset_minutes: int = 0) -> Dict[str, Any]:
    """Taegliche Aktualisierung (Job um 23:55). Arbeitet fuer den *naechsten Tag*.
       States:
         - run: normaler Tagesabschluss + Pending fuer morgen
         - not_started: wenn morgen Start erreicht -> auf run + Pending fuer morgen
         - pending: wenn challenge_members.status jetzt 'accepted'/'creator' und morgen Start erreicht -> auf run + Pending fuer morgen
         - blocked/completed: keine Aenderung
       Zusaetzlich:
         - completed wenn conf_count >= dauer
         - blocked wenn fail_count > erlaubte_fails
    """
    print(f"\n⚙️ challenge_update_stats(cid={cid}, tz_offset={tz_offset_minutes})")

    ch = db.query_one("SELECT * FROM challenges WHERE id=%s", (cid,))
    if not ch:
        return {"error": "challenge_not_found", "challengeId": cid}

    # --- Challenge-Metadaten ---
    start_at = ch.get("startedAt") or ch.get("startAt") or ch.get("start_at") or ch.get("created_at")
    dauer = ch.get("duration_days")
    erlaubte_fails = ch.get("allowed_fails")
    due_raw = ch.get("due_weekdays")

    if start_at is None or dauer is None:
        return {"error": "invalid_challenge", "challengeId": cid}

    due_days = _normalize_weekdays(
        (due_raw or "").split(",") if isinstance(due_raw, str) else due_raw
    )

    tz = timezone(timedelta(minutes=tz_offset_minutes))
    now_dt = datetime.now(tz)
    today = now_dt.date()
    tomorrow = today + timedelta(days=1)

    start_date = _to_local_date_from_ts(int(start_at), tz_offset_minutes)
    end_date = start_date + timedelta(days=int(dauer) - 1)

    # Wir planen fuer MORGEN, da Job um 23:55 laeuft
    due_today = _is_due_day(today, start_date, end_date, due_days)
    due_tomorrow = _is_due_day(tomorrow, start_date, end_date, due_days)
    challenge_started_by_tomorrow = (tomorrow >= start_date)

    print(f"📅 Zeitraum: {start_date} → {end_date} (Dauer={int(dauer)})")
    print(f"   Heute faellig: {due_today}, Morgen faellig: {due_tomorrow}, Start bis morgen erreicht: {challenge_started_by_tomorrow}")

    # --- Mitglieder inkl. aktuellem Mitglieds-Status holen ---
    members = db.query("""
        SELECT user_id, COALESCE(status, 'accepted') AS member_status
        FROM challenge_members
        WHERE challenge_id=%s
    """, (cid,))
    member_rows = {m["user_id"]: m["member_status"] for m in members}
    member_ids = list(member_rows.keys())
    print(f"👥 {len(member_ids)} Teilnehmer gefunden.")

    updates: Dict[int, Any] = {}
    now = now_ms()

    # Sicherstellen, dass fuer jeden Member ein stats-Record existiert.
    for uid, member_status in member_rows.items():
        st = db.query_one("""
            SELECT * FROM challenge_stats WHERE challenge_id=%s AND user_id=%s
        """, (cid, uid))

        if not st:
            # Initial blocked-State fuer neue Statszeile ableiten:
            if member_status == "pending":
                initial_blocked = "pending"
            else:
                initial_blocked = "run" if (today >= start_date) else "not_started"

            db.raw("""
                INSERT INTO challenge_stats
                    (challenge_id, user_id,
                     conf_count, fail_count, streak, neg_streak,
                     blocked, today_done, today_pending,
                     last_computed, created_at, updated_at)
                VALUES (%s,%s,
                        0,0,0,0,
                        %s, 0, %s,
                        NULL, %s, %s)
                ON CONFLICT (challenge_id, user_id) DO NOTHING
            """, (cid, uid, initial_blocked, 1 if due_today and initial_blocked=="run" else 0, now, now))
            st = db.query_one("""
                SELECT * FROM challenge_stats WHERE challenge_id=%s AND user_id=%s
            """, (cid, uid))

        # --- Aktuelle Werte aus stats ---
        blocked = st.get("blocked", "run")
        conf = int(st.get("conf_count", 0))
        fail = int(st.get("fail_count", 0))
        streak = int(st.get("streak", 0))
        neg_streak = int(st.get("neg_streak", 0))
        today_done = int(st.get("today_done", 0)) == 1
        today_pending_flag = int(st.get("today_pending", 0)) == 1
        last_computed = st.get("last_computed")

        # 0) Abkuerzung: bei 'blocked' oder 'completed' GAR NICHTS machen
        if blocked in ("blocked", "completed"):
            updates[uid] = {"blocked": blocked, "skipped": True}
            continue

        # 1) 'pending': pruefen, ob Mitglied inzwischen akzeptiert ist
        if blocked == "pending":
            mstat = member_rows.get(uid, "accepted")
            if mstat in ("accepted", "creator"):
                if challenge_started_by_tomorrow:
                    # ab morgen starten
                    db.update("challenge_stats", {
                        "blocked": "run",
                        "today_pending": 1 if due_tomorrow else 0,
                        "updated_at": now
                    }, where="challenge_id=%s AND user_id=%s", params=(cid, uid))
                    print(f"🔁 User {uid}: pending -> run (ab morgen). pending_tomorrow={1 if due_tomorrow else 0}")
                    updates[uid] = {"blocked": "run", "pending_to_run": True, "pending_tomorrow": bool(due_tomorrow)}
                else:
                    # Challenge startet noch nicht -> als not_started belassen
                    db.update("challenge_stats", {
                        "blocked": "not_started",
                        "today_pending": 0,
                        "updated_at": now
                    }, where="challenge_id=%s AND user_id=%s", params=(cid, uid))
                    print(f"⏳ User {uid}: pending -> not_started (Start noch nicht erreicht).")
                    updates[uid] = {"blocked": "not_started"}
            else:
                # bleibt pending
                print(f"🕓 User {uid}: bleibt pending.")
                updates[uid] = {"blocked": "pending"}
            continue

        # 2) 'not_started': wenn bis morgen Start erreicht -> run + pending fuer morgen
        if blocked == "not_started":
            if challenge_started_by_tomorrow:
                db.update("challenge_stats", {
                    "blocked": "run",
                    "today_pending": 1 if due_tomorrow else 0,
                    "updated_at": now
                }, where="challenge_id=%s AND user_id=%s", params=(cid, uid))
                print(f"🚀 User {uid}: not_started -> run (ab morgen). pending_tomorrow={1 if due_tomorrow else 0}")
                updates[uid] = {"blocked": "run", "pending_tomorrow": bool(due_tomorrow)}
            else:
                # noch nicht starten
                print(f"⏳ User {uid}: bleibt not_started (Start noch nicht erreicht).")
                updates[uid] = {"blocked": "not_started"}
            continue

        # 3) 'run': normaler Tagesabschluss fuer HEUTE, dann pending fuer MORGEN
        # 3) 'run': normale Tageslogik mit neuen Regeln
        if blocked == "run":
            if last_computed != 1:
                # Reset am Tagesanfang / vor neuer Berechnung
                print(f"🧮 Berechne Tagesupdate für User {uid}")

                if today_done:
                    if today_pending_flag:
                        # ✅ Fall 1: pending + done

                        print(f"✅ User {uid}: pending war aktiv, conf={conf}, streak={streak}")
                    else:
                        # ✅ Fall 2: nicht pending, aber done → trotzdem Erfolg
                        
                        fail = max(0, fail - 1)  # 1 Fail "wiedergutgemacht"
                        print(f"✅ User {uid}: kein pending, aber done → conf={conf}, streak={streak}, fail={fail}")
                else:
                    if today_pending_flag:
                        # ❌ Fall 3: pending aber nicht erledigt
                        streak = 0
                        fail += 1
                        print(f"❌ User {uid}: pending aber nicht done → fail={fail}, streak reset")

                # Schwellen prüfen
                if int(dauer) > 0 and conf >= int(dauer):
                    blocked = "completed"
                    print(f"🏁 User {uid}: Challenge abgeschlossen (conf={conf}/{dauer})")

                if erlaubte_fails is not None:
                    try:
                        allowed = int(erlaubte_fails)
                        if fail > allowed:
                            blocked = "blocked"
                            print(f"🚫 User {uid}: zu viele Fails (fail={fail} > erlaubt={allowed})")
                    except Exception:
                        pass

                # Update speichern (Tag abgeschlossen)
                db.update("challenge_stats", {
                    "conf_count": conf,
                    "fail_count": fail,
                    "streak": streak,
                    "neg_streak": neg_streak,
                    "blocked": blocked,
                    "today_done": 0,           # Reset
                    "today_pending": 0,        # wird unten für morgen gesetzt
                    "last_computed": today.isoformat(),
                    "updated_at": now
                }, where="challenge_id=%s AND user_id=%s", params=(cid, uid))

            # 4️⃣ Nächster Tag vorbereiten
            db.update("challenge_stats", {
                "today_pending": 1 if due_tomorrow else 0,
                "updated_at": now
            }, where="challenge_id=%s AND user_id=%s", params=(cid, uid))

            print(f"🔄 User {uid}: today_pending für morgen = {1 if due_tomorrow else 0}")

            updates[uid] = {
                "blocked": blocked,
                "conf_count": conf,
                "fail_count": fail,
                "streak": streak,
                "pending_tomorrow": bool(due_tomorrow)
            }
            continue

        # Unbekannter Zustand – ignoriere
        print(f"⚠️ User {uid}: unbekannter blocked-Status '{blocked}', keine Aktion.")
        updates[uid] = {"blocked": blocked, "unknown_state": True}

    print(f"✅ Challenge {cid} Update beendet.")
    return {
        "challengeId": cid,
        "perUser": updates,
        "today": {
            "due_today": due_today,
            "due_tomorrow": due_tomorrow
        },
        "note": "Tagesabschluss (run) + Pending fuer naechsten Tag. pending/not_started werden fuer morgen geprueft."
    }
# ============================================================
# Init-Funktion (bei Challenge-Erstellung)
# ============================================================



def init_challenge_members(cid: int, tz_offset_minutes: int = 0) -> Dict[str, Any]:
    """Initialisiert Stats für alle Mitglieder einer Challenge.
       - Jeder ChallengeMember erhält einen eigenen Datensatz in challenge_stats.
       - blocked hängt von Status + Startdatum ab.
         -> pending => blocked='pending'
         -> startdatum zukünftig => blocked='not_started'
         -> sonst => blocked='run'
    """
    print(f"\n🧩 init_challenge_members(cid={cid})")

    # --- Challenge abrufen ---
    ch = db.query_one("SELECT * FROM challenges WHERE id=%s", (cid,))
    if not ch:
        print(f"❌ Challenge {cid} nicht gefunden.")
        return {"error": "challenge_not_found", "challengeId": cid}

    # --- Startzeit bestimmen ---
    start_raw = ch.get("startedAt") or ch.get("startAt") or ch.get("start_at") or ch.get("created_at")
    try:
        start_ts = int(float(start_raw)) if start_raw is not None else None
    except Exception:
        start_ts = None

    tz = timezone(timedelta(minutes=tz_offset_minutes))
    today = datetime.now(tz).date()

    if start_ts is None:
        print("⚠️ Kein gültiges Startdatum, verwende jetzt.")
        start_ts = int(datetime.now(tz).timestamp()) * 1000
        start_date = _to_local_date_from_ts(start_ts, tz_offset_minutes)
        has_started = False
    else:
        start_date = _to_local_date_from_ts(start_ts, tz_offset_minutes)
        has_started = today >= start_date

    # --- Dauer / Endedatum ---
    try:
        duration_days = int(ch.get("duration_days") or 0)
    except Exception:
        duration_days = 0
    end_date = start_date + timedelta(days=max(duration_days - 1, 0))

    # --- Fällige Wochentage ---
    due_raw = ch.get("due_weekdays")
    due_days = _normalize_weekdays(
        (due_raw or "").split(",") if isinstance(due_raw, str) else due_raw
    )

    due_today = _is_due_day(today, start_date, end_date, due_days) if has_started else False
    print(f"📅 Zeitraum: {start_date} → {end_date}  Dauer={duration_days}")
    print(f"🚦 Gestartet={has_started}, Heute fällig={due_today}")

    # --- Mitglieder inkl. Status holen ---
    members = db.query("""
        SELECT user_id, COALESCE(status, 'accepted') AS status
        FROM challenge_members
        WHERE challenge_id=%s
    """, (cid,))
    print(f"👥 {len(members)} Mitglieder in challenge_members gefunden.")
    print(members)
    if not members:
        print(f"⚠️ Keine Mitglieder in challenge_members für Challenge {cid}")
        return {"challengeId": cid, "initialized": False, "reason": "no_members"}

    now = now_ms()

    # --- Für jeden User einen Stat-Eintrag erzeugen ---
    for m in members:
        uid = m["user_id"]
        member_status = (m.get("status") or "accepted").lower().strip()

        # Blocked bestimmen
        if member_status == "pending":
            blocked_status = "pending"
        elif not has_started:
            blocked_status = "not_started"
        else:
            blocked_status = "run"

        today_pending = 1 if (blocked_status == "run" and due_today) else 0

        payload = {
            "challenge_id": cid,
            "user_id": uid,
            "conf_count": 0,
            "fail_count": 0,
            "streak": 0,
            "neg_streak": 0,
            "blocked": blocked_status,
            "today_done": 0,
            "today_pending": today_pending,
            "last_computed": None,
            "created_at": now,
            "updated_at": now,
        }

        try:
            sid = db.insert("challenge_stats", payload)
            print(f"🧩 INSERT stats → user={uid}, id={sid}, blocked='{blocked_status}', today_pending={today_pending}")
        except Exception as e:
            print(f"ℹ️ INSERT-Konflikt oder vorhanden für user={uid} → UPDATE: {e}")
            db.update(
                "challenge_stats",
                {
                    "blocked": blocked_status,
                    "today_pending": today_pending,
                    "updated_at": now,
                },
                "challenge_id=%s AND user_id=%s",
                (cid, uid),
            )
            print(f"🛠️ UPDATE stats → user={uid}, blocked='{blocked_status}', today_pending={today_pending}")

    print(f"✅ Alle ChallengeMember ({len(members)}) in ChallengeStats initialisiert.")
    return {"challengeId": cid, "initialized": True, "memberCount": len(members)}
# ============================================================
# API-Endpoint
# ============================================================

@bp.post("/update")
def update_all_challenges_endpoint():
    """Aktualisiert alle Challenges."""
    try:
        data = request.get_json(force=True) or {}
        tz_offset = int(data.get("tz_offset", 0))
    except Exception:
        tz_offset = 0

    print(f"\n🧩 [DEBUG] update_all_challenges_endpoint: tz_offset={tz_offset}")

    challenges = db.query("SELECT id FROM challenges")
    results = {}

    for ch in challenges:
        cid = ch["id"]
        results[str(cid)] = challenge_update_stats(cid, tz_offset_minutes=tz_offset)

    print("✅ Alle Challenges erfolgreich aktualisiert.")
    return jsonify(results), 200