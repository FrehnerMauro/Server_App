# Werbung im Feed – Admin-Workflow

## 1. Bild hochladen (optional)

**Endpoint:** `POST /admin/ads/upload`  
**Auth:** Admin Basic Auth (email:password)

```bash
curl -X POST http://localhost:8000/admin/ads/upload \
  -u "admin@example.com:adminpass" \
  -F "file=@/pfad/zu/deinem/werbebild.jpg"
```

**Response:**
```json
{
  "ok": true,
  "image_url": "/static/ads/ad_1737405600000_werbebild.jpg",
  "filename": "ad_1737405600000_werbebild.jpg"
}
```

Alternativ: Verwende eine externe URL (z.B. Cloudflare, S3).

---

## 2. Anzeige erstellen

**Endpoint:** `POST /admin/ads`  
**Auth:** Admin Basic Auth

```bash
curl -X POST http://localhost:8000/admin/ads \
  -u "admin@example.com:adminpass" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "/static/ads/ad_1737405600000_werbebild.jpg",
    "click_url": "https://example.com/landing",
    "headline": "Jetzt 20% Rabatt!",
    "body": "Sichere dir exklusive Angebote",
    "cta_label": "Mehr erfahren",
    "status": "draft",
    "weight": 5
  }'
```

**Response:**
```json
{
  "ok": true,
  "ad_id": 1
}
```

**Felder:**
- `image_url` (required): Bild-URL
- `click_url` (optional): Link beim Klick
- `headline` (optional): Überschrift
- `body` (optional): Text
- `cta_label` (optional): Button-Text (z.B. "Jetzt kaufen")
- `status`: `draft` / `active` / `paused`
- `weight` (optional): Höher = öfter im Feed (Default: 1)
- `start_at` / `end_at` (optional): Timestamps (ms) für Zeitfenster

---

## 3. Anzeige aktivieren

**Endpoint:** `POST /admin/ads/<id>/activate`

```bash
curl -X POST http://localhost:8000/admin/ads/1/activate \
  -u "admin@example.com:adminpass"
```

**Response:**
```json
{
  "ok": true,
  "ad_id": 1,
  "status": "active"
}
```

---

## 4. Alle Anzeigen auflisten

**Endpoint:** `GET /admin/ads`

```bash
curl http://localhost:8000/admin/ads \
  -u "admin@example.com:adminpass"
```

**Response:**
```json
{
  "ads": [
    {
      "id": 1,
      "image_url": "/static/ads/ad_1737405600000_werbebild.jpg",
      "click_url": "https://example.com",
      "headline": "Jetzt 20% Rabatt!",
      "body": "Sichere dir exklusive Angebote",
      "cta_label": "Mehr erfahren",
      "status": "active",
      "start_at": null,
      "end_at": null,
      "weight": 5,
      "impressions": 0,
      "clicks": 0,
      "created_at": 1737405600000,
      "updated_at": 1737405600000
    }
  ]
}
```

---

## 5. Anzeige bearbeiten

**Endpoint:** `PATCH /admin/ads/<id>`

```bash
curl -X PATCH http://localhost:8000/admin/ads/1 \
  -u "admin@example.com:adminpass" \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Neuer Titel!",
    "weight": 10
  }'
```

---

## 6. Anzeige pausieren

**Endpoint:** `POST /admin/ads/<id>/pause`

```bash
curl -X POST http://localhost:8000/admin/ads/1/pause \
  -u "admin@example.com:adminpass"
```

---

## Feed-Auslieferung

Aktive Ads werden automatisch alle 6 Posts im Feed eingestreut (Status: `active`, innerhalb von `start_at`/`end_at`).

Im Feed erscheinen sie als:
```json
{
  "kind": "ad",
  "id": 1,
  "image_url": "/static/ads/ad_1737405600000_werbebild.jpg",
  "click_url": "https://example.com",
  "headline": "Jetzt 20% Rabatt!",
  "body": "Sichere dir exklusive Angebote",
  "cta_label": "Mehr erfahren"
}
```

Posts haben `"kind": "post"`.

---

## Statistik

- **Impressions**: Werden automatisch gezählt, wenn die Ad im Feed ausgeliefert wird
- **Clicks**: Frontend sendet `POST /feed/ads/<id>/click` beim Klick

Abruf über `GET /admin/ads` → siehe `impressions` und `clicks` Felder.
