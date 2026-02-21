#!/usr/bin/env bash
echo "Starte DWG to PDF Converter Add-on..."

# Wechsle in den Ordner der Flask-App
cd /usr/src/addon/app

# Starte Gunicorn (bindet an Port 5000, 1 Worker für weniger RAM-Verbrauch, 5 Min Timeout für große PDFs)
exec gunicorn -w 1 --timeout 300 -b 0.0.0.0:5000 app:app
