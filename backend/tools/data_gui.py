
import json
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Challenge JSON Viewer", layout="wide")

st.title("Challenge JSON Viewer")
st.write("Interaktive GUI zum genauen Einsehen deiner Daten (nur Lesen).")

# -------------- helpers --------------

def load_json_from_path(path_str: str) -> Optional[Dict[str, Any]]:
    try:
        p = Path(path_str).expanduser().resolve()
        if not p.exists():
            st.error(f"Datei nicht gefunden: {p}")
            return None
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.exception(e)
        return None

def normalize_per_user(per_user: Dict[str, Any]) -> pd.DataFrame:
    if not per_user:
        return pd.DataFrame()
    rows = []
    for uid, stats in per_user.items():
        row = {"userId": int(uid)}
        if isinstance(stats, dict):
            row.update(stats)
        rows.append(row)
    df = pd.DataFrame(rows)
    # sinnvolle Sortierung
    order_cols = ["userId","conf_count","fail_count","streak","neg_streak","blocked","state","lastTodayState","lastComputedAt"]
    cols = [c for c in order_cols if c in df.columns] + [c for c in df.columns if c not in order_cols]
    if len(cols) > 0:
        df = df[cols]
    return df.sort_values(by=["userId"], ascending=True, ignore_index=True)

def normalize_members(members, cid: int) -> pd.DataFrame:
    rows = [m for m in (members or []) if m.get("challengeId") == cid]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

def normalize_logs(logs_for_challenge) -> pd.DataFrame:
    if not logs_for_challenge:
        return pd.DataFrame()
    # logs_for_challenge ist typ. eine Liste von Eintraegen
    df = pd.DataFrame(logs_for_challenge)
    # Normalisierung ueblicher Felder
    rename = {"user_id":"userId","timestamp":"timestamp"}
    for a,b in rename.items():
        if a in df.columns and b not in df.columns:
            df[b] = df[a]
    return df

# -------------- input --------------

with st.sidebar:
    st.header("Datenquelle")
    source = st.radio("Quelle waehlen", ["Upload", "Pfad"], index=0)
    data: Optional[Dict[str, Any]] = None
    if source == "Upload":
        up = st.file_uploader("JSON-Datei hochladen", type=["json"])
        if up is not None:
            try:
                data = json.load(up)
            except Exception as e:
                st.error("Konnte Datei nicht lesen.")
                st.exception(e)
    else:
        default_path = st.text_input("Pfad zur JSON-Datei", value="data.json", help="z. B. ./data.json")
        if st.button("Laden", type="primary"):
            data = load_json_from_path(default_path)

if data is None:
    st.info("Bitte lade eine JSON-Datei hoch oder gib einen Dateipfad an und klicke auf Laden.")
    st.stop()

# -------------- overview --------------

st.subheader("Uebersicht")
keys = list(data.keys())
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Top-Level Keys", len(keys))
with col2:
    st.metric("Challenges", len((data.get("challenges") or {})))
with col3:
    st.metric("Challenge Stats", len((data.get("challenge_stats") or {})))

with st.expander("Rohdaten (Top-Level) anzeigen", expanded=False):
    st.json(data, expanded=False)

# -------------- challenge focus --------------

challenges = data.get("challenges") or {}
challenge_ids = list(challenges.keys())
if not challenge_ids:
    st.warning("Keine Challenges gefunden.")
    st.stop()

# Auswahl
cid_key = st.selectbox("Challenge waehlen (ID)", options=challenge_ids, format_func=lambda x: f"ID {x}")
cid_int = None
try:
    cid_int = int(cid_key)
except Exception:
    pass

# Metadaten
st.markdown("---")
st.subheader("Challenge Metadaten")
meta = challenges.get(cid_key) or {}
if meta:
    mleft, mright = st.columns([2,1])
    with mleft:
        st.json(meta, expanded=False)
    with mright:
        st.write("Kurzinfos")
        st.write(f"- startAt: `{meta.get('startAt')}`")
        st.write(f"- dauerTage/days: `{meta.get('dauerTage') or meta.get('days')}`")
        st.write(f"- faelligeWochentage: `{meta.get('faelligeWochentage')}`")
        st.write(f"- erlaubteFailsTage: `{meta.get('erlaubteFailsTage')}`")
else:
    st.info("Keine Metadaten fuer diese Challenge.")

# Mitglieder
st.markdown("---")
st.subheader("Mitglieder")
members = data.get("challenge_members") or []
df_members = normalize_members(members, cid_int if cid_int is not None else -1)
if df_members.empty:
    st.caption("Keine Mitglieder gefunden.")
else:
    st.dataframe(df_members, use_container_width=True, hide_index=True)

# Logs
st.markdown("---")
st.subheader("Logs")
logs_all = (data.get("challenge_logs") or {}).get(str(cid_key)) or (data.get("challenge_logs") or {}).get(cid_key) or []
df_logs = normalize_logs(logs_all)
if df_logs.empty:
    st.caption("Keine Logs fuer diese Challenge.")
else:
    # kleine Filter
    with st.expander("Filter", expanded=False):
        user_filter = st.text_input("Nur Logs fuer userId (optional)")
    if user_filter:
        try:
            uf = int(user_filter)
            df_logs = df_logs[df_logs["userId"] == uf]
        except Exception:
            st.warning("userId Filter ist keine Zahl.")
    st.dataframe(df_logs.sort_values(by=df_logs.columns[0], axis=0, ignore_index=True) if not df_logs.empty else df_logs,
                 use_container_width=True, hide_index=True)

# Stats
st.markdown("---")
st.subheader("Per-User Stats")
stats_all = (data.get("challenge_stats") or {}).get(str(cid_key)) or (data.get("challenge_stats") or {}).get(cid_key) or {}
per_user = (stats_all or {}).get("perUser") or {}
df_stats = normalize_per_user(per_user)

if df_stats.empty:
    st.caption("Keine per-User Stats vorhanden.")
else:
    # Filter
    with st.expander("Filter & Suche", expanded=False):
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            uid_query = st.text_input("userId enthaelt (oder genau)")
        with colf2:
            blocked_filter = st.selectbox("blocked", options=["(alle)","none","gesperrt","completed"], index=0)
        with colf3:
            state_filter = st.selectbox("state", options=["(alle)","pending","nicht_pending","erledigt"], index=0)

    df_view = df_stats.copy()
    if uid_query:
        try:
            q = int(uid_query)
            df_view = df_view[df_view["userId"].astype(str).str.contains(str(q), na=False)]
        except Exception:
            df_view = df_view[df_view["userId"].astype(str).str.contains(uid_query, na=False)]

    if blocked_filter != "(alle)" and "blocked" in df_view.columns:
        df_view = df_view[df_view["blocked"] == blocked_filter]
    if state_filter != "(alle)" and "state" in df_view.columns:
        df_view = df_view[df_view["state"] == state_filter]

    st.dataframe(df_view, use_container_width=True, hide_index=True)

# Today status (falls vorhanden)
st.markdown("---")
st.subheader("Heutiger Status (falls berechnet)")
today_block = (stats_all or {}).get("today")
if today_block:
    st.json(today_block, expanded=False)
else:
    st.caption("Kein 'today' Block vorhanden.")

st.markdown("---")
st.caption("Hinweis: Diese App schreibt nichts zurueck. Wenn du Editieren moechtest, muesstest du eine Save-Funktion hinzufuegen.")
