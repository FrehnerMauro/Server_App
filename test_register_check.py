#!/usr/bin/env python
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import time

# 1. Registriere neuen User via API
print("=" * 80)
print("1️⃣  REGISTRIERE NEUEN USER VIA API")
print("=" * 80)

timestamp = int(time.time())
email = f"testuser{timestamp}@test.com"

response = requests.post("http://localhost:8000/register", json={
    "vorname": "TestCheck",
    "name": "User",
    "email": email,
    "password": "test12345",
    "nb_state": "accepted"
})

print(f"Status: {response.status_code}")
data = response.json()
print(f"User ID: {data['user']['id']}")
print(f"Avatar: {data['user']['avatar_url'][:60]}...")

user_id = data['user']['id']

# 2. Prüfe sofort in der DB
print("\n" + "=" * 80)
print(f"2️⃣  ÜBERPRÜFE DB NACH USER ID {user_id}")
print("=" * 80)

time.sleep(1)  # Warte 1 Sekunde

conn = psycopg2.connect("postgresql://mauro:1234@localhost:5432/socialhabit")
cursor = conn.cursor(cursor_factory=RealDictCursor)

cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
user = cursor.fetchone()

if user:
    print(f"✅ USER EXISTIERT IN DB!")
    print(f"   ID: {user['id']}")
    print(f"   Username: {user['username']}")
    print(f"   Email: {user['email']}")
    print(f"   Avatar: {user['avatar_url'][:60] if user['avatar_url'] else 'NULL'}...")
else:
    print(f"❌ USER NICHT GEFUNDEN IN DB!")
    print(f"\nVerfügbare Users (letzte 3):")
    cursor.execute("SELECT id, username, email FROM users ORDER BY id DESC LIMIT 3")
    for row in cursor.fetchall():
        print(f"   - ID {row['id']}: {row['username']} ({row['email']})")

cursor.close()
conn.close()
