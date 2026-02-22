# ==========================================================
# Runtime (Leichtgewichtiges Ziel-Image)
# ==========================================================
FROM python:3.11-alpine

# 1. Nur die zwingend für die Bibliothek nötigen Laufzeit-Pakete installieren
RUN apk add --no-cache \
    fontconfig \
    pcre2 \
    libstdc++ \
    ttf-dejavu

# 2. Die vorkompilierten Binärdateien aus dem präkompilierten Basis-Image herüberkopieren
COPY --from=ecronika/libredwg-alpine:latest /usr/local/bin/dwg* /usr/local/bin/
COPY --from=ecronika/libredwg-alpine:latest /usr/local/lib/libredwg* /usr/local/lib/
COPY --from=ecronika/libredwg-alpine:latest /usr/local/share/libredwg /usr/local/share/libredwg

# 3. System mitteilen, wo die neuen .so Laufzeitbibliotheken liegen
ENV LD_LIBRARY_PATH=/usr/local/lib

# 4. Arbeitsverzeichnis für unseren Python-Code
WORKDIR /usr/src/addon

# 5. Python Pakete installieren (Matplotlib, Flask, ezdxf)
# Alpine benötigt oft C-Compiler für matplotlib, wenn es keine passenden Wheels gibt,
# wir versuchen es durch vorkompilierte Wheels zu optimieren oder installieren die Basis-Tools kurz
COPY requirements.txt ./
RUN apk add --no-cache --virtual .build-deps g++ jpeg-dev zlib-dev freetype-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# 6. Restliche Python Applikation kopieren
COPY . .

# 7. Aufräum-Skript als stündlichen Cronjob anlegen
RUN echo '#!/bin/sh' > /etc/periodic/hourly/cleanup \
    && echo 'find /tmp/converted -type f -mmin +60 -exec rm -f {} \;' >> /etc/periodic/hourly/cleanup \
    && echo 'find /tmp/uploads -type f -mmin +60 -exec rm -f {} \;' >> /etc/periodic/hourly/cleanup \
    && chmod a+x /etc/periodic/hourly/cleanup

# 8. Port öffnen und Skriptberechtigung setzen
EXPOSE 8062
RUN chmod a+x /usr/src/addon/run.sh

CMD [ "/usr/src/addon/run.sh" ]
