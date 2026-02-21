#!/usr/bin/env bash
echo "Starte DWG to PDF Converter Add-on..."

# Wechsle in den Ordner der Flask-App
cd /usr/src/addon/app

# Starte Gunicorn (bindet an Port 5000, 4 Worker-Prozesse für parallele Anfragen)
exec gunicorn -w 4 -b 0.0.0.0:5000 app:app
