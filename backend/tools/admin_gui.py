# admin_full_gui.py
# Vollstaendige Admin-GUI fuer dein Habit-Backend (Tkinter)
# Python 3.9+ ; benötigt: requests  (pip install requests)

import json
import os
from datetime import datetime
from typing import Optional, Any, Dict, List, Tuple

import tkinter as tk
from tkinter import ttk, messagebox

try:
    import requests
except ImportError:
    raise SystemExit("Bitte zuerst installieren: pip install requests")


# ---------------------------
# Helpers
# ---------------------------

def local_tz_offset_minutes() -> int:
    # lokale Zeit minus UTC in Minuten
    return int(round((datetime.now() - datetime.utcnow()).total_seconds() / 60.0))

def join_url(base: str, path: str) -> str:
    if not base.endswith("/"):
        base += "/"
    if path.startswith("/"):
        path = path[1:]
    return base + path

def auth_headers(token: Optional[str], sending_json: bool = False) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if sending_json:
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def try_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}

def fetch_json(method: str, url: str, token: Optional[str], params=None, json_body=None, timeout=30):
    try:
        resp = requests.request(
            method,
            url,
            headers=auth_headers(token, sending_json=json_body is not None),
            params=params,
            json=json_body,
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        return None, {"error": f"Network error: {e}"}
    if 200 <= resp.status_code < 300:
        return try_json(resp), None
    return None, {"error": f"HTTP {resp.status_code}", "details": try_json(resp)}

def pick_list(payload: Any) -> List[Dict[str, Any]]:
    """Akzeptiert Listen oder {data:[...]}-Strukturen."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "rows"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []

def safe_int(s: str) -> Optional[int]:
    try:
        return int(s.strip())
    except Exception:
        return None

def jdump(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


# ---------------------------
# API Wrapper
# ---------------------------

class API:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base = base_url
        self.token = token

    # --- Auth ---
    def register(self, vorname: str, name: str, email: str, passwort: str, avatar: Optional[str]):
        body = {"vorname": vorname or None, "name": name, "email": email, "passwort": passwort, "avatar": avatar or None}
        url = join_url(self.base, "/register")
        return fetch_json("POST", url, None, json_body=body)

    def login(self, email: str, password: str):
        body = {"email": email, "passwort": password}
        url = join_url(self.base, "/login")
        data, err = fetch_json("POST", url, None, json_body=body)
        if not err and isinstance(data, dict) and (data.get("token") or data.get("accessToken")):
            return data, None
        # fallback /auth/login
        url2 = join_url(self.base, "/auth/login")
        data2, err2 = fetch_json("POST", url2, None, json_body=body)
        if not err2:
            return data2, None
        return None, err or err2 or {"error": "login_failed"}

    def me(self):
        url = join_url(self.base, "/me")
        return fetch_json("GET", url, self.token)

    def health(self):
        url = join_url(self.base, "/health")
        return fetch_json("GET", url, None)

    # --- Users ---
    def users(self):
        url = join_url(self.base, "/users")
        return fetch_json("GET", url, self.token)

    def user_detail(self, uid: int):
        url = join_url(self.base, f"/users/{uid}")
        return fetch_json("GET", url, self.token)

    def users_bulk(self, ids: List[int]):
        url = join_url(self.base, "/users/bulk")
        params = {"ids": ",".join(map(str, ids))}
        return fetch_json("GET", url, self.token, params=params)

    # --- Friends ---
    def friends(self):
        url = join_url(self.base, "/friends")
        return fetch_json("GET", url, self.token)

    def friend_requests(self, direction: str):
        url = join_url(self.base, "/friends/requests")
        params = {"direction": direction}
        return fetch_json("GET", url, self.token, params=params)

    def send_friend_request(self, to_user_id: int, message: Optional[str]):
        url = join_url(self.base, "/friends/requests")
        body = {"toUserId": to_user_id, "message": message}
        return fetch_json("POST", url, self.token, json_body=body)

    def accept_friend_request(self, rid: int):
        url = join_url(self.base, f"/friends/requests/{rid}/accept")
        return fetch_json("POST", url, self.token)

    def decline_friend_request(self, rid: int):
        url = join_url(self.base, f"/friends/requests/{rid}/decline")
        return fetch_json("POST", url, self.token)

    # --- Challenges ---
    def challenges(self, with_today: bool, tz_min: Optional[int]):
        url = join_url(self.base, "/challenges")
        params = {}
        if with_today:
            params["withToday"] = "true"
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
        return fetch_json("GET", url, self.token, params=params)

    def challenge_detail(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}")
        return fetch_json("GET", url, self.token)

    def challenge_members(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}/members")
        return fetch_json("GET", url, self.token)

    def challenge_activity(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}/activity")
        return fetch_json("GET", url, self.token)

    def create_challenge(self, name: str, beschreibung: Optional[str], days_of_week: List[int],
                         start_at: Optional[int], dauer_tage: Optional[int], erlaubte_fails_tage: Optional[int],
                         friends_to_add: Optional[List[int]]):
        url = join_url(self.base, "/challenges")
        body = {
            "name": name,
            "beschreibung": beschreibung or None,
            "faelligeWochentage": days_of_week,
            "startAt": start_at,
            "dauerTage": dauer_tage,
            "erlaubteFailsTage": erlaubte_fails_tage,
            "friendsToAdd": friends_to_add or None
        }
        return fetch_json("POST", url, self.token, json_body=body)

    def post_chat(self, cid: int, text: str):
        url = join_url(self.base, f"/challenges/{cid}/chat")
        body = {"text": text}
        return fetch_json("POST", url, self.token, json_body=body)

    def get_chat(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}/chat")
        return fetch_json("GET", url, self.token)

    def confirm(self, cid: int, image_url: str, caption: Optional[str], visibility: str,
                date: Optional[str], tz_min: Optional[int], timestamp: Optional[int]):
        url = join_url(self.base, f"/challenges/{cid}/confirm")
        params = {}
        if date:
            params["date"] = date  # YYYY-MM-DD
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
        body = {"imageUrl": image_url, "caption": caption or None, "visibility": visibility or "freunde"}
        if timestamp is not None:
            body["timestamp"] = timestamp
        return fetch_json("POST", url, self.token, params=params, json_body=body)

    def leave_challenge(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}/leave")
        return fetch_json("POST", url, self.token)

    # Invites
    def list_challenge_invites(self, direction: str):
        url = join_url(self.base, "/challenges/invites")
        params = {"direction": direction}
        return fetch_json("GET", url, self.token, params=params)

    def send_challenge_invite(self, cid: int, to_user_id: int, message: Optional[str]):
        url = join_url(self.base, f"/challenges/{cid}/invites")
        body = {"toUserId": to_user_id, "message": message}
        return fetch_json("POST", url, self.token, json_body=body)

    def accept_challenge_invite(self, rid: int):
        url = join_url(self.base, f"/challenges/invites/{rid}/accept")
        return fetch_json("POST", url, self.token)

    def decline_challenge_invite(self, rid: int):
        url = join_url(self.base, f"/challenges/invites/{rid}/decline")
        return fetch_json("POST", url, self.token)

    # Stats / Blocked / Today / Fail Logs
    def challenge_stats(self, cid: int, tz_min: Optional[int]):
        url = join_url(self.base, f"/challenges/{cid}/stats")
        params = {}
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
        return fetch_json("GET", url, self.token, params=params)

    def challenge_stats_recalc(self, cid: int, tz_min: Optional[int]):
        url = join_url(self.base, f"/challenges/{cid}/stats/recalc")
        params = {}
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
        return fetch_json("POST", url, self.token, params=params)

    def challenge_blocked(self, cid: int, tz_min: Optional[int]):
        url = join_url(self.base, f"/challenges/{cid}/blocked")
        params = {}
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
        return fetch_json("GET", url, self.token, params=params)

    def challenge_today_status(self, cid: int, tz_min: Optional[int]):
        url = join_url(self.base, f"/challenges/{cid}/today-status")
        params = {}
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
        return fetch_json("GET", url, self.token, params=params)

    def challenge_fail_logs(self, cid: int, tz_min: Optional[int], user_id: Optional[int], frm: Optional[str], to: Optional[str]):
        url = join_url(self.base, f"/challenges/{cid}/logs/fails")
        params = {"tzOffsetMinutes": str(tz_min or 0)}
        if user_id is not None:
            params["userId"] = str(user_id)
        if frm:
            params["from"] = frm  # YYYY-MM-DD
        if to:
            params["to"] = to
        return fetch_json("GET", url, self.token, params=params)

    # Feed
    def feed(self):
        url = join_url(self.base, "/feed")
        return fetch_json("GET", url, self.token)

    # Notifications
    def notifications(self):
        url = join_url(self.base, "/notifications")
        return fetch_json("GET", url, self.token)

    def mark_notification_read(self, nid: int):
        url = join_url(self.base, f"/notifications/{nid}/read")
        return fetch_json("POST", url, self.token)

    # Admin
    def run_daily_all(self, tz_min: Optional[int]):
        candidates = ["/admin/run-daily-stats", "/admin/update-daily-stats"]
        params, body = {}, {}
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
            body["tzOffsetMinutes"] = tz_min
        last_err = None
        for path in candidates:
            url = join_url(self.base, path)
            data, err = fetch_json("POST", url, self.token, params=params, json_body=body)
            if not err:
                return data, None
            last_err = err
        return None, last_err or {"error": "no_admin_endpoint"}

    def run_daily_one(self, cid: int, tz_min: Optional[int]):
        candidates = [
            f"/admin/challenges/{cid}/run-daily-stats",
            f"/admin/challenges/{cid}/update-daily-stats",
        ]
        params, body = {}, {}
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
            body["tzOffsetMinutes"] = tz_min
        last_err = None
        for path in candidates:
            url = join_url(self.base, path)
            data, err = fetch_json("POST", url, self.token, params=params, json_body=body)
            if not err:
                return data, None
            last_err = err
        return None, last_err or {"error": "no_admin_endpoint"}


# ---------------------------
# GUI
# ---------------------------

class AdminGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Habit Admin GUI")
        self.geometry("1300x800")

        # State
        self.api: Optional[API] = None
        self.tz_min = local_tz_offset_minutes()
        self.challenges_cache: List[Dict[str, Any]] = []
        self.users_cache: List[Dict[str, Any]] = []

        # Header + Tabs + Output
        self._build_header()
        self._build_tabs()
        self._build_output()

        # Defaults
        self.base_var.set(os.environ.get("HABIT_BASE_URL", "http://127.0.0.1:8000"))
        self.token_var.set(os.environ.get("HABIT_JWT", ""))
        self.email_var.set("")
        self.pass_var.set("")
        self.tz_var.set(str(self.tz_min))

    # ---------- UI Builder ----------

    def _build_header(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill=tk.X, padx=10, pady=8)

        self.base_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.tz_var = tk.StringVar()

        # Row 1
        ttk.Label(wrap, text="Base URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(wrap, textvariable=self.base_var, width=46).grid(row=0, column=1, sticky="we", padx=6)

        ttk.Label(wrap, text="Token:").grid(row=0, column=2, sticky="w")
        ttk.Entry(wrap, textvariable=self.token_var, width=46, show="•").grid(row=0, column=3, sticky="we", padx=6)

        ttk.Label(wrap, text="tzOffsetMinutes:").grid(row=0, column=4, sticky="e")
        ttk.Entry(wrap, textvariable=self.tz_var, width=8).grid(row=0, column=5, sticky="w")

        # Row 2 (Auth)
        ttk.Label(wrap, text="Email:").grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Entry(wrap, textvariable=self.email_var, width=46).grid(row=1, column=1, sticky="we", padx=6, pady=(6,0))

        ttk.Label(wrap, text="Passwort:").grid(row=1, column=2, sticky="w", pady=(6,0))
        ttk.Entry(wrap, textvariable=self.pass_var, width=46, show="•").grid(row=1, column=3, sticky="we", padx=6, pady=(6,0))

        ttk.Button(wrap, text="Login", command=self.on_login).grid(row=1, column=4, sticky="we", padx=(6,0), pady=(6,0))
        ttk.Button(wrap, text="Me", command=self.on_me).grid(row=1, column=5, sticky="we", pady=(6,0))

        ttk.Button(wrap, text="Health", command=self.on_health).grid(row=0, column=6, sticky="we", padx=(6,0))
        ttk.Button(wrap, text="Register", command=self.on_register_dialog).grid(row=1, column=6, sticky="we", padx=(6,0), pady=(6,0))

        for c in range(7):
            wrap.columnconfigure(c, weight=1)

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,8))

        # Users
        self.tab_users = ttk.Frame(self.tabs); self.tabs.add(self.tab_users, text="Users")
        self._build_users_tab(self.tab_users)

        # Friends
        self.tab_friends = ttk.Frame(self.tabs); self.tabs.add(self.tab_friends, text="Friends")
        self._build_friends_tab(self.tab_friends)

        # Challenges
        self.tab_ch = ttk.Frame(self.tabs); self.tabs.add(self.tab_ch, text="Challenges")
        self._build_challenges_tab(self.tab_ch)

        # Challenge: Details/Actions
        self.tab_ch_actions = ttk.Frame(self.tabs); self.tabs.add(self.tab_ch_actions, text="Challenge Actions")
        self._build_challenge_actions_tab(self.tab_ch_actions)

        # Invites
        self.tab_invites = ttk.Frame(self.tabs); self.tabs.add(self.tab_invites, text="Invites")
        self._build_invites_tab(self.tab_invites)

        # Feed
        self.tab_feed = ttk.Frame(self.tabs); self.tabs.add(self.tab_feed, text="Feed")
        self._build_feed_tab(self.tab_feed)

        # Notifications
        self.tab_notif = ttk.Frame(self.tabs); self.tabs.add(self.tab_notif, text="Notifications")
        self._build_notifications_tab(self.tab_notif)

        # Admin
        self.tab_admin = ttk.Frame(self.tabs); self.tabs.add(self.tab_admin, text="Admin")
        self._build_admin_tab(self.tab_admin)

    def _build_output(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0,10))
        ttk.Label(wrap, text="JSON Output").pack(anchor="w")
        self.txt = tk.Text(wrap, wrap="none", height=12)
        y = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.txt.yview)
        self.txt.configure(yscrollcommand=y.set)
        self.txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y.pack(side=tk.RIGHT, fill=tk.Y)

    def set_json(self, payload: Any):
        self.txt.config(state="normal")
        self.txt.delete("1.0", tk.END)
        self.txt.insert("1.0", jdump(payload))
        self.txt.config(state="disabled")

    # ---------- Tabs ----------

    def _build_users_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="List Users", command=self.on_users).pack(side=tk.LEFT)
        ttk.Button(bar, text="Bulk (IDs 1,2,3)", command=self.on_users_bulk_demo).pack(side=tk.LEFT, padx=6)

        self.tbl_users = ttk.Treeview(root, columns=["id","name","email"], show="headings", height=18)
        for c,w in zip(["id","name","email"], [80,220,260]):
            self.tbl_users.heading(c, text=c)
            self.tbl_users.column(c, width=w, stretch=True)
        self.tbl_users.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_friends_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)

        ttk.Button(bar, text="List Friends", command=self.on_friends).pack(side=tk.LEFT)
        ttk.Button(bar, text="Requests Incoming", command=lambda: self.on_friend_requests("incoming")).pack(side=tk.LEFT, padx=6)
        ttk.Button(bar, text="Requests Outgoing", command=lambda: self.on_friend_requests("outgoing")).pack(side=tk.LEFT)

        ttk.Label(bar, text="Request-ID:").pack(side=tk.LEFT, padx=(12,2))
        self.fr_req_id = tk.StringVar()
        ttk.Entry(bar, textvariable=self.fr_req_id, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Accept", command=self.on_accept_friend_request).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Decline", command=self.on_decline_friend_request).pack(side=tk.LEFT, padx=3)

        ttk.Label(bar, text="Send to userId:").pack(side=tk.LEFT, padx=(12,2))
        self.fr_to_uid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.fr_to_uid, width=8).pack(side=tk.LEFT)
        self.fr_msg = tk.StringVar()
        ttk.Entry(bar, textvariable=self.fr_msg, width=24).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Send Request", command=self.on_send_friend_request).pack(side=tk.LEFT)

        self.tbl_friends = ttk.Treeview(root, columns=["id","fromUserId","toUserId","status","createdAt","message"], show="headings", height=18)
        for c,w in zip(["id","fromUserId","toUserId","status","createdAt","message"], [60,100,100,120,160,320]):
            self.tbl_friends.heading(c, text=c)
            self.tbl_friends.column(c, width=w, stretch=True)
        self.tbl_friends.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_challenges_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Load Challenges", command=self.on_load_challenges).pack(side=tk.LEFT)
        ttk.Button(bar, text="Refresh Auswahl", command=self.on_refresh_ch_selection).pack(side=tk.LEFT, padx=6)

        ttk.Label(bar, text="withToday").pack(side=tk.LEFT, padx=(12,2))
        self.with_today_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, variable=self.with_today_var).pack(side=tk.LEFT)
        ttk.Label(bar, text="tzOffsetMinutes").pack(side=tk.LEFT, padx=(12,2))
        self.ch_tz_var = tk.StringVar(value="")
        ttk.Entry(bar, textvariable=self.ch_tz_var, width=8).pack(side=tk.LEFT)

        ttk.Button(bar, text="Create Challenge", command=self.on_create_challenge_dialog).pack(side=tk.LEFT, padx=12)

        self.tbl_ch = ttk.Treeview(root, columns=["id","name","today.status","today.pending","blocked"], show="headings", height=18)
        for c,w in zip(["id","name","today.status","today.pending","blocked"], [80,260,140,120,100]):
            self.tbl_ch.heading(c, text=c)
            self.tbl_ch.column(c, width=w, stretch=True)
        self.tbl_ch.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_challenge_actions_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=(6,0))

        ttk.Label(bar, text="cid:").pack(side=tk.LEFT)
        self.sel_cid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.sel_cid, width=8).pack(side=tk.LEFT, padx=(4,8))

        ttk.Button(bar, text="Detail", command=self.on_ch_detail).pack(side=tk.LEFT)
        ttk.Button(bar, text="Members", command=self.on_ch_members).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Activity", command=self.on_ch_activity).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Chat (get)", command=self.on_ch_chat_get).pack(side=tk.LEFT, padx=4)

        # Chat send
        self.chat_text_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.chat_text_var, width=24).pack(side=tk.LEFT, padx=(12,3))
        ttk.Button(bar, text="Chat (send)", command=self.on_ch_chat_send).pack(side=tk.LEFT, padx=2)

        # Confirm
        row2 = ttk.Frame(root); row2.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(row2, text="imageUrl:").pack(side=tk.LEFT)
        self.confirm_img = tk.StringVar()
        ttk.Entry(row2, textvariable=self.confirm_img, width=40).pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="caption:").pack(side=tk.LEFT)
        self.confirm_cap = tk.StringVar()
        ttk.Entry(row2, textvariable=self.confirm_cap, width=24).pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="visibility:").pack(side=tk.LEFT)
        self.confirm_vis = tk.StringVar(value="freunde")
        ttk.Combobox(row2, textvariable=self.confirm_vis, values=["freunde","privat"], width=10).pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="date (YYYY-MM-DD):").pack(side=tk.LEFT, padx=(12,2))
        self.confirm_date = tk.StringVar()
        ttk.Entry(row2, textvariable=self.confirm_date, width=12).pack(side=tk.LEFT)

        ttk.Label(row2, text="tzOffsetMinutes:").pack(side=tk.LEFT, padx=(12,2))
        self.confirm_tz = tk.StringVar()
        ttk.Entry(row2, textvariable=self.confirm_tz, width=8).pack(side=tk.LEFT)

        ttk.Label(row2, text="timestamp (ms):").pack(side=tk.LEFT, padx=(12,2))
        self.confirm_ts = tk.StringVar()
        ttk.Entry(row2, textvariable=self.confirm_ts, width=14).pack(side=tk.LEFT)

        ttk.Button(row2, text="Confirm posten", command=self.on_confirm_post).pack(side=tk.LEFT, padx=10)

        # Stats/Blocked/Today/Fail Logs
        row3 = ttk.Frame(root); row3.pack(fill=tk.X, padx=6, pady=(0,6))
        ttk.Button(row3, text="Stats", command=self.on_ch_stats).pack(side=tk.LEFT)
        ttk.Button(row3, text="Stats Recalc", command=self.on_ch_stats_recalc).pack(side=tk.LEFT, padx=6)
        ttk.Button(row3, text="Blocked", command=self.on_ch_blocked).pack(side=tk.LEFT)
        ttk.Button(row3, text="Today-Status", command=self.on_ch_today_status).pack(side=tk.LEFT, padx=6)

        ttk.Label(row3, text="Fails from:").pack(side=tk.LEFT, padx=(12,2))
        self.fail_from = tk.StringVar()
        ttk.Entry(row3, textvariable=self.fail_from, width=12).pack(side=tk.LEFT)
        ttk.Label(row3, text="to:").pack(side=tk.LEFT, padx=(6,2))
        self.fail_to = tk.StringVar()
        ttk.Entry(row3, textvariable=self.fail_to, width=12).pack(side=tk.LEFT)
        ttk.Label(row3, text="userId:").pack(side=tk.LEFT, padx=(6,2))
        self.fail_uid = tk.StringVar()
        ttk.Entry(row3, textvariable=self.fail_uid, width=8).pack(side=tk.LEFT)
        ttk.Button(row3, text="Fail Logs", command=self.on_ch_fail_logs).pack(side=tk.LEFT, padx=6)

        ttk.Button(row3, text="Leave Challenge", command=self.on_leave_challenge).pack(side=tk.LEFT, padx=12)

    def _build_invites_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Invites Incoming", command=lambda: self.on_invites("incoming")).pack(side=tk.LEFT)
        ttk.Button(bar, text="Invites Outgoing", command=lambda: self.on_invites("outgoing")).pack(side=tk.LEFT, padx=6)

        ttk.Label(bar, text="cid:").pack(side=tk.LEFT, padx=(12,2))
        self.inv_cid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.inv_cid, width=8).pack(side=tk.LEFT)

        ttk.Label(bar, text="toUserId:").pack(side=tk.LEFT, padx=(8,2))
        self.inv_to_uid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.inv_to_uid, width=8).pack(side=tk.LEFT)

        self.inv_msg = tk.StringVar()
        ttk.Entry(bar, textvariable=self.inv_msg, width=24).pack(side=tk.LEFT, padx=6)

        ttk.Button(bar, text="Invite senden", command=self.on_invite_send).pack(side=tk.LEFT, padx=6)

        ttk.Label(bar, text="inviteId:").pack(side=tk.LEFT, padx=(12,2))
        self.inv_id = tk.StringVar()
        ttk.Entry(bar, textvariable=self.inv_id, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Accept", command=self.on_invite_accept).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Decline", command=self.on_invite_decline).pack(side=tk.LEFT, padx=3)

        self.tbl_inv = ttk.Treeview(root, columns=["id","challengeId","fromUserId","toUserId","status","message","createdAt"], show="headings", height=18)
        for c,w in zip(["id","challengeId","fromUserId","toUserId","status","message","createdAt"], [60,90,90,90,90,320,140]):
            self.tbl_inv.heading(c, text=c)
            self.tbl_inv.column(c, width=w, stretch=True)
        self.tbl_inv.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_feed_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Load Feed", command=self.on_feed).pack(side=tk.LEFT)
        self.tbl_feed = ttk.Treeview(root, columns=["id","action","userId","timestamp","caption","imageUrl"], show="headings", height=18)
        for c,w in zip(["id","action","userId","timestamp","caption","imageUrl"], [60,90,80,140,300,380]):
            self.tbl_feed.heading(c, text=c)
            self.tbl_feed.column(c, width=w, stretch=True)
        self.tbl_feed.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_notifications_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Load Notifications", command=self.on_notif).pack(side=tk.LEFT)
        ttk.Label(bar, text="notif id:").pack(side=tk.LEFT, padx=(12,2))
        self.notif_id = tk.StringVar()
        ttk.Entry(bar, textvariable=self.notif_id, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Mark Read", command=self.on_notif_read).pack(side=tk.LEFT, padx=6)

        self.tbl_notif = ttk.Treeview(root, columns=["id","userId","text","read","createdAt"], show="headings", height=18)
        for c,w in zip(["id","userId","text","read","createdAt"], [60,80,420,80,160]):
            self.tbl_notif.heading(c, text=c)
            self.tbl_notif.column(c, width=w, stretch=True)
        self.tbl_notif.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_admin_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Daily Update (ALLE)", command=self.on_update_all).pack(side=tk.LEFT)
        ttk.Label(bar, text="cid:").pack(side=tk.LEFT, padx=(12,2))
        self.admin_cid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.admin_cid, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Daily Update (ONE)", command=self.on_update_one).pack(side=tk.LEFT, padx=6)

    # ---------- Utilities ----------

    def _get_api(self) -> API:
        base = self.base_var.get().strip()
        token = self.token_var.get().strip() or None
        if not base:
            raise RuntimeError("Bitte Base URL eingeben.")
        if not self.api or self.api.base != base or self.api.token != token:
            self.api = API(base, token)
        return self.api

    def _tz(self) -> Optional[int]:
        s = self.tz_var.get().strip()
        if not s:
            return None
        return safe_int(s)

    def _fill_tree(self, tree: ttk.Treeview, rows: List[Dict[str, Any]], columns: List[str]):
        tree["columns"] = columns
        for c in columns:
            tree.heading(c, text=c)
            tree.column(c, width=max(80, int(1000/len(columns))), stretch=True)
        tree.delete(*tree.get_children())
        for r in rows:
            vals = [self._flatten_get(r, c) for c in columns]
            tree.insert("", tk.END, values=vals)

    def _flatten_get(self, obj: Dict[str, Any], dotted: str):
        cur = obj
        for part in dotted.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur

    # ---------- Handlers: Header ----------

    def on_login(self):
        try:
            base = self.base_var.get().strip()
            email = self.email_var.get().strip()
            pw = self.pass_var.get().strip()
            if not base or not email or not pw:
                messagebox.showwarning("Hinweis", "Bitte Base URL, Email und Passwort eingeben.")
                return
            tmp_api = API(base)
            data, err = tmp_api.login(email, pw)
            if err:
                messagebox.showerror("Login fehlgeschlagen", jdump(err))
                return
            token = (data or {}).get("token") or (data or {}).get("accessToken")
            if not token:
                messagebox.showerror("Login fehlgeschlagen", "Kein Token erhalten")
                return
            self.token_var.set(token)
            self.api = API(base, token)
            messagebox.showinfo("Login", f"Login erfolgreich fuer {email}")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def on_me(self):
        try:
            api = self._get_api()
            data, err = api.me()
            self.set_json(data or err)
        except Exception as e:
            self.set_json({"error": str(e)})

    def on_health(self):
        try:
            api = self._get_api()
            data, err = api.health()
            self.set_json(data or err)
        except Exception as e:
            self.set_json({"error": str(e)})

    def on_register_dialog(self):
        win = tk.Toplevel(self); win.title("Register"); win.geometry("420x260")
        v_vn = tk.StringVar(); v_n = tk.StringVar(); v_e = tk.StringVar(); v_p = tk.StringVar(); v_a = tk.StringVar()
        frm = ttk.Frame(win); frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for i,(lbl,var) in enumerate([("Vorname",v_vn),("Name",v_n),("Email",v_e),("Passwort",v_p),("Avatar(URL)",v_a)]):
            ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky="e", pady=4)
            show = "•" if lbl=="Passwort" else None
            ttk.Entry(frm, textvariable=var, show=show).grid(row=i, column=1, sticky="we", pady=4)
        frm.columnconfigure(1, weight=1)
        def do_reg():
            try:
                api = self._get_api()
                data, err = api.register(v_vn.get(), v_n.get(), v_e.get(), v_p.get(), v_a.get())
                self.set_json(data or err)
                if data and data.get("token"):
                    self.token_var.set(data["token"])
                    self.api = API(self.base_var.get().strip(), data["token"])
                    messagebox.showinfo("OK", "Registrierung + Auto-Login erfolgreich")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Fehler", str(e))
        ttk.Button(frm, text="Registrieren", command=do_reg).grid(row=5, column=0, columnspan=2, pady=8)

    # ---------- Users ----------

    def on_users(self):
        try:
            api = self._get_api()
            data, err = api.users()
            if err:
                self.set_json(err); return
            rows = pick_list(data) if isinstance(data, list) else data
            if isinstance(rows, dict) and "users" in rows:
                rows = rows["users"]
            if not isinstance(rows, list):
                rows = []
            self.users_cache = rows
            self._fill_tree(self.tbl_users, rows, ["id","name","email"])
            self.set_json(rows)
        except Exception as e:
            self.set_json({"error": str(e)})

    def on_users_bulk_demo(self):
        ids = [1,2,3]
        try:
            api = self._get_api()
            data, err = api.users_bulk(ids)
            self.set_json(data or err)
        except Exception as e:
            self.set_json({"error": str(e)})

    # ---------- Friends ----------

    def on_friends(self):
        try:
            api = self._get_api()
            data, err = api.friends()
            rows = pick_list(data) if not err else []
            self._fill_tree(self.tbl_friends, rows, ["id","fromUserId","toUserId","status","createdAt","message"])
            self.set_json(data or err)
        except Exception as e:
            self.set_json({"error": str(e)})

    def on_friend_requests(self, direction: str):
        try:
            api = self._get_api()
            data, err = api.friend_requests(direction)
            rows = pick_list(data) if not err else []
            self._fill_tree(self.tbl_friends, rows, ["id","fromUserId","toUserId","status","createdAt","message"])
            self.set_json(data or err)
        except Exception as e:
            self.set_json({"error": str(e)})

    def on_accept_friend_request(self):
        rid = safe_int(self.fr_req_id.get() or "")
        if not rid:
            messagebox.showwarning("Hinweis","request id fehlt"); return
        api = self._get_api()
        data, err = api.accept_friend_request(rid)
        self.set_json(data or err)

    def on_decline_friend_request(self):
        rid = safe_int(self.fr_req_id.get() or "")
        if not rid:
            messagebox.showwarning("Hinweis","request id fehlt"); return
        api = self._get_api()
        data, err = api.decline_friend_request(rid)
        self.set_json(data or err)

    def on_send_friend_request(self):
        uid = safe_int(self.fr_to_uid.get() or "")
        if not uid:
            messagebox.showwarning("Hinweis","toUserId fehlt"); return
        api = self._get_api()
        data, err = api.send_friend_request(uid, self.fr_msg.get() or None)
        self.set_json(data or err)

    # ---------- Challenges ----------

    def on_load_challenges(self):
        try:
            api = self._get_api()
            with_today = self.with_today_var.get()
            tz = safe_int(self.ch_tz_var.get().strip()) if self.ch_tz_var.get().strip() else self._tz()
            data, err = api.challenges(with_today, tz)
            if err:
                self.set_json(err); return
            rows = pick_list(data) if isinstance(data, list) else data
            if not isinstance(rows, list):
                rows = []
            self.challenges_cache = rows
            # Spalten
            for r in rows:
                r.setdefault("today", {})
            self._fill_tree(self.tbl_ch, rows, ["id","name","today.status","today.pending","blocked"])
            self.set_json(rows)
        except Exception as e:
            self.set_json({"error": str(e)})

    def on_refresh_ch_selection(self):
        sel = self.tbl_ch.selection()
        if not sel:
            self.on_load_challenges()
            return
        self.on_load_challenges()

    def on_create_challenge_dialog(self):
        win = tk.Toplevel(self); win.title("Create Challenge"); win.geometry("520x380")
        v_name = tk.StringVar(); v_desc = tk.StringVar(); v_days = tk.StringVar(value="1,2,3,4,5")
        v_start = tk.StringVar(); v_dauer = tk.StringVar(); v_fails = tk.StringVar(); v_friends = tk.StringVar()

        frm = ttk.Frame(win); frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        rows = [
            ("Name", v_name),
            ("Beschreibung", v_desc),
            ("Wochentage (z. B. 1,2,3,4,5)", v_days),
            ("startAt (ms, optional)", v_start),
            ("dauerTage (optional)", v_dauer),
            ("erlaubteFailsTage (optional)", v_fails),
            ("friendsToAdd (userIds, optional: 2,3)", v_friends),
        ]
        for i,(lbl,var) in enumerate(rows):
            ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky="e", pady=4)
            ttk.Entry(frm, textvariable=var).grid(row=i, column=1, sticky="we", pady=4)
        frm.columnconfigure(1, weight=1)

        def parse_int_list(s: str) -> List[int]:
            out = []
            for part in s.split(","):
                part = part.strip()
                if not part: continue
                try: out.append(int(part))
                except: pass
            return out

        def do_create():
            try:
                api = self._get_api()
                name = v_name.get().strip()
                if not name:
                    messagebox.showwarning("Hinweis","Name fehlt"); return
                days = parse_int_list(v_days.get())
                start_at = safe_int(v_start.get()) if v_start.get().strip() else None
                dauer = safe_int(v_dauer.get()) if v_dauer.get().strip() else None
                fails = safe_int(v_fails.get()) if v_fails.get().strip() else None
                friends = parse_int_list(v_friends.get()) if v_friends.get().strip() else None
                data, err = api.create_challenge(name, v_desc.get() or None, days, start_at, dauer, fails, friends)
                self.set_json(data or err)
                if not err:
                    messagebox.showinfo("OK","Challenge erstellt")
                    self.on_load_challenges()
                win.destroy()
            except Exception as e:
                messagebox.showerror("Fehler", str(e))

        ttk.Button(frm, text="Erstellen", command=do_create).grid(row=len(rows), column=0, columnspan=2, pady=10)

    # ---------- Challenge Actions ----------

    def _cid(self) -> Optional[int]:
        s = self.sel_cid.get().strip()
        if not s:
            # falls aus Tabelle selektiert
            sel = self.tbl_ch.selection()
            if sel:
                try:
                    # erste Spalte der values ist id
                    vals = self.tbl_ch.item(sel[0], "values")
                    if vals:
                        return int(vals[0])
                except Exception:
                    pass
            return None
        return safe_int(s)

    def on_ch_detail(self):
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.challenge_detail(cid)
        self.set_json(data or err)

    def on_ch_members(self):
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.challenge_members(cid)
        self.set_json(data or err)

    def on_ch_activity(self):
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.challenge_activity(cid)
        self.set_json(data or err)

    def on_ch_chat_get(self):
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.get_chat(cid)
        self.set_json(data or err)

    def on_ch_chat_send(self):
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt"); return
        txt = self.chat_text_var.get().strip()
        if not txt:
            messagebox.showwarning("Hinweis","Chat-Text fehlt"); return
        api = self._get_api()
        data, err = api.post_chat(cid, txt)
        self.set_json(data or err)
        if not err:
            self.chat_text_var.set("")
            self.on_ch_chat_get()

    def on_confirm_post(self):
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt"); return
        image_url = self.confirm_img.get().strip()
        if not image_url:
            messagebox.showwarning("Hinweis","imageUrl fehlt"); return
        caption = self.confirm_cap.get().strip() or None
        vis = self.confirm_vis.get().strip() or "freunde"
        date = self.confirm_date.get().strip() or None
        tz = self.confirm_tz.get().strip()
        tz_min = safe_int(tz) if tz else self._tz()
        ts = safe_int(self.confirm_ts.get().strip()) if self.confirm_ts.get().strip() else None
        api = self._get_api()
        data, err = api.confirm(cid, image_url, caption, vis, date, tz_min, ts)
        self.set_json(data or err)

    def on_ch_stats(self):
        cid = self._cid(); 
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        tz = self._tz()
        api = self._get_api()
        data, err = api.challenge_stats(cid, tz)
        self.set_json(data or err)

    def on_ch_stats_recalc(self):
        cid = self._cid(); 
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        tz = self._tz()
        api = self._get_api()
        data, err = api.challenge_stats_recalc(cid, tz)
        self.set_json(data or err)

    def on_ch_blocked(self):
        cid = self._cid(); 
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        tz = self._tz()
        api = self._get_api()
        data, err = api.challenge_blocked(cid, tz)
        self.set_json(data or err)

    def on_ch_today_status(self):
        cid = self._cid(); 
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        tz = self._tz()
        api = self._get_api()
        data, err = api.challenge_today_status(cid, tz)
        self.set_json(data or err)

    def on_ch_fail_logs(self):
        cid = self._cid(); 
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        tz = self._tz()
        uid = safe_int(self.fail_uid.get().strip()) if self.fail_uid.get().strip() else None
        frm = self.fail_from.get().strip() or None
        to = self.fail_to.get().strip() or None
        api = self._get_api()
        data, err = api.challenge_fail_logs(cid, tz, uid, frm, to)
        self.set_json(data or err)

    def on_leave_challenge(self):
        cid = self._cid(); 
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.leave_challenge(cid)
        self.set_json(data or err)

    # ---------- Invites ----------

    def on_invites(self, direction: str):
        api = self._get_api()
        data, err = api.list_challenge_invites(direction)
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_inv, rows, ["id","challengeId","fromUserId","toUserId","status","message","createdAt"])
        self.set_json(data or err)

    def on_invite_send(self):
        cid = safe_int(self.inv_cid.get().strip() or "")
        uid = safe_int(self.inv_to_uid.get().strip() or "")
        if not cid or not uid:
            messagebox.showwarning("Hinweis","cid und toUserId erforderlich"); return
        api = self._get_api()
        data, err = api.send_challenge_invite(cid, uid, self.inv_msg.get().strip() or None)
        self.set_json(data or err)

    def on_invite_accept(self):
        rid = safe_int(self.inv_id.get().strip() or "")
        if not rid:
            messagebox.showwarning("Hinweis","inviteId erforderlich"); return
        api = self._get_api()
        data, err = api.accept_challenge_invite(rid)
        self.set_json(data or err)

    def on_invite_decline(self):
        rid = safe_int(self.inv_id.get().strip() or "")
        if not rid:
            messagebox.showwarning("Hinweis","inviteId erforderlich"); return
        api = self._get_api()
        data, err = api.decline_challenge_invite(rid)
        self.set_json(data or err)

    # ---------- Feed ----------

    def on_feed(self):
        api = self._get_api()
        data, err = api.feed()
        rows = pick_list(data) if not err else []
        # Extrahiere caption/imageUrl, falls unter evidence
        flat = []
        for it in rows:
            cap = None; img = None
            ev = it.get("evidence") if isinstance(it, dict) else None
            if isinstance(ev, dict):
                cap = ev.get("caption"); img = ev.get("imageUrl")
            flat.append({
                "id": it.get("id"),
                "action": it.get("action"),
                "userId": it.get("userId"),
                "timestamp": it.get("timestamp"),
                "caption": cap,
                "imageUrl": img
            })
        self._fill_tree(self.tbl_feed, flat, ["id","action","userId","timestamp","caption","imageUrl"])
        self.set_json(data or err)

    # ---------- Notifications ----------

    def on_notif(self):
        api = self._get_api()
        data, err = api.notifications()
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_notif, rows, ["id","userId","text","read","createdAt"])
        self.set_json(data or err)

    def on_notif_read(self):
        nid = safe_int(self.notif_id.get().strip() or "")
        if not nid:
            messagebox.showwarning("Hinweis","notif id fehlt"); return
        api = self._get_api()
        data, err = api.mark_notification_read(nid)
        self.set_json(data or err)

    # ---------- Admin ----------

    def on_update_all(self):
        api = self._get_api()
        data, err = api.run_daily_all(self._tz())
        self.set_json(data or err)

    def on_update_one(self):
        cid = safe_int(self.admin_cid.get().strip() or "")
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.run_daily_one(cid, self._tz())
        self.set_json(data or err)


# ---------------------------
# main
# ---------------------------

def main():
    app = AdminGUI()
    app.mainloop()

if __name__ == "__main__":
    main()