# Avatar Generator

Das Avatar Generator System erstellt automatisch Avatar-Bilder mit Anfangsbuchstaben, wenn kein custom Avatar hochgeladen wird.

## Features

✨ **Automatische Initialen-Generierung**
- Extrahiert die Anfangsbuchstaben aus dem Display-Namen
- Beispiel: "Mauro Frehner" → "MF"
- Fallback auf "U" (User) wenn kein Name vorhanden

🎨 **Farbige SVG-Avatare**
- Jeder Name bekommt eine konsistente, aber unterschiedliche Farbe
- 10 verschiedene Farben aus einer kuratierten Palette
- Farbe wird anhand des Namens berechnet (deterministisch)

📊 **Data-URI Basiert**
- Avatar wird als Base64-encodiertes SVG gespeichert
- Keine zusätzlichen Datei-Dependencies
- Funktioniert überall, auch offline

## Verwendung

### In der Registrierung

Bei der User-Registrierung wird automatisch ein Avatar generiert, wenn:
- Kein Avatar hochgeladen wird (`request.avatar` ist None/leer)
- Der Display-Name vorhanden ist

```python
from backend.services.auth_service import AuthService

auth_service = AuthService()
response = auth_service.register(register_request)
# Avatar wird automatisch generiert mit display_name Anfangsbuchstaben
```

### In User Updates

Wenn ein User seinen Display-Namen ändert und keinen Avatar hat, wird auch ein neuer Avatar generiert:

```python
from backend.services.user_service import UserService

user_service = UserService()
updated_user = user_service.update_user(user_id, update_request)
# Avatar wird regeneriert falls nötig
```

### Manuelle Verwendung

```python
from backend.utils.avatar_generator import (
    get_initials,
    get_avatar_color,
    generate_avatar_data_uri,
    get_or_create_avatar,
)

# Nur Initialen
initials = get_initials("Mauro Frehner")  # "MF"

# Farbe für Namen
color = get_avatar_color("Mauro Frehner")  # "#4ECDC4"

# Kompletter Data-URI
avatar_uri = generate_avatar_data_uri("Mauro Frehner")
# "data:image/svg+xml;base64,PHN2Zi..."

# Smart: Verwende existierenden Avatar oder generiere einen
avatar = get_or_create_avatar("Mauro Frehner", existing_avatar_url)
```

## Avatar-Beispiele

| Name | Initialen | Farbe | Avatar |
|------|-----------|-------|--------|
| Mauro Frehner | MF | #4ECDC4 | Türkis |
| Julia Schmidt | JS | #FFA07A | Orange |
| Peter Müller | PM | #F8B739 | Gold |
| Sarah Klein | SK | #FFA07A | Orange |

## Implementation Details

### Initialen-Extraktion
- Splittet Namen bei Leerzeichen
- Nimmt bis zu 2 Wörter
- Konvertiert zu Großbuchstaben
- Default: "U" wenn leer

### Farb-Zuweisung
- Deterministische Hash-Funktion basierend auf Namen
- Unterschiedliche Farben für verschiedene Namen
- Konsistent: gleicher Name = gleiche Farbe

### SVG-Format
- 200x200px Standard (konfigurierbar)
- Zentrierte Initialen
- Bold Font-Gewicht
- Transparente Hintergrund-Unterstützung (wird mit Farbe gefüllt)

## Frontend Integration

Der Avatar wird als Data-URI in der `avatar_url` gespeichert:

```swift
// iOS Example
if let avatar = profile.avatar_url, !avatar.isEmpty {
    RemoteOrDataURLImage(urlString: avatar)
        .frame(width: 50, height: 50)
        .clipShape(Circle())
}
```

Der Data-URI kann direkt in `<img src="...">` oder `AsyncImage` verwendet werden.

## Tests

Test-Script ausführen:
```bash
python tests/test_avatar_generator.py
```

Output:
```
============================================================
AVATAR GENERATOR TEST
============================================================

✓ Display Name: 'Mauro Frehner'
  Expected: MF, Got: MF
  Color: #4ECDC4
...
```

## Konfiguration

Standard-Größen können angepasst werden:

```python
# Kleinerer Avatar
avatar_uri = generate_avatar_data_uri("Mauro Frehner", size=100, font_size=40)

# Größerer Avatar
avatar_uri = generate_avatar_data_uri("Mauro Frehner", size=400, font_size=160)
```

## Future Improvements

- [ ] Unterstützung für Emoji-Avatare
- [ ] Gradient-Hintergründe
- [ ] User-definierte Farben
- [ ] Avatar-Caching für Performance
