# Wir erzwingen ein Debian-basiertes Image, da HomeAssistant sonst sein eigenes Alpine-Image nimmt
# und "apt-get" sowie "dpkg" (für die .deb Datei) dann fehlschlagen würden!
FROM python:3.11-slim

# System-Abhängigkeiten installieren (oft nötig für CAD/PDF-Rendering)
RUN apt-get update && apt-get install -y \
    wget \
    xvfb \
    libfontconfig1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis im Container festlegen
WORKDIR /usr/src/addon

# ⚠️ WICHTIG: ODA File Converter installieren
# Die .deb Datei MUSS im selben Ordner wie dieses Dockerfile liegen!
COPY ODAFileConverter*.deb /tmp/oda.deb
RUN dpkg -i /tmp/oda.deb || apt-get install -f -y && rm /tmp/oda.deb

# Python-Pakete (Flask, ezdxf, etc.) kopieren und installieren
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Den gesamten restlichen Code in den Container kopieren
COPY . .

# Ausführungsrechte für das Start-Skript setzen
RUN chmod a+x /usr/src/addon/run.sh

# Start-Befehl für das Add-on
CMD [ "/usr/src/addon/run.sh" ]
