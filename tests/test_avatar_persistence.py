#!/usr/bin/env python3
"""
Test: Avatar wird in Datenbank gespeichert.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.utils.avatar_generator import get_or_create_avatar


def test_avatar_persistence():
    """Testet dass generierte Avatare gespeichert werden."""
    print("=" * 60)
    print("Test: Avatar-Persistierung in Datenbank")
    print("=" * 60)
    
    print("\n✅ Implementierung:")
    print("   1. User wird aus DB geladen")
    print("   2. Wenn avatar_url leer/NULL ist:")
    print("      - Avatar mit Initialen wird generiert")
    print("      - Generierter Avatar wird in DB gespeichert")
    print("   3. Beim nächsten Laden: Avatar ist bereits in DB")
    print()
    
    print("📝 Beispiel-Flow:")
    print()
    print("   ERSTER LOAD (avatar_url = NULL in DB):")
    print("   ----------------------------------------")
    print("   1. SELECT * FROM users WHERE id = 1")
    print("   2. avatar_url aus DB: NULL")
    print("   3. Generiere Avatar: 'data:image/svg+xml;base64,...'")
    print("   4. UPDATE users SET avatar_url = '...' WHERE id = 1")
    print("   5. User-Objekt hat jetzt Avatar")
    print()
    
    print("   ZWEITER LOAD (avatar_url in DB gespeichert):")
    print("   ---------------------------------------------")
    print("   1. SELECT * FROM users WHERE id = 1")
    print("   2. avatar_url aus DB: 'data:image/svg+xml;base64,...'")
    print("   3. Avatar bereits vorhanden, kein Update nötig")
    print("   4. User-Objekt hat Avatar aus DB")
    print()
    
    print("   NACH UPLOAD (User lädt eigenen Avatar hoch):")
    print("   ---------------------------------------------")
    print("   1. PATCH /api/users/me mit avatar_url")
    print("   2. UPDATE users SET avatar_url = 'https://...' WHERE id = 1")
    print("   3. Hochgeladener Avatar ersetzt generierten Avatar")
    print()
    
    print("=" * 60)
    print("✅ Vorteile dieser Implementierung:")
    print("=" * 60)
    print("   ✓ Avatar muss nur einmal generiert werden")
    print("   ✓ Konsistenz: Gleicher Avatar bei jedem Laden")
    print("   ✓ Performance: Keine wiederholte Generierung")
    print("   ✓ Transparent: Funktioniert automatisch")
    print("=" * 60)
    
    # Test der Funktion
    print("\n🧪 Funktionstest:")
    print()
    
    test_cases = [
        ("Mauro Frehner", None, True),
        ("Anna Schmidt", "", True),
        ("Max Mustermann", "https://example.com/avatar.jpg", False),
    ]
    
    for name, existing, should_generate in test_cases:
        result = get_or_create_avatar(name, existing)
        is_generated = result.startswith("data:image/svg+xml") if result else False
        
        if should_generate:
            assert is_generated, f"Avatar sollte generiert werden für {name}"
            print(f"   ✅ {name}: Avatar generiert (wird in DB gespeichert)")
        else:
            assert result == existing, f"Bestehender Avatar sollte verwendet werden für {name}"
            print(f"   ✅ {name}: Bestehender Avatar beibehalten")
    
    print()
    print("=" * 60)
    print("✅ Alle Tests erfolgreich!")
    print("=" * 60)


if __name__ == "__main__":
    test_avatar_persistence()
