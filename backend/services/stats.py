from typing import Dict, Any
from backend.common.store import state

def update_stats_for_challenge_today(cid: int, tz_offset_min: int):
    # Dummy: hier koenntest du Tagesstatus rekonstruieren
    # Wir berechnen minimal status/pending auf Basis der Logs.
    st = state()
    logs = st.get("challenge_logs", {}).get(str(cid), [])
    today_status = "open" if not logs else "done"
    st.setdefault("challenge_stats", {})[str(cid)] = {
        "today": {"status": today_status, "pending": today_status == "open"}
    }
    # kein save(), da nur cache-artig