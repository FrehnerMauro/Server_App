# ============================================================
#  Apple Push Notification Service (APNs) via Zertifikat (PEM)
#  Mauro Frehner — 2025
# ============================================================

# --- Python 3.11 Fix für alte hyper/hyperframe Bibliotheken ---
import collections, collections.abc
for name in ["Iterable", "Mapping", "MutableMapping", "MutableSet", "Sequence", "Set"]:
    if not hasattr(collections, name):
        setattr(collections, name, getattr(collections.abc, name))
# ----------------------------------------------------------------

import os, json, traceback, ssl
from datetime import datetime
from apns2.client import APNsClient
from apns2.payload import Payload, PayloadAlert
from apns2.credentials import CertificateCredentials
from apns2.errors import Unregistered

# ============================================================
# 🔧  KONFIGURATION
# ============================================================
CERT_PATH = "/Users/maurofrehner/Desktop/steadyturtle_keys/prod/apns_combined.pem"
BUNDLE_ID = "MauroFrehner.social-habit-v1"

# ============================================================
# 🧩  Debug Helper
# ============================================================
def debug_log(section, info):
    print(f"\n🧩 [{datetime.now().strftime('%H:%M:%S')}] DEBUG | {section}")
    print("--------------------------------------------------")
    if isinstance(info, dict):
        print(json.dumps(info, indent=2))
    else:
        print(info)
    print("--------------------------------------------------\n")

# ============================================================
# 🚀  Client Cache (Production / Sandbox)
# ============================================================
_clients = {}

def get_client(environment: str = "prod") -> APNsClient:
    """Gibt einen APNsClient je nach Umgebung (sandbox/prod) zurück."""
    global _clients
    env = environment.lower().strip()

    if env not in _clients:
        if not os.path.exists(CERT_PATH):
            raise FileNotFoundError(f"❌ Zertifikatsdatei nicht gefunden: {CERT_PATH}")

        # OpenSSL-Fix für restriktive Cipher-Policies (neuere macOS / Python 3.11)
        ssl._create_default_https_context = ssl._create_unverified_context

        creds = CertificateCredentials(CERT_PATH)
        use_sandbox = (env == "sandbox")
        client = APNsClient(credentials=creds, use_sandbox=use_sandbox)

        _clients[env] = client
        debug_log("INIT", f"APNs Client erstellt für environment={env}")

    return _clients[env]

# ============================================================
# 📬  Notification senden
# ============================================================
def send_apns(
    device_token: str,
    title: str = "🔔 Notification",
    body: str = "Test-Nachricht von Mauro 🚀",
    sound: str = "default",
    badge: int = 1,
    environment: str = "prod"
) -> bool:
    """
    Sendet eine Push Notification via Apple APNs (Zertifikatsauth).
    - environment: 'prod' oder 'sandbox'
    Gibt True bei Erfolg, False bei Fehler.
    """
    debug_log("START", f"Sende APNs an Token={device_token[:10]}… ({environment})")

    try:
        client = get_client(environment)

        # Payload
        alert = PayloadAlert(title=title, body=body)
        payload = Payload(alert=alert, sound=sound, badge=badge)
        debug_log("PAYLOAD", payload.dict())

        # Senden
        response = client.send_notification(device_token, payload, topic=BUNDLE_ID)
        debug_log("RESPONSE", str(response))
        print(f"✅ Push gesendet an {device_token[:10]}… ({environment.upper()})")
        return True

    except Unregistered:
        debug_log("ERROR", "❌ Device deregistriert (Unregistered).")
    except ssl.SSLError as e:
        debug_log("SSL ERROR", f"❌ SSL-Fehler: {e}")
        print("👉 Wahrscheinlich falsches Environment (Sandbox/Prod mismatch).")
    except Exception as e:
        debug_log("EXCEPTION", f"{e}\n{traceback.format_exc()}")
    finally:
        debug_log("END", "send_apns abgeschlossen")

    return False