#!/usr/bin/env python3
"""
Debug: Prüft ob Avatar bei Registrierung gespeichert wird.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.utils.avatar_generator import get_or_create_avatar


def test_registration_logic():
    """Simuliert die Registrierungslogik."""
    print("=" * 60)
    print("Debug: Registrierung mit Avatar")
    print("=" * 60)
    
    # Simuliere RegisterRequest
    class MockRequest:
        vorname = "Max"
        name = "Mustermann"
        email = "max@test.com"
        password = "test123"
        avatar = None  # Kein Avatar beim Request
        nb_state = "accepted"
    
    request = MockRequest()
    
    print(f"\n1. Request-Daten:")
    print(f"   vorname: {request.vorname}")
    print(f"   name: {request.name}")
    print(f"   avatar: {request.avatar}")
    
    # Simuliere auth_service.py Logic
    display_name = f"{request.vorname} {request.name}"
    print(f"\n2. Display Name erstellt:")
    print(f"   display_name: {display_name}")
    
    # Avatar generieren
    avatar_url = get_or_create_avatar(display_name, request.avatar)
    print(f"\n3. Avatar generiert:")
    print(f"   avatar_url: {avatar_url[:80]}...")
    print(f"   Länge: {len(avatar_url)} Zeichen")
    print(f"   Ist generiert: {avatar_url.startswith('data:image/svg+xml')}")
    
    # Daten für DB
    user_data = {
        "username": f"{request.vorname.lower()}.{request.name.lower()}",
        "display_name": display_name,
        "email": request.email,
        "avatar_url": avatar_url,  # ← Hier sollte Avatar sein
        "password": "hashed_password",
        "is_admin": 0,
        "role": "user",
        "is_active": True,
    }
    
    print(f"\n4. Daten für DB create():")
    for key, value in user_data.items():
        if key == "avatar_url":
            print(f"   {key}: {value[:80] if value else 'NULL'}...")
        else:
            print(f"   {key}: {value}")
    
    print(f"\n5. SQL INSERT würde sein:")
    keys = ", ".join(user_data.keys())
    placeholders = ", ".join(["%s"] * len(user_data))
    print(f"   INSERT INTO users ({keys})")
    print(f"   VALUES ({placeholders})")
    
    print(f"\n6. avatar_url Wert:")
    avatar_value = user_data.get("avatar_url")
    if avatar_value:
        print(f"   ✅ Avatar ist vorhanden")
        print(f"   Typ: {type(avatar_value)}")
        print(f"   Länge: {len(avatar_value)}")
        print(f"   Vorschau: {avatar_value[:100]}...")
    else:
        print(f"   ❌ Avatar ist NULL/leer!")
    
    print("\n" + "=" * 60)
    if avatar_value and avatar_value.startswith('data:image'):
        print("✅ Avatar würde korrekt in DB gespeichert werden!")
    else:
        print("❌ PROBLEM: Avatar würde NICHT gespeichert werden!")
    print("=" * 60)


if __name__ == "__main__":
    test_registration_logic()
