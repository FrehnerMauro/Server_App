# Automatische Avatar-Generierung mit Initialen

## Übersicht

Das Backend generiert jetzt automatisch Avatare mit Anfangsbuchstaben für Benutzer, die noch keinen Avatar hochgeladen haben. Sobald ein Benutzer ein eigenes Avatar-Bild hochlädt, wird das automatisch generierte durch das hochgeladene Bild ersetzt.

## Funktionsweise

### 1. Bei Registrierung
Wenn sich ein neuer Benutzer registriert und kein Avatar hochlädt, wird automatisch ein Avatar mit den Initialen des Namens generiert.

**Beispiel:**
- Name: "Mauro Frehner"
- Generierter Avatar: SVG mit "MF" in einer zufälligen Farbe

### 2. Beim Laden aus der Datenbank
Wenn ein Benutzer aus der Datenbank geladen wird und kein Avatar vorhanden ist (`NULL` oder leerer String):
- Avatar wird automatisch mit Initialen generiert
- **Generierter Avatar wird in der Datenbank gespeichert**
- Beim nächsten Laden ist der Avatar bereits in der DB vorhanden (bessere Performance)

### 3. Bei Profil-Updates
- **Kein Avatar vorhanden**: Avatar wird mit den (ggf. aktualisierten) Initialen generiert
- **Avatar vorhanden**: Bestehender Avatar wird beibehalten
- **Avatar hochgeladen**: Neuer Avatar ersetzt den automatisch generierten

### 4. Beim Avatar-Upload
Sobald ein Benutzer einen Avatar hochlädt, wird dieser verwendet und ersetzt den automatisch generierten Avatar.

## Technische Details

### Avatar-Format
Die automatisch generierten Avatare sind **SVG Data-URIs** im Format:
```
data:image/svg+xml;base64,<base64-encoded-svg>
```

### Initialen-Logik
- **Zwei Namen**: Erste Buchstaben beider Namen (z.B. "Max Mustermann" → "MM")
- **Ein Name**: Erster Buchstabe (z.B. "Pedro" → "P")
- **Mehr als zwei Namen**: Erste beiden Namen (z.B. "Anna Maria Schmidt" → "AS")
- **Kein Name**: Default "U" für "User"

### Farben
Jeder Name erhält eine konsistente Farbe basierend auf einem Hash-Algorithmus. Die gleiche Person erhält immer die gleiche Farbe.

