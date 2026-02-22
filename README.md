# HA Add-on: DWG to PDF Converter 🏗️

Ein benutzerdefiniertes Home Assistant Add-on mit einem Flask-basierten Webinterface. Es ermöglicht den Upload von DWG-Dateien, bietet eine Vorschau zur Ebenen-Steuerung (Layer) und exportiert bereinigte Pläne als PDF.

## Funktionsweise

Da DWG ein proprietäres Format ist, arbeitet dieses Add-on in einer mehrstufigen Pipeline:
1. **Upload:** DWG-Datei wird über die Web-UI hochgeladen.
2. **Konvertierung:** Das Open-Source Tool **GNU LibreDWG** wandelt die DWG im Hintergrund in eine DXF-Datei um.
3. **Vorschau & Layer:** Die DXF wird lokal im Browser gerendert, unerwünschte Layer können abgewählt werden.
4. **Export:** Das Python-Backend (`ezdxf`) generiert aus der bereinigten DXF ein fertiges PDF.

## 🚀 Technologie-Basis

Dieses Add-on nutzt **GNU LibreDWG** zur Umwandlung. Die lästige Installation externer proprietärer Tools (wie dem ODA File Converter) entfällt komplett, da LibreDWG tief ins Add-on-Image integriert ist.

## Ordnerstruktur

- `/app`: Enthält die Flask-Anwendung (`app.py`), HTML-Templates und statische Dateien (JS/CSS).
- `Dockerfile`: Baut das Image inkl. Python-Abhängigkeiten und kopiert LibreDWG aus einem Basis-Image.
- `config.yaml`: Die Home Assistant Add-on Konfigurationsdatei.
- `run.sh`: Der Startpunkt für den Gunicorn-Webserver.

## Installation in Home Assistant

1. Fügen Sie dieses Repository als "Custom Add-on Repository" in Ihrem Home Assistant Add-on Store hinzu.
2. Laden Sie die Add-on-Liste neu.
3. Suchen Sie nach "DWG to PDF Converter" und klicken Sie auf Installieren.
4. Starten Sie das Add-on und öffnen Sie die Web UI (Ingress wird unterstützt).
