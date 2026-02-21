# ==========================================================
# STAGE 1: GCC Builder (Kompiliert GNU LibreDWG für ARM/x86)
# ==========================================================
FROM python:3.11-alpine AS builder

# 1. Alle nötigen C-Compiler und Build-Tools für Alpine Linux installieren
RUN apk add --no-cache \
    build-base \
    automake \
    libtool \
    python3-dev \
    swig \
    git \
    texinfo \
    pcre2-dev

# 2. GNU LibreDWG Quellcode direkt vom offiziellen Git Repository laden
WORKDIR /build
RUN git clone https://git.savannah.gnu.org/git/libredwg.git .

# 3. Das Kommandozeilen-Tool (dwg2dxf) und die Bibliothek aus dem C-Quellcode kompilieren
RUN sh ./autogen.sh && \
    ./configure --disable-bindings --enable-trace && \
    make -j$(nproc) && \
    make install

# ==========================================================
# STAGE 2: Runtime (Leichtgewichtiges Ziel-Image)
# ==========================================================
FROM python:3.11-alpine

# 1. Nur die zwingend für die Bibliothek nötigen Laufzeit-Pakete installieren
RUN apk add --no-cache \
    fontconfig \
    pcre2 \
    libstdc++

# 2. Die vorkompilierten Binärdateien aus der "Builder"-Stage herüberkopieren
COPY --from=builder /usr/local/bin/dwg* /usr/local/bin/
COPY --from=builder /usr/local/lib/libredwg* /usr/local/lib/

# 3. System mitteilen, wo die neuen .so Laufzeitbibliotheken liegen
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# 4. Arbeitsverzeichnis für unseren Python-Code
WORKDIR /usr/src/addon

# 5. Python Pakete installieren (Matplotlib, Flask, ezdxf)
# Alpine benötigt oft C-Compiler für matplotlib, wenn es keine passenden Wheels gibt,
# wir versuchen es durch vorkompilierte Wheels zu optimieren oder installieren die Basis-Tools kurz
RUN apk add --no-cache --virtual .build-deps g++ jpeg-dev zlib-dev freetype-dev && \
    COPY requirements.txt ./ && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# 6. Restliche Python Applikation kopieren
COPY . .

# 7. Port öffnen und Skriptberechtigung setzen
EXPOSE 8123
RUN chmod a+x /usr/src/addon/run.sh

CMD [ "/usr/src/addon/run.sh" ]
