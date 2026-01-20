#!/usr/bin/env python3
"""
Generiert eine HTML-Vorschau mit automatisch generierten Avataren.
"""
import sys
import os

# Füge Backend zum Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.utils.avatar_generator import generate_avatar_data_uri, get_initials, get_avatar_color


def generate_preview_html():
    """Generiert HTML-Vorschau mit Beispiel-Avataren."""
    
    # Beispiel-Benutzer
    users = [
        "Mauro Frehner",
        "Anna Schmidt",
        "Max Mustermann",
        "Lisa Müller",
        "Tom Weber",
        "Sarah Johnson",
        "Peter Pan",
        "Maria Garcia",
        "John Doe",
        "Emma Wilson"
    ]
    
    html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automatische Avatar-Generierung - Vorschau</title>
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
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .info-box {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .info-box h2 {
            color: #667eea;
            margin-bottom: 15px;
        }
        
        .info-box p {
            color: #555;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        
        .info-box ul {
            margin-left: 20px;
            color: #555;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 30px;
            margin-bottom: 50px;
        }
        
        .avatar-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
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
            border-radius: 50%;
            margin: 0 auto 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .user-name {
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        
        .user-initials {
            font-size: 0.9em;
            color: #888;
            margin-bottom: 5px;
        }
        
        .user-color {
            font-size: 0.85em;
            color: #999;
            font-family: 'Courier New', monospace;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .feature {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .feature h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        .feature p {
            color: #666;
            font-size: 0.95em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎨 Automatische Avatar-Generierung</h1>
            <p class="subtitle">Initialen-Avatare für alle Benutzer</p>
        </header>
        
        <div class="info-box">
            <h2>📋 Wie funktioniert es?</h2>
            <p>Das Backend generiert automatisch personalisierte Avatare für Benutzer, die noch kein Profilbild hochgeladen haben:</p>
            <ul>
                <li>✨ Initialen werden aus dem Namen extrahiert (z.B. "Max Mustermann" → "MM")</li>
                <li>🎨 Jeder Name erhält eine konsistente, zufällige Farbe</li>
                <li>🔄 Beim Avatar-Upload wird der automatische Avatar ersetzt</li>
                <li>⚡ SVG Data-URIs benötigen keine zusätzlichen HTTP-Requests</li>
            </ul>
        </div>
        
        <div class="info-box">
            <h2>✅ Funktionen</h2>
            <div class="feature-grid">
                <div class="feature">
                    <h3>Automatische Generierung</h3>
                    <p>Bei Registrierung und beim Laden aus der DB wird automatisch ein Avatar erstellt</p>
                </div>
                <div class="feature">
                    <h3>Konsistente Farben</h3>
                    <p>Gleicher Name = gleiche Farbe, immer</p>
                </div>
                <div class="feature">
                    <h3>Ersetzbar</h3>
                    <p>Hochgeladene Avatare ersetzen automatisch generierte</p>
                </div>
                <div class="feature">
                    <h3>Performant</h3>
                    <p>SVG Data-URIs, keine zusätzlichen Netzwerk-Requests</p>
                </div>
            </div>
        </div>
        
        <h2 style="color: white; text-align: center; margin-bottom: 30px;">👥 Beispiel-Benutzer</h2>
        
        <div class="grid">
"""
    
    # Generiere Avatar-Karten für jeden Benutzer
    for user in users:
        initials = get_initials(user)
        color = get_avatar_color(user)
        avatar_data_uri = generate_avatar_data_uri(user)
        
        html += f"""
            <div class="avatar-card">
                <img src="{avatar_data_uri}" alt="{user}" class="avatar-image">
                <div class="user-name">{user}</div>
                <div class="user-initials">Initialen: {initials}</div>
                <div class="user-color">Farbe: {color}</div>
            </div>
"""
    
    html += """
        </div>
        
        <div class="info-box">
            <h2>🚀 Implementierung</h2>
            <p><strong>Geänderte Datei:</strong> <code>backend/repositories/user_repository.py</code></p>
            <p>Die Avatar-Generierung erfolgt automatisch beim Laden von User-Objekten aus der Datenbank.</p>
            <p style="margin-top: 15px;"><strong>Keine Frontend-Änderungen erforderlich!</strong> Die <code>avatar_url</code> wird wie gewohnt verwendet.</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


if __name__ == "__main__":
    print("Generiere Avatar-Vorschau...")
    html = generate_preview_html()
    
    output_file = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "AVATAR_AUTO_PREVIEW.html"
    )
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ Vorschau erstellt: {output_file}")
    print("\nÖffne die Datei im Browser, um die Avatare zu sehen!")
