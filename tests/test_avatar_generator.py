"""
Test Script für Avatar-Generierung.
"""
import sys
import os
from pathlib import Path

# Füge Backend zum Path hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from backend.utils.avatar_generator import (
    get_initials,
    get_avatar_color,
    generate_avatar_data_uri,
)


def test_avatar_generation():
    """Testet die Avatar-Generierung."""
    
    test_cases = [
        ("Mauro Frehner", "MF"),
        ("John Doe", "JD"),
        ("Anna", "A"),
        ("", "U"),
        (None, "U"),
        ("   ", "U"),
        ("Marie Theres Koch", "MK"),  # Nur erste 2 Wörter
    ]
    
    print("=" * 60)
    print("AVATAR GENERATOR TEST")
    print("=" * 60)
    
    for display_name, expected_initials in test_cases:
        initials = get_initials(display_name)
        status = "✓" if initials == expected_initials else "✗"
        print(f"\n{status} Display Name: {display_name!r}")
        print(f"  Expected: {expected_initials}, Got: {initials}")
        
        if display_name:
            color = get_avatar_color(display_name)
            print(f"  Color: {color}")
    
    # Test Data-URI Generation
    print("\n" + "=" * 60)
    print("TESTING DATA-URI GENERATION")
    print("=" * 60)
    
    display_name = "Mauro Frehner"
    data_uri = generate_avatar_data_uri(display_name)
    print(f"\nDisplay Name: {display_name}")
    print(f"Data-URI Length: {len(data_uri)} characters")
    print(f"Data-URI Prefix: {data_uri[:50]}...")
    print(f"Valid: {data_uri.startswith('data:image/svg+xml;base64,')}")
    
    # Test mit verschiedenen Namen
    print("\n" + "=" * 60)
    print("VERSCHIEDENE AVATARE")
    print("=" * 60)
    
    names = [
        "Mauro Frehner",
        "Julia Schmidt",
        "Peter Müller",
        "Sarah Klein",
        "Marco Rossi",
    ]
    
    for name in names:
        uri = generate_avatar_data_uri(name)
        initials = get_initials(name)
        color = get_avatar_color(name)
        print(f"\n{name}")
        print(f"  Initialen: {initials}")
        print(f"  Farbe: {color}")
        print(f"  URI-Länge: {len(uri)} chars")


if __name__ == "__main__":
    test_avatar_generation()
    print("\n" + "=" * 60)
    print("Test abgeschlossen!")
    print("=" * 60)
