import json
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional, List

import pandas as pd
import streamlit as st

# ==============================
# Setup
# ==============================

st.set_page_config(page_title="Challenge JSON Viewer", layout="wide")
st.title("Challenge JSON Viewer")
st.write("Interaktive GUI zum Einsehen **und** Bearbeiten deiner Daten.")

# ==============================
# Helpers
# ==============================

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

def dumps_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)

def ensure_dict(obj: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}

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
    order_cols = [
        "userId","conf_count","fail_count","streak","neg_streak",
        "blocked","state","lastTodayState","lastComputedAt","lastComputedDate"
    ]
    cols = [c for c in order_cols if c in df.columns] + [c for c in df.columns if c not in order_cols]
    if cols:
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
    df = pd.DataFrame(logs_for_challenge)
    # vereinheitliche Felder
    rename = {"user_id":"userId"}
    for a,b in rename.items():
        if a in df.columns and b not in df.columns:
            df[b] = df[a]
    # sinnvolle Spaltenordnung
    order = ["userId","timestamp","caption","imageUrl","type","id"]
    cols = [c for c in order if c in df.columns] + [c for c in df.columns if c not in order]
    if cols:
        df = df[cols]
    return df

def df_to_records(df: pd.DataFrame) -> List[dict]:
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records"))

