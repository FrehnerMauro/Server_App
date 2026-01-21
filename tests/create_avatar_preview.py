"""
Visual Test - Generiert HTML mit echten Avatar-Bildern.
"""
import sys
import os
from pathlib import Path

# Füge Backend zum Path hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.avatar_generator import (
    get_initials,
    get_avatar_color,
    generate_avatar_svg,
)


def create_avatar_preview_html():
    """Erstellt eine HTML-Datei mit Avatar-Vorschau."""
    
    test_users = [
        "Mauro Frehner",
        "Julia Schmidt", 
        "Peter Müller",
        "Sarah Klein",
        "Marco Rossi",
        "Anna Weber",
        "Thomas Fischer",
        "Lisa Bauer",
    ]
    
    html_content = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Avatar Generator Preview</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 30px;
            margin-bottom: 50px;
        }
        
        .avatar-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .avatar-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .avatar-image {
            width: 120px;
            height: 120px;
            margin: 0 auto 15px;
            border-radius: 50%;
            display: block;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .avatar-name {
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .avatar-initials {
            font-size: 0.9em;
            color: #666;
            font-family: 'Courier New', monospace;
        }
        
        .info-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            color: #333;
        }
        
        .info-section h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .info-section p {
            line-height: 1.6;
            margin-bottom: 10px;
            color: #555;
        }
        
        .code-block {
            background: #f5f5f5;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }
        
        .feature-list {
            list-style: none;
            margin-left: 0;
        }
        
        .feature-list li {
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }
        
        .feature-list li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 Avatar Generator Preview</h1>
        
        <div class="grid">
"""
    
    # Generiere Avatare für jeden User
    for user_name in test_users:
        initials = get_initials(user_name)
        color = get_avatar_color(user_name)
        svg = generate_avatar_svg(initials, color, size=200, font_size=80)
        
        # Konvertiere SVG zu Base64 Data-URI
        import base64
        svg_bytes = svg.encode('utf-8')
        base64_bytes = base64.b64encode(svg_bytes)
        base64_string = base64_bytes.decode('utf-8')
        data_uri = f"data:image/svg+xml;base64,{base64_string}"
        
        html_content += f"""
            <div class="avatar-card">
                <img src="{data_uri}" class="avatar-image" alt="{initials}">
                <div class="avatar-name">{user_name}</div>
                <div class="avatar-initials">{initials}</div>
            </div>
"""
    
    html_content += """
        </div>
        
        <div class="info-section">
            <h2>Über den Avatar Generator</h2>
            
            <p>Der Avatar Generator erstellt automatisch Avatare mit Anfangsbuchstaben für neue Benutzer.</p>
            
            <h3 style="margin-top: 20px; color: #667eea;">Features:</h3>
            <ul class="feature-list">
                <li>Automatische Initialen-Generierung aus dem Display-Namen</li>
                <li>Deterministische Farb-Zuweisung (gleicher Name = gleiche Farbe)</li>
                <li>SVG-basiert und als Base64 Data-URI gespeichert</li>
                <li>Keine zusätzlichen Datei-Dependencies</li>
                <li>Responsive und skalierbar</li>
            </ul>
            
            <h3 style="margin-top: 20px; color: #667eea;">Beispiel:</h3>
            <div class="code-block">
// Registrierung
auth_service.register(register_request)
// → Avatar wird automatisch mit "MF" für "Mauro Frehner" generiert

// Manuell
avatar_url = generate_avatar_data_uri("Mauro Frehner")
// → data:image/svg+xml;base64,PHN2Zi8uLi4=
            </div>
            
            <p style="margin-top: 20px; color: #888; font-size: 0.9em;">
                Erzeugt am 20. Januar 2026 | Avatar Generator v1.0
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    output_path = project_root / "AVATAR_PREVIEW.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return str(output_path)


if __name__ == "__main__":
    output_file = create_avatar_preview_html()
    print(f"✓ Avatar Preview HTML erstellt: {output_file}")
    print(f"\nÖffne die Datei in einem Browser, um die generierten Avatare zu sehen!")
