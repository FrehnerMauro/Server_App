"""
Legacy Challenge Routes - Kompatibilität mit altem Frontend.
Diese Routen verwenden die alten Feldnamen (name statt title, etc.)
"""
from flask import Blueprint, request, jsonify
from backend.blueprints.user import challenges as legacy_challenges

# Verwende alte Challenge-Routes aus blueprints/user/challenges.py
bp = legacy_challenges.bp

# Dieser Blueprint wird mit /api registriert, nicht /api/challenges
# da die alten Routen direkt unter /challenges definiert sind
