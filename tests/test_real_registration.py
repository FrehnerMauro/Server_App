#!/usr/bin/env python3
"""
Test: Direkte Registrierung über API testen.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Importiere die Services erst nachdem app initialisiert wurde
def test_real_registration():
    """Testet echte Registrierung mit Avatar."""
    print("=" * 60)
    print("Test: Echte Registrierung mit Avatar-Generierung")
    print("=" * 60)
    
    # Initialisiere App
    from backend.app_v2 import create_app
    app = create_app()
    
    with app.app_context():
        from backend.core.container import get_container
        from backend.schemas import RegisterRequest
        
        container = get_container()
        auth_service = container.auth_service
        
        # Test-User Daten
        import random
        random_id = random.randint(1000, 9999)
        test_email = f"test.avatar.{random_id}@example.com"
        
        print(f"\n1. Registriere Test-User:")
        print(f"   Email: {test_email}")
        print(f"   Name: Max{random_id} Mustermann{random_id}")
        
        request = RegisterRequest(
            vorname=f"Max{random_id}",
            name=f"Mustermann{random_id}",
            email=test_email,
            password="test123456",
            avatar=None,  # Kein Avatar beim Request
            nb_state="accepted"
        )
        
        try:
            # Registrierung durchführen
            response = auth_service.register(request)
            
            print(f"\n2. Registrierung erfolgreich!")
            print(f"   User ID: {response.user.id}")
            print(f"   Username: {response.user.username}")
            print(f"   Display Name: {response.user.display_name}")
            
            # Prüfe Avatar
            avatar_url = response.user.avatar_url
            print(f"\n3. Avatar-URL:")
            if avatar_url:
                print(f"   Vorhanden: ✅")
                print(f"   Typ: {type(avatar_url)}")
                print(f"   Länge: {len(avatar_url)}")
                print(f"   Startet mit data:image: {avatar_url.startswith('data:image')}")
                print(f"   Vorschau: {avatar_url[:80]}...")
                
                # Lade User nochmal aus DB
                from backend.repositories import UserRepository
                user_repo = UserRepository()
                db_user = user_repo.find_by_id(response.user.id)
                
                print(f"\n4. User aus DB geladen:")
                print(f"   Avatar in DB: {db_user.avatar_url[:80] if db_user.avatar_url else 'NULL'}...")
                
                if db_user.avatar_url:
                    print(f"\n✅ SUCCESS: Avatar wurde in DB gespeichert!")
                else:
                    print(f"\n❌ FEHLER: Avatar ist NULL in DB!")
            else:
                print(f"   ❌ FEHLER: Kein Avatar in Response!")
                
        except Exception as e:
            print(f"\n❌ FEHLER bei Registrierung: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_real_registration()
