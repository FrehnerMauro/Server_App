#!/Users/maurofrehner/Desktop/Virt/Server_App_2/bin/python3
"""
send_apns_cert.py
-----------------
Einmaliger Testversand einer Apple Push Notification über ein
ZERTIFIKAT (statt Token-Auth).

Voraussetzung:
    - apns2 ist installiert
      -> pip install apns2
    - Zertifikat liegt als PEM-Datei vor (enthält Key + Cert)
      -> cat private_key.pem aps_development.pem > apns_cert.pem
"""

import os
import traceback
import logging
import collections
import collections.abc

# --- Python 3.11 Fix für alte hyper Bibliotheken ---
for name in ["Iterable", "Mapping", "MutableMapping", "MutableSet", "Sequence", "Set"]:
    if not hasattr(collections, name):
        setattr(collections, name, getattr(collections.abc, name))
# ---------------------------------------------------

# Logging Setup
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("send_apns_cert")

# ---------------------------------------------------
# KONFIGURATION
# ---------------------------------------------------
CERT_PATH = "/Users/maurofrehner/Desktop/apns_cert.pem"  # kombiniert
DEVICE_TOKEN = "f77f73200f6f1e228046aad329e74b28457798de2c28daa6c6e9184ae2d46ae4"
BUNDLE_ID = "MauroFrehner.social-habit-v1"
USE_SANDBOX = True  # True = Entwicklungsumgebung

TITLE = "🔔 Hallo Mauro!"
BODY = "Test-Push via Zertifikat 🚀"


# ---------------------------------------------------
# FUNKTION
# ---------------------------------------------------
def is_valid_hex_token(t: str) -> bool:
    """Überprüft, ob Token ein gültiger Hex-String ist."""
    import re
    return bool(re.fullmatch(r"[0-9a-fA-F]+", t))


def send_apns_once():
    """Sendet einen einmaligen Push über APNs (Zertifikat)."""
    log.info("🧩 Starte APNs Push (Zertifikat-Modus) …")
    log.debug("Device Token: %s", DEVICE_TOKEN)
    log.debug("Cert Path: %s (exists=%s)", CERT_PATH, os.path.exists(CERT_PATH))
    log.debug("Bundle ID (Topic): %s", BUNDLE_ID)
    log.debug("Environment: %s", "SANDBOX" if USE_SANDBOX else "PRODUCTION")

    if not is_valid_hex_token(DEVICE_TOKEN):
        log.error("❌ Ungültiger Device Token – kein reiner Hex-String.")
        return False

    if not os.path.exists(CERT_PATH):
        log.error("❌ Zertifikatsdatei nicht gefunden: %s", CERT_PATH)
        return False

    try:
        from apns2.client import APNsClient
        from apns2.payload import Payload, PayloadAlert
        from apns2.credentials import CertificateCredentials

        alert = PayloadAlert(title=TITLE, body=BODY)
        payload = Payload(alert=alert, sound="default", badge=1)

        creds = CertificateCredentials(CERT_PATH)
        client = APNsClient(credentials=creds, use_sandbox=USE_SANDBOX)

        log.info("📡 Sende Notification an APNs …")
        response = client.send_notification(DEVICE_TOKEN, payload, topic=BUNDLE_ID)

        log.info("✅ Push erfolgreich gesendet.")
        log.debug("Response: %s", response)
        return True

    except Exception as e:
        log.error("❌ Fehler beim Senden:")
        traceback.print_exc()
        return False


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
if __name__ == "__main__":
    ok = send_apns_once()
    if ok:
        log.info("🏁 Fertig – Push erfolgreich versendet.")
    else:
        log.error("🏁 Abgeschlossen – Push fehlgeschlagen.")