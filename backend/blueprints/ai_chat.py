# backend/blueprints/ai_chat.py
from flask import Blueprint, request, Response, current_app, stream_with_context
import requests, json
from typing import Generator, Optional, Dict, Any, List

from backend.common import store  # wir lesen nur aus dem Store

bp = Blueprint("ai_chat", __name__)

# ---------------------------
# Helpers
# ---------------------------

def _ollama_base() -> str:
    return current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")

def _extract_token(payload: Dict[str, Any]) -> Optional[str]:
    """Token aus Authorization, X-Auth-Token oder payload.token lesen."""
    auth_hdr = request.headers.get("Authorization") or ""
    x_token = request.headers.get("X-Auth-Token")
    body_token = payload.get("token")

    token = None
    if auth_hdr.lower().startswith("bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
    elif x_token:
        token = x_token.strip()
    elif body_token:
        token = str(body_token).strip()

    print(f"[AI_CHAT] Auth Header: {auth_hdr}")
    print(f"[AI_CHAT] X-Auth-Token: {x_token}")
    print(f"[AI_CHAT] Body.token: {body_token}")
    print(f"[AI_CHAT] -> Parsed token: {token!r}")
    return token

def _uid_from_token(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    st = store.state()
    uid = (st.get("auth", {}).get("tokens", {}) or {}).get(token)
    try:
        uid_i = int(uid) if uid is not None else None
    except Exception:
        uid_i = None
    print(f"[AI_CHAT] -> uid from token: {uid_i}")
    return uid_i

def _user_basic(st: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    u = (st.get("users", {}) or {}).get(str(user_id)) or {}
    basic = {
        "id": int(u.get("id", user_id)),
        "vorname": u.get("vorname"),
        "name": u.get("name"),
        "avatar": u.get("avatar"),
    }
    print(f"[AI_CHAT] User basic: {basic}")
    return basic

def _friends(st: Dict[str, Any], user_id: int) -> List[Dict[str, Any]]:
    res: List[Dict[str, Any]] = []
    for fr in st.get("friends", []) or []:
        if fr.get("status") != "accepted":
            continue
        a, b = fr.get("fromUserId"), fr.get("toUserId")
        other = b if a == user_id else (a if b == user_id else None)
        if other is None:
            continue
        res.append(_user_basic(st, int(other)))
    print(f"[AI_CHAT] Freunde count: {len(res)}")
    return res

def _user_challenge_ids(st: Dict[str, Any], user_id: int) -> List[int]:
    ids = []
    for m in st.get("challenge_members", []) or []:
        if m.get("userId") == user_id:
            try:
                ids.append(int(m.get("challengeId")))
            except Exception:
                pass
    print(f"[AI_CHAT] Challenge IDs: {ids}")
    return ids

def _challenge_meta(st: Dict[str, Any], ch_id: int) -> Dict[str, Any]:
    ch = (st.get("challenges", {}) or {}).get(str(ch_id)) or {}
    name = ch.get("name") or f"Challenge {ch_id}"
    dauer = ch.get("dauerTage")
    meta = {"name": name, "dauerTage": dauer}
    return meta

def _stats_from_challenge_stats(st: Dict[str, Any], ch_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    cs = (st.get("challenge_stats", {}) or {}).get(str(ch_id))
    if not cs:
        return None
    per = cs.get("perUser") or []
    mine = next((p for p in per if p.get("userId") == user_id), None)
    if not mine:
        return None
    conf = int(mine.get("confCount", 0))
    fail = int(mine.get("failCount", 0))
    streak = int(mine.get("streak", 0))
    today = str(mine.get("challenge_today_status", "unknown")).lower()
    status = str(mine.get("challenge_status", "none")).lower()
    total = cs.get("dauerTage")
    try:
        total_i = int(total) if total is not None else max(conf + fail, 1)
    except Exception:
        total_i = max(conf + fail, 1)
    return {
        "days_total": total_i,
        "days_done": conf,
        "fail_count": fail,
        "streak": streak,
        "today": today,
        "status": status,
    }

def _stats_from_logs_fallback(st: Dict[str, Any], ch_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    logs = ((st.get("challenge_user_logs", {}) or {}).get(str(ch_id), {}) or {}).get(str(user_id)) or []
    if not logs:
        return None
    last = logs[-1]
    conf = int(last.get("conf_count", 0))
    fail = int(last.get("fail_count", 0))
    streak = int(last.get("streak", 0))
    blocked = bool(last.get("blocked", False))
    state = str(last.get("state", "run")).lower()
    status = "blocked" if blocked else ("done" if state in ("done", "completed", "abgeschlossen") else "run")
    total = max(conf + fail, 1)
    return {
        "days_total": total,
        "days_done": conf,
        "fail_count": fail,
        "streak": streak,
        "today": "unknown",
        "status": status,
    }

def _user_stats_for_challenge(st: Dict[str, Any], ch_id: int, user_id: int) -> Dict[str, Any]:
    stt = _stats_from_challenge_stats(st, ch_id, user_id)
    if stt is None:
        stt = _stats_from_logs_fallback(st, ch_id, user_id)
    if stt is None:
        stt = {
            "days_total": 1,
            "days_done": 0,
            "fail_count": 0,
            "streak": 0,
            "today": "unknown",
            "status": "none",
        }
    return stt

def _build_user_context(st: Dict[str, Any], user_id: int, limit_challenges: Optional[int] = 10) -> Dict[str, Any]:
    basic = _user_basic(st, user_id)
    friends = _friends(st, user_id)
    ch_ids = _user_challenge_ids(st, user_id)
    if limit_challenges is not None:
        ch_ids = ch_ids[:limit_challenges]

    challenges: List[Dict[str, Any]] = []
    for cid in ch_ids:
        meta = _challenge_meta(st, cid)
        stt = _user_stats_for_challenge(st, cid, user_id)
        challenges.append({
            "id": cid,
            "name": meta["name"],
            "days_total": stt["days_total"],
            "days_done": stt["days_done"],
            "streak": stt["streak"],
            "fail_count": stt["fail_count"],
            "today": stt["today"],
            "status": stt["status"],
        })
        print(f"[AI_CHAT] Challenge {cid} '{meta['name']}' -> Stats: {stt}")

    ctx = {
        "type": "user_context_v1",
        "user": basic,
        "friends": friends,
        "challenges": challenges,
    }
    print(f"[AI_CHAT] Kontext gebaut: challenges={len(challenges)}, friends={len(friends)}")
    return ctx

def _context_system_message(ctx: Dict[str, Any]) -> Dict[str, Any]:
    # Diese Message macht es fuer das Modell explizit
    return {"role": "system", "content": "Server-Kontext:\n" + json.dumps(ctx, ensure_ascii=False)}

# ---------------------------
# Routes
# ---------------------------

@bp.post("/pull")
def pull_model():
    data = request.get_json(force=True) or {}
    model = data.get("model")
    if not model:
        return {"error": "Feld 'model' fehlt"}, 400

    base = _ollama_base()

    def _generator() -> Generator[bytes, None, None]:
        try:
            with requests.post(f"{base}/api/pull", json={"name": model}, stream=True, timeout=600) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        yield line + b"\n"
        except requests.RequestException as e:
            yield (json.dumps({"error": str(e)}).encode("utf-8") + b"\n")

    headers = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache", "Connection": "keep-alive"}
    return Response(stream_with_context(_generator()), mimetype="application/json", headers=headers)

@bp.post("/chat")
def chat():
    payload = request.get_json(force=True) or {}
    model = payload.get("model", "llama3.2:1b")
    messages = payload.get("messages", [])
    stream = bool(payload.get("stream", False))
    options = payload.get("options", {})
    no_context = bool(payload.get("no_context", False))
    debug_only = bool(payload.get("debug", False))

    if not messages:
        return {"error": "Feld 'messages' fehlt oder ist leer"}, 400

    # Token und User ermitteln
    token = _extract_token(payload)
    uid = _uid_from_token(token)

    # Kontext bauen und anhaengen
    st = store.state()
    ctx = None
    if uid is not None and not no_context:
        ctx = _build_user_context(st, uid, limit_challenges=10)
        messages = [_context_system_message(ctx)] + messages
    else:
        print("[AI_CHAT] Kein uid gefunden oder Kontext explizit deaktiviert; es wird kein Kontext angehaengt.")

    body = {"model": model, "messages": messages, "options": options, "stream": stream}
    base = _ollama_base()

    # Log: Zeige finalen Body (gekuerzt wenn zu lang)
    try:
        preview = json.dumps(body, ensure_ascii=False, indent=2)
        print("[AI_CHAT] === Sende an Ollama ===")
        print(preview if len(preview) < 4000 else preview[:4000] + "... [truncated]")
        print("================================")
    except Exception as e:
        print(f"[AI_CHAT] Fehler beim Dump des Forward-Bodys: {e}")

    # Debug: direkt zurueckgeben, was wir senden wuerden
    if debug_only:
        return {"has_token": bool(token), "user_id": uid, "context": ctx, "forward_body": body}

    if stream:
        def _sse() -> Generator[str, None, None]:
            try:
                # Kontext zunaechst als eigenes Event fuer den Client
                if ctx is not None:
                    yield f"event: context\ndata: {json.dumps(ctx, ensure_ascii=False)}\n\n"

                with requests.post(f"{base}/api/chat", json=body, stream=True, timeout=600) as r:
                    r.raise_for_status()
                    for raw in r.iter_lines():
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw.decode("utf-8"))
                        except Exception:
                            continue
                        yield f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"
            except requests.RequestException as e:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        headers = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache", "Connection": "keep-alive"}
        return Response(stream_with_context(_sse()), mimetype="text/event-stream", headers=headers)

    # non-stream
    try:
        r = requests.post(f"{base}/api/chat", json=body, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"error": str(e)}, 502