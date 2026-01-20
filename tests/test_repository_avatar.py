#!/usr/bin/env python3
"""
Test-Script für Avatar-Generierung im Repository-Layer.
"""
import sys
import os

# Füge Backend zum Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_repository_avatar_generation():
    """Testet die Avatar-Generierung im Repository."""
    print("=" * 60)
    print("Test: Repository Avatar-Generierung")
    print("=" * 60)
    
    # Mock Row Class
    class MockRow(dict):
        def get(self, key, default=None):
            return self.get(key, default) if key in self else default
    
    from backend.repositories.user_repository import UserRepository
    
    repo = UserRepository()
    
    # Simuliere verschiedene DB-Rows
    test_cases = [
        {
            "name": "Benutzer ohne Avatar",
            "row": MockRow({
                "id": 1,
                "username": "mauro.frehner",
                "email": "mauro@example.com",
                "display_name": "Mauro Frehner",
                "avatar_url": None,
                "role": "user",
                "is_admin": 0,
                "is_active": True,
                "created_at": 1640000000000,
                "updated_at": 1640000000000
            })
        },
        {
            "name": "Benutzer mit leerem Avatar",
            "row": MockRow({
                "id": 2,
                "username": "anna.schmidt",
                "email": "anna@example.com",
                "display_name": "Anna Schmidt",
                "avatar_url": "",
                "role": "user",
                "is_admin": 0,
                "is_active": True,
                "created_at": 1640000000000,
                "updated_at": 1640000000000
            })
        },
        {
            "name": "Benutzer mit bestehendem Avatar",
            "row": MockRow({
                "id": 3,
                "username": "john.doe",
                "email": "john@example.com",
                "display_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "role": "user",
                "is_admin": 0,
                "is_active": True,
                "created_at": 1640000000000,
                "updated_at": 1640000000000
            })
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}:")
        print(f"   Display Name: {test['row']['display_name']}")
        print(f"   Original Avatar: {test['row']['avatar_url']}")
        
        # Konvertiere zu User-Objekt
        user = repo._row_to_model(test['row'])
        
        print(f"   Generierter Avatar: {user.avatar_url[:50] if user.avatar_url else None}...")
        
        # Prüfe ob Avatar generiert wurde
        if test['row']['avatar_url'] in [None, ""]:
            assert user.avatar_url and user.avatar_url.startswith("data:image/svg+xml"), \
                "Avatar sollte automatisch generiert werden"
            print(f"   ✅ Avatar wurde automatisch generiert")
        else:
            assert user.avatar_url == test['row']['avatar_url'], \
                "Bestehender Avatar sollte beibehalten werden"
            print(f"   ✅ Bestehender Avatar wurde beibehalten")
    
    print("\n" + "=" * 60)
    print("✅ Alle Repository-Tests erfolgreich!")
    print("=" * 60)


if __name__ == "__main__":
    test_repository_avatar_generation()
