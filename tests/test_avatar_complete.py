#!/usr/bin/env python3
"""
Einfacher Test für Avatar-Generierung - ohne DB-Abhängigkeiten.
"""
import sys
import os

# Füge Backend zum Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.utils.avatar_generator import get_or_create_avatar, get_initials


def test_complete_flow():
    """Testet den kompletten Avatar-Generierungs-Flow."""
    print("=" * 60)
    print("Test: Kompletter Avatar-Generierungs-Flow")
    print("=" * 60)
    
    scenarios = [
        {
            "case": "Neuer Benutzer ohne Avatar bei Registrierung",
            "display_name": "Max Mustermann",
            "existing_avatar": None,
            "expected_initialen": "MM",
            "should_generate": True
        },
        {
            "case": "Neuer Benutzer mit leerem Avatar",
            "display_name": "Lisa Müller",
            "existing_avatar": "",
            "expected_initialen": "LM",
            "should_generate": True
        },
        {
            "case": "Benutzer mit hochgeladenem Avatar",
            "display_name": "Tom Weber",
            "existing_avatar": "https://cdn.example.com/avatars/user123.jpg",
            "expected_initialen": "TW",
            "should_generate": False
        },
        {
            "case": "Benutzer aktualisiert Namen, kein Avatar",
            "display_name": "Anna-Maria Schmidt",
            "existing_avatar": None,
            "expected_initialen": "AS",  # Nur ersten 2 Wörter
            "should_generate": True
        },
        {
            "case": "Benutzer mit nur einem Namen",
            "display_name": "Pedro",
            "existing_avatar": None,
            "expected_initialen": "P",
            "should_generate": True
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['case']}")
        print(f"   Display Name: {scenario['display_name']}")
        print(f"   Bestehender Avatar: {scenario['existing_avatar']}")
        
        # Führe Avatar-Generierung aus
        result_avatar = get_or_create_avatar(
            scenario['display_name'], 
            scenario['existing_avatar']
        )
        
        # Prüfe Initialen
        initialen = get_initials(scenario['display_name'])
        print(f"   Initialen: {initialen}")
        assert initialen == scenario['expected_initialen'], \
            f"Initialen sollten {scenario['expected_initialen']} sein, aber waren {initialen}"
        
        # Prüfe Avatar-Ergebnis
        if scenario['should_generate']:
            assert result_avatar.startswith("data:image/svg+xml"), \
                "Avatar sollte als SVG Data-URI generiert werden"
            print(f"   ✅ Avatar wurde generiert: {result_avatar[:60]}...")
        else:
            assert result_avatar == scenario['existing_avatar'], \
                "Bestehender Avatar sollte verwendet werden"
            print(f"   ✅ Bestehender Avatar beibehalten: {result_avatar}")
    
    print("\n" + "=" * 60)
    print("✅ Alle Szenarien erfolgreich getestet!")
    print("=" * 60)
    print("\n📋 Zusammenfassung:")
    print("   - Bei Registrierung: Avatar wird automatisch mit Initialen generiert")
    print("   - Beim Laden aus DB: Avatar wird automatisch generiert wenn keiner vorhanden")
    print("   - Bei Update: Avatar wird nur generiert wenn keiner vorhanden")
    print("   - Upload: Hochgeladener Avatar ersetzt automatisch generierten Avatar")
    print("=" * 60)


if __name__ == "__main__":
    test_complete_flow()
