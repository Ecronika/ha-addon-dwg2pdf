#!/bin/sh
echo "Starte DWG to PDF Converter Add-on..."

# Wechsle in den Ordner der Flask-App
cd /usr/src/addon/app

# Starte Gunicorn (bindet an Port 8062, 1 Worker für weniger RAM-Verbrauch, 5 Min Timeout für große PDFs)
exec gunicorn -w 1 --threads 4 --timeout 300 -b 0.0.0.0:8062 app:app
