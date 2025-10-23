"""
backend/tools/admin_gui.py
Robuste Flask Admin GUI (Blueprint + Standalone)
- Startbar mit:  python backend/tools/admin_gui.py
- Oder als Modul: python -m backend.tools.admin_gui
- Oder in app.py registrierbar mit: app.register_blueprint(admin_gui)
"""

# -------------------------------------------------------------------
# Pfad-Bootstrap: funktioniert egal, von wo du startest
# -------------------------------------------------------------------
import os, sys
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(FILE_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)
for p in [REPO_ROOT, BACKEND_DIR, FILE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
from flask import Blueprint, Flask, request, session, redirect, url_for, render_template_string
from backend.common.store import state, save, next_id

# -------------------------------------------------------------------
# Blueprint-Setup
# -------------------------------------------------------------------
admin_gui = Blueprint("admin_gui", __name__, url_prefix="/admin")

HARD_CODED_ADMIN_EMAIL = "admin@example.com"
HARD_CODED_ADMIN_VORNAME = "Admin"
HARD_CODED_ADMIN_NAME = "User"
AUTO_ISSUE_TOKEN = True


# -------------------------------------------------------------------
# Bootstrap Admin
# -------------------------------------------------------------------
def _ensure_hardcoded_admin(st):
    st.setdefault("users", {})
    st.setdefault("auth", {}).setdefault("tokens", {})
    existing = next(
        (u for u in st["users"].values() if (u.get("email") or "").lower() == HARD_CODED_ADMIN_EMAIL.lower()), None
    )
    if existing:
        if not existing.get("is_admin"):
            existing["is_admin"] = True
            st["users"][str(existing["id"])] = existing
        if AUTO_ISSUE_TOKEN:
            st["auth"]["tokens"][f"token-{existing['id']}"] = existing["id"]
        return existing

    uid = next_id(st, "user_id")
    user = {
        "id": uid,
        "vorname": HARD_CODED_ADMIN_VORNAME,
        "name": HARD_CODED_ADMIN_NAME,
        "email": HARD_CODED_ADMIN_EMAIL,
        "avatar": None,
        "is_admin": True,
    }
    st["users"][str(uid)] = user
    if AUTO_ISSUE_TOKEN:
        st["auth"]["tokens"][f"token-{uid}"] = uid
    return user


@admin_gui.before_app_request
def _bootstrap_admin_once():
    st = state()
    meta = st.setdefault("meta", {})
    if meta.get("admin_bootstrapped"):
        return
    _ensure_hardcoded_admin(st)
    meta["admin_bootstrapped"] = True
    save()


# -------------------------------------------------------------------
# Session Helpers
# -------------------------------------------------------------------
def _session_token():
    t = session.get("auth_token")
    return t.strip() if isinstance(t, str) and t.strip() else None


def _require_login():
    t = _session_token()
    st = state()
    uid = st.get("auth", {}).get("tokens", {}).get(t)
    if not uid:
        return None, None
    u = st.get("users", {}).get(str(uid))
    return uid, u


def _require_admin():
    uid, u = _require_login()
    if not uid or not u or not u.get("is_admin"):
        return None, None
    return uid, u


# -------------------------------------------------------------------
# HTML Layout / Templates
# -------------------------------------------------------------------
TPL_BASE = """
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root { font-family: ui-sans-serif, system-ui, Arial, sans-serif; }
    body { background:#f6f7f9; margin:0; padding:0; }
    .wrap { max-width: 900px; margin: 40px auto; padding: 0 16px; }
    .card { background:white; padding:24px; border-radius:16px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
    .btn { display:inline-block; padding:10px 14px; border-radius:12px; border:1px solid #e5e7eb; background:white; cursor:pointer; }
    .btn.primary { background:black; color:white; }
    .btn + .btn { margin-left: 8px; }
    .row { display:flex; gap:16px; flex-wrap: wrap; }
    .col { flex: 1 1 300px; }
    input[type=text], input[type=email], input[type=password], input[type=number] {
      width:100%; padding:10px 12px; border-radius:12px; border:1px solid #e5e7eb; box-sizing: border-box;
    }
    label { display:block; margin: 0 0 12px; font-size:14px; color:#374151; }
    h1 { font-size:24px; margin:0 0 16px; }
    h2 { font-size:18px; margin:16px 0 8px; }
    pre { background:#f3f4f6; padding:12px; border-radius:12px; overflow:auto; }
    .muted { color:#6b7280; font-size:12px; }
    .error { color:#dc2626; }
    .ok { color:#16a34a; }
    a { color: #111827; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      {{ content|safe }}
    </div>
  </div>
</body>
</html>
"""


def render_page(title, content_html, **ctx):
    inner = render_template_string(content_html, **ctx)
    return render_template_string(TPL_BASE, title=title, content=inner)


# -------------------------------------------------------------------
# Seiten
# -------------------------------------------------------------------
TPL_LOGIN = """
<h1>Admin Login</h1>
<form method="post" action="{{ url_for('admin_gui.login_post') }}">
  <label>Email
    <input name="email" type="email" value="{{ email or '' }}" placeholder="admin@example.com" autocomplete="username" required>
  </label>
  <label>Passwort (wird nicht geprueft)
    <input name="password" type="password" placeholder="irgendwas" autocomplete="current-password">
  </label>
  <button class="btn primary" type="submit">Anmelden</button>
  {% if error %}<p class="error" style="margin-top:12px">{{ error }}</p>{% endif %}
  <p class="muted" style="margin-top:12px">Hinweis: Der Login akzeptiert jede Kombination, wenn die Email existiert.</p>
</form>
"""

TPL_PANEL = """
<div style="display:flex; justify-content: space-between; align-items:center;">
  <h1>Admin Panel</h1>
  <div>
    <a class="btn" href="{{ url_for('admin_gui.logout') }}">Logout</a>
  </div>
</div>
<p class="muted">Eingeloggt als <b>{{ user.email }}</b></p>

<div class="row">
  <div class="col">
    <h2>Admin Info</h2>
    <form method="post" action="{{ url_for('admin_gui.action_info') }}">
      <button class="btn primary" type="submit">Laden</button>
    </form>
    {% if info %}<pre>{{ info | tojson(indent=2) }}</pre>{% endif %}
  </div>

  <div class="col">
    <h2>Alle Benutzer</h2>
    <form method="post" action="{{ url_for('admin_gui.action_users') }}">
      <button class="btn" type="submit">Liste laden</button>
    </form>
    {% if users %}<pre>{{ users | tojson(indent=2) }}</pre>{% endif %}
  </div>
</div>

<div class="row" style="margin-top:16px">
  <div class="col">
    <h2>Promote</h2>
    <form method="post" action="{{ url_for('admin_gui.action_promote') }}">
      <label>User ID
        <input name="uid" type="number" min="1" required>
      </label>
      <button class="btn primary" type="submit">Promote</button>
    </form>
    {% if promote_msg %}<p class="{{ 'ok' if promote_ok else 'error' }}">{{ promote_msg }}</p>{% endif %}
  </div>

  <div class="col">
    <h2>Demote</h2>
    <form method="post" action="{{ url_for('admin_gui.action_demote') }}">
      <label>User ID
        <input name="uid" type="number" min="1" required>
      </label>
      <button class="btn" type="submit">Demote</button>
    </form>
    {% if demote_msg %}<p class="{{ 'ok' if demote_ok else 'error' }}">{{ demote_msg }}</p>{% endif %}
  </div>
</div>
"""

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@admin_gui.get("/login")
def login_get():
    _, u = _require_login()
    if u:
        return redirect(url_for("admin_gui.panel"))
    return render_page("Admin Login", TPL_LOGIN, email=HARD_CODED_ADMIN_EMAIL, error=None)


@admin_gui.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip()
    st = state()
    user = next((u for u in st.get("users", {}).values() if (u.get("email") or "").lower() == email.lower()), None)
    if not user:
        return render_page("Admin Login", TPL_LOGIN, email=email, error="Login fehlgeschlagen (Email unbekannt).")

    token = f"token-{user['id']}"
    st.setdefault("auth", {}).setdefault("tokens", {})
    st["auth"]["tokens"][token] = user["id"]
    save()

    session["auth_token"] = token
    return redirect(url_for("admin_gui.panel"))


@admin_gui.get("/logout")
def logout():
    session.pop("auth_token", None)
    return redirect(url_for("admin_gui.login_get"))


@admin_gui.get("/")
def panel():
    uid, u = _require_admin()
    if not u:
        return redirect(url_for("admin_gui.login_get"))
    return render_page("Admin Panel", TPL_PANEL, user=u)


@admin_gui.post("/action/info")
def action_info():
    uid, u = _require_admin()
    if not u:
        return redirect(url_for("admin_gui.login_get"))
    st = state()
    admin_user = next((x for x in st.get("users", {}).values() if x.get("is_admin")), None)
    tokens = st.get("auth", {}).get("tokens", {})
    admin_tokens = [t for t, tuid in tokens.items() if admin_user and tuid == admin_user["id"]]
    info = {"admin_exists": bool(admin_user), "admin_user": admin_user, "issued_tokens": admin_tokens}
    return render_page("Admin Panel", TPL_PANEL, user=u, info=info)


@admin_gui.post("/action/users")
def action_users():
    uid, u = _require_admin()
    if not u:
        return redirect(url_for("admin_gui.login_get"))
    st = state()
    users = list(st.get("users", {}).values())
    return render_page("Admin Panel", TPL_PANEL, user=u, users=users)


@admin_gui.post("/action/promote")
def action_promote():
    uid, u = _require_admin()
    if not u:
        return redirect(url_for("admin_gui.login_get"))
    try:
        target = int(request.form.get("uid", "0"))
    except ValueError:
        target = 0
    st = state()
    user = st.get("users", {}).get(str(target))
    if not user:
        msg, ok = "User nicht gefunden", False
    else:
        user["is_admin"] = True
        st["users"][str(target)] = user
        save()
        msg, ok = f"User {target} promoted", True
    users = list(st.get("users", {}).values())
    return render_page("Admin Panel", TPL_PANEL, user=u, users=users, promote_msg=msg, promote_ok=ok)


@admin_gui.post("/action/demote")
def action_demote():
    uid, u = _require_admin()
    if not u:
        return redirect(url_for("admin_gui.login_get"))
    try:
        target = int(request.form.get("uid", "0"))
    except ValueError:
        target = 0
    st = state()
    if target == int(uid):
        msg, ok = "Demote deiner eigenen Rolle ist nicht erlaubt", False
    else:
        user = st.get("users", {}).get(str(target))
        if not user:
            msg, ok = "User nicht gefunden", False
        else:
            user["is_admin"] = False
            st["users"][str(target)] = user
            save()
            msg, ok = f"User {target} demoted", True
    users = list(st.get("users", {}).values())
    return render_page("Admin Panel", TPL_PANEL, user=u, users=users, demote_msg=msg, demote_ok=ok)


# -------------------------------------------------------------------
# Standalone Mode
# -------------------------------------------------------------------
if __name__ == "__main__":
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev"
    app.register_blueprint(admin_gui)
    print("Starte Admin GUI auf http://127.0.0.1:5010/admin")
    app.run(host="127.0.0.1", port=5010, debug=True)