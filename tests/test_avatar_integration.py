#!/usr/bin/env python3
"""
Test-Script für Avatar-Generierung bei Benutzern.
"""
import sys
import os

# Füge Backend zum Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.utils.avatar_generator import get_or_create_avatar, get_initials, get_avatar_color


def test_avatar_generation():
    """Testet die Avatar-Generierung."""
    print("=" * 60)
    print("Test: Avatar-Generierung mit Initialen")
    print("=" * 60)
    
    # Test 1: Kein bestehender Avatar
    print("\n1. Benutzer ohne Avatar:")
    avatar1 = get_or_create_avatar("Mauro Frehner", None)
    print(f"   Name: Mauro Frehner")
    print(f"   Initialen: {get_initials('Mauro Frehner')}")
    print(f"   Farbe: {get_avatar_color('Mauro Frehner')}")
    print(f"   Avatar: {avatar1[:50]}...")
    
    # Test 2: Mit bestehendem Avatar
    print("\n2. Benutzer mit bestehendem Avatar:")
    existing_avatar = "https://example.com/avatar.jpg"
    avatar2 = get_or_create_avatar("John Doe", existing_avatar)
    print(f"   Name: John Doe")
    print(f"   Bestehender Avatar: {existing_avatar}")
    print(f"   Ergebnis: {avatar2}")
    assert avatar2 == existing_avatar, "Bestehender Avatar sollte beibehalten werden"
    
    # Test 3: Leerer Avatar-String
    print("\n3. Benutzer mit leerem Avatar-String:")
    avatar3 = get_or_create_avatar("Anna Schmidt", "")
    print(f"   Name: Anna Schmidt")
    print(f"   Initialen: {get_initials('Anna Schmidt')}")
    print(f"   Avatar: {avatar3[:50]}...")
    
    # Test 4: Einzelner Name
    print("\n4. Benutzer mit nur einem Namen:")
    avatar4 = get_or_create_avatar("Tom", None)
    print(f"   Name: Tom")
    print(f"   Initialen: {get_initials('Tom')}")
    print(f"   Avatar: {avatar4[:50]}...")
    
    # Test 5: Kein Name
    print("\n5. Benutzer ohne Namen:")
    avatar5 = get_or_create_avatar(None, None)
    print(f"   Name: None")
    print(f"   Initialen: {get_initials(None)}")
    print(f"   Avatar: {avatar5[:50]}...")
    
    print("\n" + "=" * 60)
    print("✅ Alle Tests erfolgreich!")
    print("=" * 60)


if __name__ == "__main__":
    test_avatar_generation()
