#!/usr/bin/env python3
"""
Überprüfe ob User in DB mit Avatar gespeichert ist.
"""
import psycopg2
from psycopg2.extras import RealDictCursor

# Verbinde mit der Datenbank
conn = psycopg2.connect("postgresql://mauro:1234@localhost:5432/socialhabit")
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Prüfe die letzten 5 Users
cursor.execute("""
    SELECT id, username, display_name, email, avatar_url, created_at 
    FROM users 
    ORDER BY id DESC 
    LIMIT 5
""")

print("=" * 80)
print("LETZTE 5 USERS IN DB:")
print("=" * 80)

for row in cursor.fetchall():
    print(f"\n👤 User ID: {row['id']}")
    print(f"   Username: {row['username']}")
    print(f"   Display Name: {row['display_name']}")
    print(f"   Email: {row['email']}")
    
    if row['avatar_url']:
        avatar_preview = row['avatar_url'][:80] if len(row['avatar_url']) > 80 else row['avatar_url']
        print(f"   ✅ Avatar vorhanden: {avatar_preview}...")
        print(f"      Länge: {len(row['avatar_url'])} Zeichen")
        print(f"      Startet mit data:image: {row['avatar_url'].startswith('data:image')}")
    else:
        print(f"   ❌ Avatar ist NULL!")
    
    print(f"   Created: {row['created_at']}")

print("\n" + "=" * 80)

# Spezielle Prüfung für User ID 13 (gerade erstellt)
print("\n✅ DETAILLIERTE PRÜFUNG FÜR USER ID=13:")
print("-" * 80)

cursor.execute("SELECT * FROM users WHERE id = 13")
user = cursor.fetchone()

if user:
    print(f"✅ User 13 existiert in DB!")
    print(f"   ID: {user['id']}")
    print(f"   Username: {user['username']}")
    print(f"   Display Name: {user['display_name']}")
    print(f"   Email: {user['email']}")
    print(f"   avatar_url: {user['avatar_url'][:100] if user['avatar_url'] else 'NULL'}...")
    
    if user['avatar_url'] and user['avatar_url'].startswith('data:image/svg+xml;base64'):
        print(f"\n🎉 SUCCESS! Avatar wurde in DB gespeichert!")
    else:
        print(f"\n❌ FEHLER: Avatar ist nicht in DB!")
else:
    print(f"❌ User 13 existiert NICHT in DB!")

cursor.close()
conn.close()

print("\n" + "=" * 80)