Verfügbare Farben:
- Rot (#FF6B6B)
- Türkis (#4ECDC4)
- Blau (#45B7D1)
- Orange (#FFA07A)
- Mint (#98D8C8)
- Gelb (#F7DC6F)
- Lila (#BB8FCE)
- Hellblau (#85C1E2)
- Gold (#F8B739)
- Rosa (#FF9FF3)

## Implementierung

### Geänderte Dateien

#### 1. `/backend/repositories/user_repository.py`
```python
from backend.utils.avatar_generator import get_or_create_avatar

def _row_to_model(self, row: RealDictRow) -> User:
    display_name = row.get("display_name")
    avatar_url_from_db = row.get("avatar_url")
    
    # Generiere Avatar mit Anfangsbuchstaben falls nicht vorhanden
    avatar_url = get_or_create_avatar(display_name, avatar_url_from_db)
    
    user = User(
        # ... andere Felder
        avatar_url=avatar_url,
        # ...
    )
    
    # Wenn Avatar generiert wurde (DB hatte keinen), speichere ihn
    if not avatar_url_from_db and avatar_url:
        self._save_generated_avatar(user.id, avatar_url)
    
    return user

def _save_generated_avatar(self, user_id: int, avatar_url: str) -> None:
    """Speichert generierten Avatar in der Datenbank."""
    sql = f"UPDATE {self.table_name} SET avatar_url = %s, updated_at = %s WHERE id = %s"
    updated_at = int(datetime.utcnow().timestamp() * 1000)
    
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(sql, (avatar_url, updated_at, user_id))
    except Exception:
        # Fehler beim Speichern ignorieren - Avatar wurde trotzdem generiert
        pass
```

**Wichtig**: Die Avatar-Generierung erfolgt im Repository-Layer, damit **alle** User-Objekte, die aus der Datenbank geladen werden, automatisch einen Avatar haben. **Generierte Avatare werden in der DB gespeichert**, sodass sie nur einmal generiert werden müssen.

#### 2. `/backend/services/auth_service.py`
Bei der Registrierung wird bereits `get_or_create_avatar()` verwendet (war bereits implementiert):
```python
avatar_url = get_or_create_avatar(display_name, request.avatar)
```

#### 3. `/backend/services/user_service.py`
Bei Profil-Updates wird die Avatar-Logik angewendet (war bereits implementiert):
```python
if "display_name" in update_data or "avatar_url" in update_data:
    display_name = update_data.get("display_name") or user.display_name
    avatar_url = update_data.get("avatar_url") or user.avatar_url
    update_data["avatar_url"] = get_or_create_avatar(display_name, avatar_url)
```

### Bestehende Hilfsfunktionen

Die folgenden Funktionen in `/backend/utils/avatar_generator.py` waren bereits implementiert:

- `get_initials(display_name)`: Extrahiert Initialen aus Namen
- `get_avatar_color(display_name)`: Generiert konsistente Farbe
- `generate_avatar_svg(...)`: Erstellt SVG-Avatar
- `generate_avatar_data_uri(...)`: Erstellt Data-URI
- `get_or_create_avatar(...)`: **Hauptfunktion** - verwendet bestehenden Avatar oder generiert neuen

## API-Verhalten

### Registrierung (`POST /api/auth/register`)
**Request:**
```json
{
  "vorname": "Max",
  "name": "Mustermann",
  "email": "max@example.com",
  "password": "geheim123",
  "nb_state": "accepted"
}
```

**Response:**
```json
{
  "token": "token-...",
  "user": {
    "id": 1,
    "username": "max.mustermann",
    "email": "max@example.com",
    "display_name": "Max Mustermann",
    "avatar_url": "data:image/svg+xml;base64,PHN2ZyB3aWR0...",
    "is_admin": false,
    "created_at": "2026-01-20T10:00:00Z"
  }
}
```

### Profil abrufen (`GET /api/users/me`)
**Response:**
```json
{
  "id": 1,
  "username": "max.mustermann",
  "email": "max@example.com",
  "display_name": "Max Mustermann",
  "avatar_url": "data:image/svg+xml;base64,PHN2ZyB3aWR0...",
  "is_admin": false,
  "created_at": "2026-01-20T10:00:00Z"
}
```

### Profil aktualisieren mit Avatar (`PATCH /api/users/me`)
**Request:**
```json
{
  "avatar_url": "https://cdn.example.com/my-photo.jpg"
}
```

**Response:**
   - SVG Data-URIs benötigen keine zusätzlichen HTTP-Requests
   - **Avatar wird nur einmal generiert und dann in DB gespeichert**
5. **Automatisch**: Keine manuelle Intervention nötig
6. **Konsistenz**: Gespeicherte Avatare bleiben gleich (keine erneute Generierung)
{
  "id": 1,
  "username": "max.mustermann",
  "email": "max@example.com",
  "display_name": "Max Mustermann",
  "avatar_url": "https://cdn.example.com/my-photo.jpg",
  "is_admin": false,
  "created_at": "2026-01-20T10:00:00Z"
}
```

## Vorteile

1. **Bessere User Experience**: Jeder Benutzer hat sofort einen Avatar, auch ohne Upload
2. **Wiedererkennbarkeit**: Konsistente Farben machen User leicht erkennbar
3. **Keine Platzhalter-Bilder**: Avatare mit Initialen sind persönlicher als generische Icons
4. **Performant**: SVG Data-URIs benötigen keine zusätzlichen HTTP-Requests
5. **Automatisch**: Keine manuelle Intervention nötig

## Frontend-Integration

Das Frontend muss keine Änderungen vornehmen. Die `avatar_url` wird wie gewohnt verwendet:

```swift
// iOS (SwiftUI)
AsyncImage(url: URL(string: user.avatar_url)) { image in
    image.resizable()
} placeholder: {
    ProgressView()
}
```

SVG Data-URIs werden von modernen Browsern und nativen Apps unterstützt.
Generierte Avatare werden automatisch gespeichert!** 

Beim ersten Laden eines Users ohne Avatar:
1. Avatar wird generiert (SVG Data-URI)
2. Avatar wird in der DB gespeichert (`UPDATE users SET avatar_url = '...'`)
3. Bei erneutem Laden: Avatar ist bereits in der DB vorhanden

Vier Test-Skripte verifizieren die Funktionalität:

1. **`tests/test_avatar_integration.py`**: Testet die Avatar-Generator-Funktionen
2. **`tests/test_avatar_complete.py`**: Testet den kompletten Flow mit verschiedenen Szenarien
3. **`tests/test_avatar_persistence.py`**: Testet die Speicherung in der Datenbank
4. **Bestehend: `tests/test_avatar_generator.py`**: Unit-Tests für Avatar-Generator

Alle Tests ausführen:
```bash
python tests/test_avatar_integration.py
python tests/test_avatar_complete.py
python tests/test_avatar_persistenc
Drei Test-Skripte verifizieren die Funktionalität:

1. **`tests/test_avatar_integration.py`**: Testet die Avatar-Generator-Funktionen
2. **`tests/test_avatar_complete.py`**: Testet den kompletten Flow mit verschiedenen Szenarien
3. **Bestehend: `tests/test_avatar_generator.py`**: Unit-Tests für Avatar-Generator

Alle Tests ausführen:
```bash
python tests/test_avatar_integration.py
python tests/test_avatar_complete.py
python tests/test_avatar_generator.py
```

## Zusammenfassung

Die Implementierung ist **nicht-invasiv** und **abwärtskompatibel**:
- Bestehende User mit Avataren sind nicht betroffen
- Bestehende User ohne Avatare erhalten automatisch Initialen-Avatare
- Neue User erhalten automatisch Initialen-Avatare
- Avatar-Uploads funktionieren wie bisher

Das gesamte System arbeitet transparent und erfordert keine Frontend-Änderungen.
