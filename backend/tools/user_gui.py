# user_gui.py
# User-GUI fuer dein Habit-Backend (Tkinter)
# Python 3.9+ ; benoetigt: requests  (pip install requests)

import json
import os
import time
from datetime import datetime
from typing import Optional, Any, Dict, List

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

try:
    import requests
except ImportError:
    raise SystemExit("Bitte zuerst installieren: pip install requests")

# ---------------------------------
# Helpers
# ---------------------------------

def local_tz_offset_minutes() -> int:
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

def safe_int(s: str) -> Optional[int]:
    try:
        return int(s.strip())
    except Exception:
        return None

def pick_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data","items","results","rows"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []

def jdump(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)

# ---------------------------------
# API Wrapper (User-sicht)
# ---------------------------------

class API:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base = base_url
        self.token = token

    # Auth
    def register(self, vorname: str, name: str, email: str, passwort: str, avatar: Optional[str]):
        url = join_url(self.base, "/register")
        body = {"vorname": vorname or None, "name": name, "email": email, "passwort": passwort, "avatar": avatar or None}
        return fetch_json("POST", url, None, json_body=body)

    def login(self, email: str, passwort: str):
        body = {"email": email, "passwort": passwort}
        url = join_url(self.base, "/login")
        data, err = fetch_json("POST", url, None, json_body=body)
        if not err and isinstance(data, dict) and (data.get("token") or data.get("accessToken")):
            return data, None
        url2 = join_url(self.base, "/auth/login")
        data2, err2 = fetch_json("POST", url2, None, json_body=body)
        if not err2:
            return data2, None
        return None, err or err2 or {"error": "login_failed"}

    def me(self):
        url = join_url(self.base, "/me")
        return fetch_json("GET", url, self.token)

    # Users/Friends
    def users(self):
        url = join_url(self.base, "/users")
        return fetch_json("GET", url, self.token)

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

    # Challenges
    def challenges(self, with_today: bool, tz_min: Optional[int]):
        url = join_url(self.base, "/challenges")
        params = {}
        if with_today:
            params["withToday"] = "true"
        if tz_min is not None:
            params["tzOffsetMinutes"] = str(tz_min)
        return fetch_json("GET", url, self.token, params=params)

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

    def challenge_detail(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}")
        return fetch_json("GET", url, self.token)

    def challenge_members(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}/members")
        return fetch_json("GET", url, self.token)

    def challenge_activity(self, cid: int):
        url = join_url(self.base, f"/challenges/{cid}/activity")
        return fetch_json("GET", url, self.token)

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
        if date: params["date"] = date
        if tz_min is not None: params["tzOffsetMinutes"] = str(tz_min)
        body = {"imageUrl": image_url, "caption": caption or None, "visibility": visibility or "freunde"}
        if timestamp is not None:
            body["timestamp"] = timestamp
        return fetch_json("POST", url, self.token, params=params, json_body=body)

    # Feed
    def feed(self):
        url = join_url(self.base, "/feed")
        return fetch_json("GET", url, self.token)

    def feed_like(self, post_id: int):
        url = join_url(self.base, f"/feed/{post_id}/like")
        return fetch_json("POST", url, self.token)

    def feed_unlike(self, post_id: int):
        url = join_url(self.base, f"/feed/{post_id}/unlike")
        return fetch_json("POST", url, self.token)

    def feed_comment(self, post_id: int, text: str):
        url = join_url(self.base, f"/feed/{post_id}/comments")
        body = {"text": text}
        return fetch_json("POST", url, self.token, json_body=body)

    # Profile
    def my_posts(self):
        url = join_url(self.base, "/me/posts")
        return fetch_json("GET", url, self.token)

    def user_posts(self, uid: int):
        url = join_url(self.base, f"/users/{uid}/posts")
        return fetch_json("GET", url, self.token)

    # Notifications
    def notifications(self):
        url = join_url(self.base, "/notifications")
        return fetch_json("GET", url, self.token)

    def mark_notification_read(self, nid: int):
        url = join_url(self.base, f"/notifications/{nid}/read")
        return fetch_json("POST", url, self.token)

    # Challenge-Invites
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

# ---------------------------------
# GUI
# ---------------------------------

class UserGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Habit User GUI")
        self.geometry("1280x900")

        # State
        self.api: Optional[API] = None
        self.tz_min = local_tz_offset_minutes()
        self.users_cache: List[Dict[str, Any]] = []
        self.challenges_cache: List[Dict[str, Any]] = []
        self.feed_cache: List[Dict[str, Any]] = []

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

    # ---------- Header ----------

    def _build_header(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill=tk.X, padx=10, pady=8)

        self.base_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.tz_var = tk.StringVar()

        ttk.Label(wrap, text="Base URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(wrap, textvariable=self.base_var, width=44).grid(row=0, column=1, sticky="we", padx=6)

        ttk.Label(wrap, text="Token:").grid(row=0, column=2, sticky="w")
        ttk.Entry(wrap, textvariable=self.token_var, width=44, show="•").grid(row=0, column=3, sticky="we", padx=6)

        ttk.Label(wrap, text="tzOffsetMinutes:").grid(row=0, column=4, sticky="e")
        ttk.Entry(wrap, textvariable=self.tz_var, width=8).grid(row=0, column=5, sticky="w")

        ttk.Label(wrap, text="Email:").grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Entry(wrap, textvariable=self.email_var, width=44).grid(row=1, column=1, sticky="we", padx=6, pady=(6,0))

        ttk.Label(wrap, text="Passwort:").grid(row=1, column=2, sticky="w", pady=(6,0))
        ttk.Entry(wrap, textvariable=self.pass_var, width=44, show="•").grid(row=1, column=3, sticky="we", padx=6, pady=(6,0))

        ttk.Button(wrap, text="Login", command=self.on_login).grid(row=1, column=4, sticky="we", padx=(6,0), pady=(6,0))
        ttk.Button(wrap, text="Register", command=self.on_register_dialog).grid(row=1, column=5, sticky="we", pady=(6,0))

        for c in range(6):
            wrap.columnconfigure(c, weight=1)

    # ---------- Tabs ----------

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,8))

        # Challenges
        self.tab_ch = ttk.Frame(self.tabs); self.tabs.add(self.tab_ch, text="Challenges")
        self._build_challenges_tab(self.tab_ch)

        # Feed
        self.tab_feed = ttk.Frame(self.tabs); self.tabs.add(self.tab_feed, text="Feed")
        self._build_feed_tab(self.tab_feed)

        # Freunde
        self.tab_fr = ttk.Frame(self.tabs); self.tabs.add(self.tab_fr, text="Freunde")
        self._build_friends_tab(self.tab_fr)

        # Notifications
        self.tab_notif = ttk.Frame(self.tabs); self.tabs.add(self.tab_notif, text="Notifications")
        self._build_notifications_tab(self.tab_notif)

        # Profile
        self.tab_prof = ttk.Frame(self.tabs); self.tabs.add(self.tab_prof, text="Profile")
        self._build_profile_tab(self.tab_prof)

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

    # ---------- Challenges Tab ----------

    def _build_challenges_tab(self, root: ttk.Frame):
        # Top-Zeile
        top = ttk.Frame(root); top.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(top, text="Challenges laden", command=self.on_load_challenges).pack(side=tk.LEFT)
        ttk.Label(top, text="withToday").pack(side=tk.LEFT, padx=(12,4))
        self.with_today_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, variable=self.with_today_var).pack(side=tk.LEFT)
        ttk.Label(top, text="tzOffsetMinutes").pack(side=tk.LEFT, padx=(12,4))
        self.ch_tz_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.ch_tz_var, width=8).pack(side=tk.LEFT)
        ttk.Button(top, text="Challenge erstellen", command=self.on_create_challenge_dialog).pack(side=tk.LEFT, padx=12)

        # Mitte-Zeile: Basis-Controls + Chat
        mid = ttk.Frame(root); mid.pack(fill=tk.X, padx=6, pady=(0,6))
        ttk.Label(mid, text="cid:").pack(side=tk.LEFT)
        self.sel_cid = tk.StringVar()
        ttk.Entry(mid, textvariable=self.sel_cid, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(mid, text="Detail", command=self.on_ch_detail).pack(side=tk.LEFT, padx=2)
        ttk.Button(mid, text="Mitglieder", command=self.on_ch_members).pack(side=tk.LEFT, padx=2)
        ttk.Button(mid, text="Activity", command=self.on_ch_activity).pack(side=tk.LEFT, padx=2)
        ttk.Button(mid, text="Chat laden", command=self.on_ch_chat_get).pack(side=tk.LEFT, padx=2)
        self.chat_text_var = tk.StringVar()
        ttk.Entry(mid, textvariable=self.chat_text_var, width=28).pack(side=tk.LEFT, padx=(12,4))
        ttk.Button(mid, text="Chat senden", command=self.on_ch_chat_send).pack(side=tk.LEFT)

        # **Deutlich sichtbarer Button** -> oeffnet Confirm-Dialog
        big = ttk.Frame(root); big.pack(fill=tk.X, padx=6, pady=(0,6))
        ttk.Button(big, text="Bestaetigen posten … (Dialog)", command=self.open_confirm_dialog)\
            .pack(side=tk.RIGHT, padx=4)

        # Inline-Confirm in eigenem LabelFrame (grid)
        confirm = ttk.LabelFrame(root, text="Bestaetigen posten (Inline)")
        confirm.pack(fill=tk.X, padx=6, pady=(0,6))
        r = 0
        ttk.Label(confirm, text="imageUrl:").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.confirm_img = tk.StringVar()
        ttk.Entry(confirm, textvariable=self.confirm_img, width=48).grid(row=r, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(confirm, text="caption:").grid(row=r, column=2, sticky="w", padx=4, pady=4)
        self.confirm_cap = tk.StringVar()
        ttk.Entry(confirm, textvariable=self.confirm_cap, width=28).grid(row=r, column=3, sticky="we", padx=4, pady=4)

        r += 1
        ttk.Label(confirm, text="visibility:").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.confirm_vis = tk.StringVar(value="freunde")
        ttk.Combobox(confirm, textvariable=self.confirm_vis, values=["freunde","privat"], width=12)\
            .grid(row=r, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(confirm, text="date (YYYY-MM-DD):").grid(row=r, column=2, sticky="w", padx=4, pady=4)
        self.confirm_date = tk.StringVar()
        ttk.Entry(confirm, textvariable=self.confirm_date, width=14).grid(row=r, column=3, sticky="w", padx=4, pady=4)

        r += 1
        ttk.Label(confirm, text="tzOffsetMinutes:").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.confirm_tz = tk.StringVar()
        ttk.Entry(confirm, textvariable=self.confirm_tz, width=10).grid(row=r, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(confirm, text="timestamp (ms):").grid(row=r, column=2, sticky="w", padx=4, pady=4)
        self.confirm_ts = tk.StringVar()
        ttk.Entry(confirm, textvariable=self.confirm_ts, width=18).grid(row=r, column=3, sticky="w", padx=4, pady=4)

        r += 1
        ttk.Button(confirm, text="Bestaetigen posten (Inline)", command=self.on_confirm_post)\
            .grid(row=r, column=0, columnspan=4, sticky="e", padx=4, pady=(6,4))

        confirm.columnconfigure(1, weight=1)
        confirm.columnconfigure(3, weight=1)

        # Tabelle
        self.tbl_ch = ttk.Treeview(root, columns=["id","name","today.status","today.pending","blocked"],
                                   show="headings", height=18)
        for c,w in zip(["id","name","today.status","today.pending","blocked"], [80,320,140,120,100]):
            self.tbl_ch.heading(c, text=c)
            self.tbl_ch.column(c, width=w, stretch=True)
        self.tbl_ch.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tbl_ch.bind("<<TreeviewSelect>>", lambda e: self._on_select_ch_row())

    def _on_select_ch_row(self):
        sel = self.tbl_ch.selection()
        if not sel:
            return
        try:
            vals = self.tbl_ch.item(sel[0], "values")
            if vals and len(vals) > 0:
                self.sel_cid.set(str(vals[0]))
        except Exception:
            pass

    # ---------- Confirm Dialog ----------

    def open_confirm_dialog(self):
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt (Zeile auswaehlen oder cid Feld fuellen).")
            return
        win = tk.Toplevel(self)
        win.title(f"Bestaetigen posten – Challenge {cid}")
        win.geometry("560x260")
        frm = ttk.Frame(win); frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        v_img = tk.StringVar(value=self.confirm_img.get() or "")
        v_cap = tk.StringVar(value=self.confirm_cap.get() or "")
        v_vis = tk.StringVar(value=self.confirm_vis.get() or "freunde")

        ttk.Label(frm, text="imageUrl").grid(row=0, column=0, sticky="e", pady=6, padx=6)
        ttk.Entry(frm, textvariable=v_img).grid(row=0, column=1, sticky="we", pady=6, padx=6)

        ttk.Label(frm, text="caption").grid(row=1, column=0, sticky="e", pady=6, padx=6)
        ttk.Entry(frm, textvariable=v_cap).grid(row=1, column=1, sticky="we", pady=6, padx=6)

        ttk.Label(frm, text="visibility").grid(row=2, column=0, sticky="e", pady=6, padx=6)
        ttk.Combobox(frm, textvariable=v_vis, values=["freunde","privat"], width=12).grid(row=2, column=1, sticky="w", pady=6, padx=6)

        frm.columnconfigure(1, weight=1)

        def do_post():
            self.confirm_img.set(v_img.get().strip())
            self.confirm_cap.set(v_cap.get().strip())
            self.confirm_vis.set(v_vis.get().strip() or "freunde")
            if not (self.confirm_ts.get() or "").strip():
                self.confirm_ts.set(str(int(time.time()*1000)))
            if not (self.confirm_tz.get() or "").strip():
                self.confirm_tz.set(str(self.tz_min))
            self.on_confirm_post()
            win.destroy()

        ttk.Button(frm, text="POSTEN", command=do_post).grid(row=3, column=1, sticky="e", pady=(10,0))

    # ---------- Feed Tab ----------

    def _build_feed_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Feed laden", command=self.on_feed).pack(side=tk.LEFT)
        ttk.Label(bar, text="postId:").pack(side=tk.LEFT, padx=(12,2))
        self.feed_post_id = tk.StringVar()
        ttk.Entry(bar, textvariable=self.feed_post_id, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Like", command=self.on_feed_like).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Unlike", command=self.on_feed_unlike).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Kommentieren", command=self.on_feed_comment).pack(side=tk.LEFT, padx=4)

        self.tbl_feed = ttk.Treeview(root, columns=["id","userId","action","timestamp","caption","imageUrl","likesCount","commentsCount","likedByMe"], show="headings", height=18)
        for c,w in zip(["id","userId","action","timestamp","caption","imageUrl","likesCount","commentsCount","likedByMe"], [60,80,100,140,280,360,100,120,100]):
            self.tbl_feed.heading(c, text=c)
            self.tbl_feed.column(c, width=w, stretch=True)
        self.tbl_feed.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    # ---------- Friends Tab ----------

    def _build_friends_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Freunde laden", command=self.on_friends).pack(side=tk.LEFT)
        ttk.Label(bar, text="Suche Nutzer (Name/Email):").pack(side=tk.LEFT, padx=(12,4))
        self.search_q = tk.StringVar()
        ttk.Entry(bar, textvariable=self.search_q, width=24).pack(side=tk.LEFT)
        ttk.Button(bar, text="Alle Nutzer laden", command=self.on_users_all).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Suche anwenden", command=self.on_users_filter).pack(side=tk.LEFT, padx=4)

        ttk.Label(bar, text="toUserId:").pack(side=tk.LEFT, padx=(12,2))
        self.req_to_uid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.req_to_uid, width=8).pack(side=tk.LEFT)
        self.req_msg = tk.StringVar()
        ttk.Entry(bar, textvariable=self.req_msg, width=24).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Freund anfragen", command=self.on_send_friend_request).pack(side=tk.LEFT)

        ttk.Label(bar, text="friend userId entfernen:").pack(side=tk.LEFT, padx=(12,2))
        self.rm_uid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.rm_uid, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Entfernen", command=self.on_remove_friend).pack(side=tk.LEFT, padx=4)

        bar2 = ttk.Frame(root); bar2.pack(fill=tk.X, padx=6, pady=(0,6))
        ttk.Button(bar2, text="Requests Incoming", command=lambda: self.on_friend_requests("incoming")).pack(side=tk.LEFT)
        ttk.Button(bar2, text="Requests Outgoing", command=lambda: self.on_friend_requests("outgoing")).pack(side=tk.LEFT, padx=6)
        ttk.Label(bar2, text="requestId:").pack(side=tk.LEFT, padx=(12,2))
        self.req_id = tk.StringVar()
        ttk.Entry(bar2, textvariable=self.req_id, width=8).pack(side=tk.LEFT)
        ttk.Button(bar2, text="Accept", command=self.on_accept_friend_request).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar2, text="Decline", command=self.on_decline_friend_request).pack(side=tk.LEFT, padx=4)

        self.tbl_users = ttk.Treeview(root, columns=["id","name","email"], show="headings", height=18)
        for c,w in zip(["id","name","email"], [80,240,260]):
            self.tbl_users.heading(c, text=c)
            self.tbl_users.column(c, width=w, stretch=True)
        self.tbl_users.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    # ---------- Notifications Tab ----------

    def _build_notifications_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Notifications laden", command=self.on_notif).pack(side=tk.LEFT)
        ttk.Label(bar, text="notif id:").pack(side=tk.LEFT, padx=(12,2))
        self.notif_id = tk.StringVar()
        ttk.Entry(bar, textvariable=self.notif_id, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Mark Read", command=self.on_notif_read).pack(side=tk.LEFT, padx=6)

        ttk.Button(bar, text="Invites Incoming", command=lambda: self.on_invites("incoming")).pack(side=tk.LEFT, padx=(20,4))
        ttk.Button(bar, text="Invites Outgoing", command=lambda: self.on_invites("outgoing")).pack(side=tk.LEFT, padx=4)
        ttk.Label(bar, text="inviteId:").pack(side=tk.LEFT, padx=(12,2))
        self.inv_id = tk.StringVar()
        ttk.Entry(bar, textvariable=self.inv_id, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Accept", command=self.on_invite_accept).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Decline", command=self.on_invite_decline).pack(side=tk.LEFT, padx=3)

        self.tbl_notif = ttk.Treeview(root, columns=["id","userId","text","read","createdAt"], show="headings", height=10)
        for c,w in zip(["id","userId","text","read","createdAt"], [60,80,420,80,160]):
            self.tbl_notif.heading(c, text=c)
            self.tbl_notif.column(c, width=w, stretch=True)
        self.tbl_notif.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6,3))

        ttk.Label(root, text="Invites").pack(anchor="w", padx=6)
        self.tbl_inv = ttk.Treeview(root, columns=["id","challengeId","fromUserId","toUserId","status","message","createdAt"],
                                    show="headings", height=8)
        for c,w in zip(["id","challengeId","fromUserId","toUserId","status","message","createdAt"], [60,90,90,90,90,320,140]):
            self.tbl_inv.heading(c, text=c)
            self.tbl_inv.column(c, width=w, stretch=True)
        self.tbl_inv.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,8))

    # ---------- Profile Tab ----------

    def _build_profile_tab(self, root: ttk.Frame):
        bar = ttk.Frame(root); bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bar, text="Meine Posts laden", command=self.on_my_posts).pack(side=tk.LEFT)
        ttk.Label(bar, text="userId:").pack(side=tk.LEFT, padx=(12,2))
        self.prof_uid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.prof_uid, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="User Posts laden", command=self.on_user_posts).pack(side=tk.LEFT, padx=4)

        ttk.Label(bar, text="postId:").pack(side=tk.LEFT, padx=(12,2))
        self.prof_pid = tk.StringVar()
        ttk.Entry(bar, textvariable=self.prof_pid, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text="Like", command=self.on_prof_like).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Unlike", command=self.on_prof_unlike).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Kommentieren", command=self.on_prof_comment).pack(side=tk.LEFT, padx=3)

        self.tbl_prof = ttk.Treeview(root, columns=["id","userId","visibility","timestamp","caption","imageUrl","likesCount","commentsCount"],
                                     show="headings", height=18)
        for c,w in zip(["id","userId","visibility","timestamp","caption","imageUrl","likesCount","commentsCount"],
                       [60,80,90,140,300,280,100,120]):
            self.tbl_prof.heading(c, text=c)
            self.tbl_prof.column(c, width=w, stretch=True)
        self.tbl_prof.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

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
        s = (self.tz_var.get() or "").strip()
        if not s: return None
        return safe_int(s)

    def _cid(self) -> Optional[int]:
        s = (self.sel_cid.get() or "").strip()
        if s: return safe_int(s)
        sel = self.tbl_ch.selection()
        if sel:
            try:
                vals = self.tbl_ch.item(sel[0], "values")
                if vals: return int(vals[0])
            except: pass
        return None

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

    # ---------- Handlers: Auth ----------

    def on_login(self):
        try:
            base = self.base_var.get().strip()
            email = self.email_var.get().strip()
            pw = self.pass_var.get().strip()
            if not base or not email or not pw:
                messagebox.showwarning("Hinweis","Bitte Base URL, Email, Passwort eingeben.")
                return
            tmp = API(base)
            data, err = tmp.login(email, pw)
            if err:
                self.set_json(err); messagebox.showerror("Login fehlgeschlagen", jdump(err)); return
            token = (data or {}).get("token") or (data or {}).get("accessToken")
            if not token:
                messagebox.showerror("Login fehlgeschlagen","Kein Token erhalten"); return
            self.token_var.set(token)
            self.api = API(base, token)
            messagebox.showinfo("Login", f"Login erfolgreich fuer {email}")
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
                    messagebox.showinfo("OK","Registrierung + Auto-Login erfolgreich")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Fehler", str(e))
        ttk.Button(frm, text="Registrieren", command=do_reg).grid(row=5, column=0, columnspan=2, pady=8)

    # ---------- Handlers: Challenges ----------

    def on_load_challenges(self):
        api = self._get_api()
        with_today = True if self.with_today_var.get() else False
        tz = safe_int(self.ch_tz_var.get().strip()) if self.ch_tz_var.get().strip() else self._tz()
        data, err = api.challenges(with_today, tz)
        if err:
            self.set_json(err); return
        rows = pick_list(data) if isinstance(data, list) else data
        if not isinstance(rows, list): rows = []
        for r in rows:
            r.setdefault("today", {})
        self.challenges_cache = rows
        self._fill_tree(self.tbl_ch, rows, ["id","name","today.status","today.pending","blocked"])
        self.set_json(rows)

    def on_create_challenge_dialog(self):
        win = tk.Toplevel(self); win.title("Challenge erstellen"); win.geometry("520x360")
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
            out=[]
            for part in s.split(","):
                part=part.strip()
                if not part: continue
                try: out.append(int(part))
                except: pass
            return out

        def do_create():
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

        ttk.Button(frm, text="Erstellen", command=do_create).grid(row=len(rows), column=0, columnspan=2, pady=10)

    def on_ch_detail(self):
        cid = self._cid()
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.challenge_detail(cid)
        self.set_json(data or err)

    def on_ch_members(self):
        cid = self._cid()
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.challenge_members(cid)
        self.set_json(data or err)

    def on_ch_activity(self):
        cid = self._cid()
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.challenge_activity(cid)
        self.set_json(data or err)

    def on_ch_chat_get(self):
        cid = self._cid()
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        api = self._get_api()
        data, err = api.get_chat(cid)
        self.set_json(data or err)

    def on_ch_chat_send(self):
        cid = self._cid()
        if not cid: messagebox.showwarning("Hinweis","cid fehlt"); return
        txt = self.chat_text_var.get().strip()
        if not txt: messagebox.showwarning("Hinweis","Chat-Text fehlt"); return
        api = self._get_api()
        data, err = api.post_chat(cid, txt)
        self.set_json(data or err)
        if not err:
            self.chat_text_var.set("")
            self.on_ch_chat_get()

    def on_confirm_post(self):
        print("[DEBUG] on_confirm_post clicked")
        cid = self._cid()
        if not cid:
            messagebox.showwarning("Hinweis","cid fehlt (Zeile in Tabelle waehlen oder cid Feld fuellen).")
            return

        image_url = self.confirm_img.get().strip()
        if not image_url:
            image_url = simpledialog.askstring("imageUrl", "Bitte imageUrl eingeben (oder data:image/...):") or ""
            image_url = image_url.strip()
            if not image_url:
                messagebox.showwarning("Hinweis","imageUrl fehlt")
                return
            self.confirm_img.set(image_url)

        cap = self.confirm_cap.get().strip() or None
        vis = (self.confirm_vis.get().strip() or "freunde")

        date = self.confirm_date.get().strip() or None
        tz_text = self.confirm_tz.get().strip()
        tz_min = safe_int(tz_text) if tz_text else (self._tz() if self._tz() is not None else local_tz_offset_minutes())
        ts_text = self.confirm_ts.get().strip()
        ts = safe_int(ts_text) if ts_text else int(time.time() * 1000)

        print(f"[DEBUG] posting confirm cid={cid} imageUrl(len)={len(image_url)} vis={vis} date={date} tz={tz_min} ts={ts}")

        api = self._get_api()
        data, err = api.confirm(cid, image_url, cap, vis, date, tz_min, ts)
        self.set_json(data or err)

        if err:
            print(f"[DEBUG] confirm error: {err}")
            messagebox.showerror("Fehler beim Posten", jdump(err))
        else:
            print("[DEBUG] confirm ok")
            messagebox.showinfo("OK", "Bestaetigung gepostet.")

    # ---------- Feed ----------

    def on_feed(self):
        api = self._get_api()
        data, err = api.feed()
        rows = pick_list(data) if not err else []
        self.feed_cache = rows
        flat = []
        for it in rows:
            ev = it.get("evidence") if isinstance(it, dict) else None
            cap = ev.get("caption") if isinstance(ev, dict) else None
            img = ev.get("imageUrl") if isinstance(ev, dict) else None
            flat.append({
                "id": it.get("id"),
                "userId": it.get("userId"),
                "action": it.get("action") or it.get("type"),
                "timestamp": it.get("timestamp"),
                "caption": cap,
                "imageUrl": img,
                "likesCount": it.get("likesCount"),
                "commentsCount": it.get("commentsCount"),
                "likedByMe": it.get("likedByMe"),
            })
        self._fill_tree(self.tbl_feed, flat, ["id","userId","action","timestamp","caption","imageUrl","likesCount","commentsCount","likedByMe"])
        self.set_json(data or err)

    def on_feed_like(self):
        pid = safe_int((self.feed_post_id.get() or "").strip())
        if not pid:
            messagebox.showwarning("Hinweis","postId fehlt"); return
        api = self._get_api()
        data, err = api.feed_like(pid)
        self.set_json(data or err)
        if not err:
            self.on_feed()

    def on_feed_unlike(self):
        pid = safe_int((self.feed_post_id.get() or "").strip())
        if not pid:
            messagebox.showwarning("Hinweis","postId fehlt"); return
        api = self._get_api()
        data, err = api.feed_unlike(pid)
        self.set_json(data or err)
        if not err:
            self.on_feed()

    def on_feed_comment(self):
        pid = safe_int((self.feed_post_id.get() or "").strip())
        if not pid:
            messagebox.showwarning("Hinweis","postId fehlt"); return
        text = simpledialog.askstring("Kommentieren", "Kommentar-Text:")
        if not text: return
        api = self._get_api()
        data, err = api.feed_comment(pid, text)
        self.set_json(data or err)
        if not err:
            self.on_feed()

    # ---------- Friends ----------

    def on_users_all(self):
        api = self._get_api()
        data, err = api.users()
        rows = pick_list(data) if not err else data or []
        if isinstance(rows, dict) and "users" in rows:
            rows = rows["users"]
        if not isinstance(rows, list):
            rows = []
        self.users_cache = rows
        self._fill_tree(self.tbl_users, rows, ["id","name","email"])
        self.set_json(rows)

    def on_users_filter(self):
        if not self.users_cache:
            self.on_users_all()
            return
        q = (self.search_q.get() or "").strip().lower()
        if not q:
            rows = self.users_cache
        else:
            rows = []
            for u in self.users_cache:
                s = f"{u.get('name','')} {u.get('email','')}".lower()
                if q in s:
                    rows.append(u)
        self._fill_tree(self.tbl_users, rows, ["id","name","email"])
        self.set_json(rows)

    def on_friends(self):
        api = self._get_api()
        data, err = api.friends()
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_users, rows, ["id","fromUserId","toUserId","status","createdAt","message"])
        self.set_json(data or err)

    def on_send_friend_request(self):
        uid = safe_int((self.req_to_uid.get() or "").strip())
        if not uid:
            messagebox.showwarning("Hinweis","toUserId fehlt"); return
        api = self._get_api()
        data, err = api.send_friend_request(uid, self.req_msg.get().strip() or None)
        self.set_json(data or err)

    def on_friend_requests(self, direction: str):
        api = self._get_api()
        data, err = api.friend_requests(direction)
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_users, rows, ["id","fromUserId","toUserId","status","createdAt","message"])
        self.set_json(data or err)

    def on_accept_friend_request(self):
        rid = safe_int((self.req_id.get() or "").strip())
        if not rid:
            messagebox.showwarning("Hinweis","requestId fehlt"); return
        api = self._get_api()
        data, err = api.accept_friend_request(rid)
        self.set_json(data or err)

    def on_decline_friend_request(self):
        rid = safe_int((self.req_id.get() or "").strip())
        if not rid:
            messagebox.showwarning("Hinweis","requestId fehlt"); return
        api = self._get_api()
        data, err = api.decline_friend_request(rid)
        self.set_json(data or err)

    def on_remove_friend(self):
        messagebox.showinfo("Info", "Freund entfernen ist serverseitig (noch) nicht implementiert.")

    # ---------- Notifications & Invites ----------

    def on_notif(self):
        api = self._get_api()
        data, err = api.notifications()
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_notif, rows, ["id","userId","text","read","createdAt"])
        self.set_json(data or err)

    def on_notif_read(self):
        nid = safe_int((self.notif_id.get() or "").strip())
        if not nid:
            messagebox.showwarning("Hinweis","notif id fehlt"); return
        api = self._get_api()
        data, err = api.mark_notification_read(nid)
        self.set_json(data or err)

    def on_invites(self, direction: str):
        api = self._get_api()
        data, err = api.list_challenge_invites(direction)
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_inv, rows, ["id","challengeId","fromUserId","toUserId","status","message","createdAt"])
        self.set_json(data or err)

    def on_invite_accept(self):
        rid = safe_int((self.inv_id.get() or "").strip())
        if not rid:
            messagebox.showwarning("Hinweis","inviteId fehlt"); return
        api = self._get_api()
        data, err = api.accept_challenge_invite(rid)
        self.set_json(data or err)

    def on_invite_decline(self):
        rid = safe_int((self.inv_id.get() or "").strip())
        if not rid:
            messagebox.showwarning("Hinweis","inviteId fehlt"); return
        api = self._get_api()
        data, err = api.decline_challenge_invite(rid)
        self.set_json(data or err)

    # ---------- Profile Handlers ----------

    def on_my_posts(self):
        api = self._get_api()
        data, err = api.my_posts()
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_prof, rows, ["id","userId","visibility","timestamp","caption","imageUrl","likesCount","commentsCount"])
        self.set_json(data or err)

    def on_user_posts(self):
        uid = safe_int((self.prof_uid.get() or "").strip())
        if not uid:
            messagebox.showwarning("Hinweis","userId fehlt"); return
        api = self._get_api()
        data, err = api.user_posts(uid)
        rows = pick_list(data) if not err else []
        self._fill_tree(self.tbl_prof, rows, ["id","userId","visibility","timestamp","caption","imageUrl","likesCount","commentsCount"])
        self.set_json(data or err)

    def on_prof_like(self):
        pid = safe_int((self.prof_pid.get() or "").strip())
        if not pid:
            messagebox.showwarning("Hinweis","postId fehlt"); return
        api = self._get_api()
        data, err = api.feed_like(pid)
        self.set_json(data or err)
        if not err:
            # Refresh je nachdem, welches Grid gerade relevant ist
            if (self.prof_uid.get() or "").strip():
                self.on_user_posts()
            else:
                self.on_my_posts()

    def on_prof_unlike(self):
        pid = safe_int((self.prof_pid.get() or "").strip())
        if not pid:
            messagebox.showwarning("Hinweis","postId fehlt"); return
        api = self._get_api()
        data, err = api.feed_unlike(pid)
        self.set_json(data or err)
        if not err:
            if (self.prof_uid.get() or "").strip():
                self.on_user_posts()
            else:
                self.on_my_posts()

    def on_prof_comment(self):
        pid = safe_int((self.prof_pid.get() or "").strip())
        if not pid:
            messagebox.showwarning("Hinweis","postId fehlt"); return
        text = simpledialog.askstring("Kommentieren", "Kommentar-Text:")
        if not text:
            return
        api = self._get_api()
        data, err = api.feed_comment(pid, text)
        self.set_json(data or err)
        if not err:
            if (self.prof_uid.get() or "").strip():
                self.on_user_posts()
            else:
                self.on_my_posts()

# ---------------------------------
# main
# ---------------------------------

def main():
    app = UserGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
    
    
    
    