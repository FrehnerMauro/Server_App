"""
Avatar Generator - Erstellt Avatar-Initialen mit JPEG-DataURI.
"""
import base64
import re
import io
from typing import Optional
from urllib.parse import quote

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None


def get_initials(display_name: Optional[str]) -> str:
    """
    Extrahiert Anfangsbuchstaben aus einem Namen.
    
    Args:
        display_name: Anzeigename (z.B. "Mauro Frehner")
    
    Returns:
        Anfangsbuchstaben in Großbuchstaben (z.B. "MF")
    
    Examples:
        >>> get_initials("Mauro Frehner")
        "MF"
        >>> get_initials("john doe")
        "JD"
        >>> get_initials("anna")
        "A"
        >>> get_initials("")
        "U"
    """
    if not display_name or not display_name.strip():
        return "U"  # Default für "User"
    
    # Entferne mehrfache Leerzeichen und trimme
    names = display_name.strip().split()
    
    if not names:
        return "U"
    
    # Nimm max. die ersten 2 Wörter
    initials = "".join(word[0].upper() for word in names[:2] if word)
    
    return initials if initials else "U"


def get_avatar_color(display_name: Optional[str]) -> str:
    """
    Generiert eine konsistente Farbe basierend auf dem Namen.
    
    Args:
        display_name: Anzeigename
    
    Returns:
        Hex-Farbe (z.B. "#FF5733")
    """
    if not display_name:
        return "#4A90E2"
    
    # Erzeuge Hashwert vom Namen
    hash_val = hash(display_name.lower()) % 360
    
    # Vordefinierte Farben für besseres Aussehen
    colors = [
        "#FF6B6B",  # Rot
        "#4ECDC4",  # Türkis
        "#45B7D1",  # Blau
        "#FFA07A",  # Orange
        "#98D8C8",  # Mint
        "#F7DC6F",  # Gelb
        "#BB8FCE",  # Lila
        "#85C1E2",  # Hellblau
        "#F8B739",  # Gold
        "#FF9FF3",  # Rosa
    ]
    
    index = abs(hash(display_name.lower())) % len(colors)
    return colors[index]


def generate_avatar_jpeg(
    initials: str,
    bg_color: str,
    size: int = 200,
    font_size: int = 80,
    text_color: str = "#FFFFFF"
) -> bytes:
    """
    Generiert ein Avatar-Bild als JPEG (nicht SVG).
    
    Args:
        initials: Anfangsbuchstaben (z.B. "MF")
        bg_color: Hintergrundfarbe (z.B. "#FF6B6B")
        size: Bildgröße in Pixeln
        font_size: Schriftgröße für Initialen
        text_color: Textfarbe
    
    Returns:
        JPEG-Bytes
    """
    if Image is None:
        raise ImportError("Pillow ist nicht installiert. Installiere: pip install Pillow")
    
    # Konvertiere Hex-Farben zu RGB
    def hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    bg_rgb = hex_to_rgb(bg_color)
    text_rgb = hex_to_rgb(text_color)
    
    # Erstelle Bild
    img = Image.new('RGB', (size, size), bg_rgb)
    draw = ImageDraw.Draw(img)
    
    # Zeichne Text (Initialen) in die Mitte
    # Versuche Standard-Font, fallback auf default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y), initials, fill=text_rgb, font=font)
    
    # Konvertiere zu JPEG bytes
    jpeg_buffer = io.BytesIO()
    img.save(jpeg_buffer, format='JPEG', quality=95)
    jpeg_buffer.seek(0)
    
    return jpeg_buffer.getvalue()



def generate_avatar_data_uri(
    display_name: Optional[str],
    size: int = 200,
    font_size: int = 80
) -> str:
    """
    Generiert einen Data-URI Avatar mit Initialen (JPEG Format).
    
    Args:
        display_name: Anzeigename (z.B. "Mauro Frehner")
        size: Bildgröße in Pixeln
        font_size: Schriftgröße für Initialen
    
    Returns:
        Data-URI für JPEG (data:image/jpeg;base64,...)
    
    Examples:
        >>> uri = generate_avatar_data_uri("Mauro Frehner")
        >>> uri.startswith("data:image/jpeg;base64,")
        True
    """
    initials = get_initials(display_name)
    bg_color = get_avatar_color(display_name)
    
    # Generiere JPEG-Bytes
    jpeg_bytes = generate_avatar_jpeg(initials, bg_color, size, font_size)
    
    # Konvertiere zu base64
    base64_string = base64.b64encode(jpeg_bytes).decode('utf-8')
    
    return f"data:image/jpeg;base64,{base64_string}"


def get_or_create_avatar(display_name: Optional[str], existing_avatar_url: Optional[str] = None) -> str:
    """
    Gibt bestehenden Avatar zurück oder generiert einen neuen.
    
    Args:
        display_name: Anzeigename
        existing_avatar_url: Bestehende Avatar-URL (falls vorhanden)
    
    Returns:
        Avatar-URL (entweder existierend oder neu generiert)
    """
    # Wenn Avatar bereits vorhanden und nicht leer, verwende diesen
    if existing_avatar_url and existing_avatar_url.strip():
        return existing_avatar_url
    
    # Sonst generiere Avatar mit Anfangsbuchstaben
    return generate_avatar_data_uri(display_name)
