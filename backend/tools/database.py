import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.common.store import Database

def main():
    db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")
    tables = db.list_tables()
    print("📦 Tabellen in der Datenbank:")
    for t in tables:
        print(f"  • {t}")

if __name__ == "__main__":
    main()