def df_per_user_to_map(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {}
    out: Dict[str, Any] = {}
    for _, row in df.iterrows():
        # userId MUSS vorhanden sein
        if "userId" not in row or pd.isna(row["userId"]):
            # ueberspringen statt crashen
            continue
        uid = str(int(row["userId"]))
        rec = row.to_dict()
        rec.pop("userId", None)
        out[uid] = rec
    return out

def df_members_to_list(df: pd.DataFrame) -> List[dict]:
    return df_to_records(df)

def df_logs_to_list(df: pd.DataFrame) -> List[dict]:
    recs = df_to_records(df)
    for r in recs:
        # unify field naming
        if "user_id" in r and "userId" not in r:
            r["userId"] = r.pop("user_id")
    return recs

# ==============================
# Datenquelle
# ==============================

with st.sidebar:
    st.header("Datenquelle")
    source = st.radio("Quelle waehlen", ["Upload", "Pfad"], index=0)
    data: Optional[Dict[str, Any]] = None
    default_path = None
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

# ==============================
# Edit-Modus & Ziel
# ==============================

st.markdown("---")
st.subheader("Editieren & Speichern")

edit_mode = st.checkbox(
    "Editiermodus aktivieren",
    value=False,
    help="Erlaubt das Aendern in Formularen und Tabellen unten."
)

col_save1, col_save2 = st.columns([3,2])
with col_save1:
    if source == "Pfad":
        output_path = st.text_input(
            "Zielpfad zum Speichern",
            value=(default_path or "data.json")
        )
        make_backup = st.checkbox("Backup .bak anlegen", value=True)
    else:
        st.caption("Upload-Quelle: Originaldatei wird nicht ueberschrieben. Du bekommst einen Download-Button.")

# ==============================
# Uebersicht
# ==============================

st.subheader("Uebersicht")
keys = list(data.keys())
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Top-Level Keys", len(keys))
with c2:
    st.metric("Challenges", len((data.get("challenges") or {})))
with c3:
    st.metric("Challenge Stats", len((data.get("challenge_stats") or {})))

with st.expander("Rohdaten (Top-Level) anzeigen", expanded=False):
    st.json(data, expanded=False)

# ==============================
# Challenge Auswahl
# ==============================

challenges = data.get("challenges") or {}
challenge_ids = list(challenges.keys())
if not challenge_ids:
    st.warning("Keine Challenges gefunden.")
    st.stop()

cid_key = st.selectbox("Challenge waehlen (ID)", options=challenge_ids, format_func=lambda x: f"ID {x}")
try:
    cid_int = int(cid_key)
except Exception:
    cid_int = None

# ==============================
# Metadaten
# ==============================

st.markdown("---")
st.subheader("Challenge Metadaten")
meta = ensure_dict(challenges.get(cid_key))

with st.form(key="meta_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        startAt = st.text_input("startAt (ms)", value=str(meta.get("startAt") or ""))
        dauer_val = meta.get("dauerTage") if meta.get("dauerTage") is not None else meta.get("days")
        dauerTage = st.text_input("dauerTage / days", value=str(dauer_val or ""))
        erlaubteFailsTage = st.text_input("erlaubteFailsTage", value=str(meta.get("erlaubteFailsTage") or ""))
    with c2:
        f_raw = meta.get("faelligeWochentage") or []
        faellige_str = st.text_input("faelligeWochentage (JSON Liste, z. B. [1,3,5])", value=json.dumps(f_raw))
        sonst = st.text_area("Weitere Felder (JSON-Merge, optional)", value="", placeholder='z. B. {"name":"Meine Challenge"}')

    meta_submit = st.form_submit_button("Metadaten uebernehmen", disabled=not edit_mode, use_container_width=True)

if meta_submit and edit_mode:
    try:
        meta["startAt"] = int(startAt) if str(startAt).strip() != "" else None
    except Exception:
        st.warning("startAt ist keine gueltige Zahl.")
    try:
        if str(dauerTage).strip() == "":
            meta.pop("dauerTage", None); meta.pop("days", None)
        else:
            dv = int(dauerTage)
            # bevorzugt dauerTage
            meta["dauerTage"] = dv
            meta.pop("days", None)
    except Exception:
        st.warning("dauerTage/days ist keine gueltige Zahl.")
    try:
        if str(erlaubteFailsTage).strip() == "":
            meta.pop("erlaubteFailsTage", None)
        else:
            meta["erlaubteFailsTage"] = int(erlaubteFailsTage)
    except Exception:
        st.warning("erlaubteFailsTage ist keine gueltige Zahl.")
    try:
        meta["faelligeWochentage"] = json.loads(faellige_str) if faellige_str.strip() else []
    except Exception:
        st.warning("faelligeWochentage ist kein gueltiges JSON (Liste).")
    if sonst.strip():
        try:
            extra = json.loads(sonst)
            if isinstance(extra, dict):
                meta.update(extra)
            else:
                st.warning("Weitere Felder ist kein JSON-Objekt.")
        except Exception:
            st.warning("Weitere Felder: JSON-Parsing fehlgeschlagen.")
    # persist in place
    data.setdefault("challenges", {})[cid_key] = meta
    st.success("Metadaten uebernommen.")

# Metadaten kurz anzeigen
mleft, mright = st.columns([2,1])
with mleft:
    st.json(meta, expanded=False)
with mright:
    st.write("Kurzinfos")
    st.write(f"- startAt: `{meta.get('startAt')}`")
    st.write(f"- dauerTage/days: `{meta.get('dauerTage') or meta.get('days')}`")
    st.write(f"- faelligeWochentage: `{meta.get('faelligeWochentage')}`")
    st.write(f"- erlaubteFailsTage: `{meta.get('erlaubteFailsTage')}`")

# ==============================
# Mitglieder
# ==============================

st.markdown("---")
st.subheader("Mitglieder")
members_all = data.get("challenge_members") or []
df_members = normalize_members(members_all, cid_int if cid_int is not None else -1)

with st.expander("Mitglieder bearbeiten", expanded=False):
    st.caption("Nutze die Tabelle, um Eintraege zu aendern, neue Zeilen hinzuzufuegen oder zu loeschen.")
    df_members_edit = st.data_editor(
        df_members if not df_members.empty else pd.DataFrame(columns=["id","challengeId","userId"]),
        num_rows="dynamic",
        use_container_width=True,
        disabled=not edit_mode
    )
    col_mb1, col_mb2 = st.columns(2)
    with col_mb1:
        apply_members = st.button("Mitglieder uebernehmen", disabled=not edit_mode, use_container_width=True)
    with col_mb2:
        st.write("")
    if apply_members and edit_mode:
        # filter nur die fuer diese Challenge
        new_rows = df_members_to_list(df_members_edit)
        # alte Liste ohne diese Challenge + neue rein
        others = [m for m in members_all if m.get("challengeId") != (cid_int if cid_int is not None else None)]
        # saubere ints
        for r in new_rows:
            if "challengeId" not in r or r["challengeId"] in ("", None):
                r["challengeId"] = cid_int
        data["challenge_members"] = others + new_rows
        st.success("Mitglieder gespeichert.")

# ==============================
# Logs
# ==============================

st.markdown("---")
st.subheader("Logs")
logs_all = (data.get("challenge_logs") or {})
logs_for_ch = logs_all.get(str(cid_key)) or logs_all.get(cid_key) or []
df_logs = normalize_logs(logs_for_ch)

user_filter = None
with st.expander("Filter", expanded=False):
    user_filter = st.text_input("Nur Logs fuer userId (optional)")
if user_filter:
    try:
        uf = int(user_filter)
        df_logs = df_logs[df_logs["userId"] == uf]
    except Exception:
        st.warning("userId Filter ist keine Zahl.")

with st.expander("Logs bearbeiten", expanded=False):
    st.caption("Zeitstempel sind erwartungsgemaess in ms. Spalten koennen frei erweitert werden.")
    df_logs_edit = st.data_editor(
        df_logs if not df_logs.empty else pd.DataFrame(columns=["userId","timestamp","caption","imageUrl"]),
        num_rows="dynamic",
        use_container_width=True,
        disabled=not edit_mode
    )
    c_la, c_lb = st.columns(2)
    with c_la:
        apply_logs = st.button("Logs uebernehmen", disabled=not edit_mode, use_container_width=True)
    if apply_logs and edit_mode:
        # komplette Liste fuer diese Challenge ersetzen
        new_list = df_logs_to_list(df_logs_edit)
        # set in data
        data.setdefault("challenge_logs", {})
        data["challenge_logs"][str(cid_key)] = new_list
        st.success("Logs gespeichert.")

# Anzeige aktuelle Logs (ungefiltert) optional:
with st.expander("Aktuelle Logs (roh)", expanded=False):
    st.dataframe(normalize_logs(logs_all.get(str(cid_key)) or logs_all.get(cid_key) or []),
                 use_container_width=True, hide_index=True)

# ==============================
# Per-User-Stats
# ==============================

st.markdown("---")
st.subheader("Per-User Stats")
stats_all = (data.get("challenge_stats") or {}).get(str(cid_key)) or (data.get("challenge_stats") or {}).get(cid_key) or {}
per_user = (stats_all or {}).get("perUser") or {}
df_stats = normalize_per_user(per_user)

with st.expander("Filter & Suche", expanded=False):
    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        uid_query = st.text_input("userId enthaelt (oder genau)")
    with colf2:
        blocked_filter = st.selectbox("blocked", options=["(alle)","none","gesperrt","completed","run"], index=0)
    with colf3:
        state_filter = st.selectbox("state", options=["(alle)","pending","not_pending","done","not_done"], index=0)

df_view = df_stats.copy()
if not df_view.empty:
    if uid_query:
        df_view = df_view[df_view["userId"].astype(str).str.contains(uid_query, na=False)]
    if blocked_filter != "(alle)" and "blocked" in df_view.columns:
        df_view = df_view[df_view["blocked"] == blocked_filter]
    if state_filter != "(alle)" and "state" in df_view.columns:
        df_view = df_view[df_view["state"] == state_filter]

with st.expander("Per-User Stats bearbeiten", expanded=False):
    st.caption("Aendere Werte direkt in der Tabelle. userId ist Pflichtspalte.")
    df_stats_edit = st.data_editor(
        df_view if not df_view.empty else pd.DataFrame(columns=[
            "userId","conf_count","fail_count","streak","neg_streak","blocked","state","lastTodayState","lastComputedAt","lastComputedDate"
        ]),
        num_rows="dynamic",
        use_container_width=True,
        disabled=not edit_mode
    )
    apply_stats = st.button("Per-User Stats uebernehmen", disabled=not edit_mode, use_container_width=True)
    if apply_stats and edit_mode:
        # Wir schreiben auf Basis der BEARBEITETEN Sicht; Achtung: Filter koennte Zeilen verstecken.
        # Strategie: Map der editierten Zeilen bauen und in perUser ersetzen (nur fuer die betroffenen userIds).
        new_map = df_per_user_to_map(df_stats_edit)
        # alte Map holen (voll)
        full_stats_all = data.setdefault("challenge_stats", {}).setdefault(str(cid_key), {})
        full_per_user = ensure_dict(full_stats_all.get("perUser"))
        # upsert je userId aus new_map
        for uid, rec in new_map.items():
            full_per_user[uid] = rec
        # falls Zeilen geloescht werden sollen, die im Filter nicht sichtbar waren, muesste man separat behandeln.
        full_stats_all["perUser"] = full_per_user
        st.success("Per-User Stats gespeichert.")

# Anzeige der aktuellen Stats (roh)
if df_stats.empty:
    st.caption("Keine per-User Stats vorhanden.")
else:
    st.dataframe(df_stats, use_container_width=True, hide_index=True)

# ==============================
# Today-Block
# ==============================

st.markdown("---")
st.subheader("Heutiger Status (today)")

stats_for_ch = data.setdefault("challenge_stats", {}).setdefault(str(cid_key), {})
today_block = ensure_dict(stats_for_ch.get("today"))

with st.form(key="today_form", clear_on_submit=False):
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        t_status = st.selectbox("status", ["pending","not_pending","done"], index=["pending","not_pending","done"].index(today_block.get("status","not_pending")))
    with t_col2:
        t_pending = st.checkbox("pending (bool)", value=bool(today_block.get("pending", False)))
    today_submit = st.form_submit_button("Today uebernehmen", disabled=not edit_mode, use_container_width=True)

if today_submit and edit_mode:
    stats_for_ch["today"] = {"status": t_status, "pending": bool(t_pending)}
    st.success("Today-Block gespeichert.")

# Anzeige
if stats_for_ch.get("today"):
    st.json(stats_for_ch["today"], expanded=False)
else:
    st.caption("Kein 'today' Block vorhanden.")

# ==============================
# Speichern
# ==============================

st.markdown("---")
st.subheader("Speichern")

if source == "Pfad":
    col_sp1, col_sp2 = st.columns([1,3])
    with col_sp1:
        do_save = st.button("In Datei speichern", type="primary", use_container_width=True, disabled=not edit_mode)
    if do_save and edit_mode:
        try:
            out = Path(output_path).expanduser().resolve()
            if make_backup and out.exists():
                bak = out.with_suffix(out.suffix + ".bak")
                bak.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
            out.write_text(dumps_json(data), encoding="utf-8")
            st.success(f"Gespeichert nach: {out}")
        except Exception as e:
            st.error("Speichern fehlgeschlagen.")
            st.exception(e)
else:
    # Upload-Quelle -> Download anbieten
    st.download_button(
        label="Geaenderte JSON herunterladen",
        data=dumps_json(data),
        file_name="data.edited.json",
        mime="application/json",
        disabled=not edit_mode
    )