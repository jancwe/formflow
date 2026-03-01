#!/bin/bash

# Aktuelle Frontend-Versionen (werden vom Skript selbst aktualisiert)
BOOTSTRAP_VER="5.3.8"
SIGPAD_VER="5.1.3"

echo "🔍 Prüfe auf Updates für alle Abhängigkeiten (das kann einen Moment dauern)..."

# --- 1. Frontend (NPM Registry) ---
LATEST_BOOTSTRAP=$(curl -s "https://registry.npmjs.org/bootstrap/latest" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)
LATEST_SIGPAD=$(curl -s "https://registry.npmjs.org/signature_pad/latest" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)

# --- 2. Backend (PyPI) ---
CUR_FLASK=$(grep -i '^Flask==' requirements.txt | cut -d'=' -f3)
CUR_WEASYPRINT=$(grep -i '^WeasyPrint==' requirements.txt | cut -d'=' -f3)
CUR_SMBPROTO=$(grep -i '^smbprotocol==' requirements.txt | cut -d'=' -f3 || true)
# fpdf2 is no longer used in the project; keep for backwards compatibility check
CUR_FPDF2=$(grep -i '^fpdf2==' requirements.txt | cut -d'=' -f3 || echo "(nicht installiert)")

LATEST_FLASK=$(curl -s "https://pypi.org/pypi/Flask/json" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)
LATEST_WEASYPRINT=$(curl -s "https://pypi.org/pypi/WeasyPrint/json" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)
LATEST_SMBPROTO=$(curl -s "https://pypi.org/pypi/smbprotocol/json" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)
# no need to query fpdf2

# --- 3. Docker (Docker Hub) ---
CUR_PYTHON=$(grep '^FROM python:' Dockerfile | cut -d':' -f2)
# Holt das neueste 3.x-slim Image
LATEST_PYTHON=$(curl -s "https://hub.docker.com/v2/repositories/library/python/tags?page_size=100" | grep -o '"name":"3\.[0-9]*-slim"' | cut -d'"' -f4 | sort -V | tail -n1)

# Fallbacks, falls offline oder API-Limit erreicht
[ -z "$LATEST_BOOTSTRAP" ] && LATEST_BOOTSTRAP=$BOOTSTRAP_VER
[ -z "$LATEST_SIGPAD" ] && LATEST_SIGPAD=$SIGPAD_VER
[ -z "$LATEST_FLASK" ] && LATEST_FLASK=$CUR_FLASK
[ -z "$LATEST_FPDF2" ] && LATEST_FPDF2=$CUR_FPDF2
[ -z "$LATEST_PYTHON" ] && LATEST_PYTHON=$CUR_PYTHON

echo ""
echo "-------------------------------------------------"
echo "📦 Frontend (Lokale Dateien):"
echo "  Bootstrap:     $BOOTSTRAP_VER -> $LATEST_BOOTSTRAP"
echo "  Signature Pad: $SIGPAD_VER -> $LATEST_SIGPAD"
echo ""
echo "🐍 Backend (requirements.txt):"
echo "  Flask:         $CUR_FLASK -> $LATEST_FLASK"
echo "  WeasyPrint:    $CUR_WEASYPRINT -> $LATEST_WEASYPRINT"
if [ -n "$CUR_SMBPROTO" ]; then
  echo "  smbprotocol:   $CUR_SMBPROTO -> $LATEST_SMBPROTO"
fi
if [ "$CUR_FPDF2" != "(nicht installiert)" ]; then
  echo "  fpdf2:         $CUR_FPDF2 -> $LATEST_FPDF2"  # legacy-kompatibel
fi
echo ""
echo "🐳 Docker (Dockerfile):"
echo "  Python Image:  $CUR_PYTHON -> $LATEST_PYTHON"
echo "-------------------------------------------------"
echo ""

# Prüfen, ob es überhaupt Updates gibt
if [ "$BOOTSTRAP_VER" == "$LATEST_BOOTSTRAP" ] && \
   [ "$SIGPAD_VER" == "$LATEST_SIGPAD" ] && \
   [ "$CUR_FLASK" == "$LATEST_FLASK" ] && \
   [ "$CUR_WEASYPRINT" == "$LATEST_WEASYPRINT" ] && \
   ([ -z "$CUR_SMBPROTO" ] || [ "$CUR_SMBPROTO" == "$LATEST_SMBPROTO" ]) && \
   [ "$CUR_PYTHON" == "$LATEST_PYTHON" ]; then
    echo "✅ Alles ist bereits auf dem neuesten Stand!"
    exit 0
fi

read -p "Möchtest du die Abhängigkeiten auf die neuesten Versionen aktualisieren? (j/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Jj]$ ]]
then
    echo "🔄 Aktualisiere Konfigurationsdateien..."

    # Sicherungsdateien anlegen, damit wir bei Buildfehlern zurückrollen können
    cp requirements.txt requirements.txt.bak
    cp Dockerfile Dockerfile.bak
    tar cfz frontend-backup.tar.gz static/css static/js || true

    # Update requirements.txt
    sed -i "s/^Flask==.*/Flask==$LATEST_FLASK/" requirements.txt
    sed -i "s/^WeasyPrint==.*/WeasyPrint==$LATEST_WEASYPRINT/" requirements.txt
    if grep -q '^smbprotocol==' requirements.txt; then
        sed -i "s/^smbprotocol==.*/smbprotocol==$LATEST_SMBPROTO/" requirements.txt
    else
        echo "smbprotocol==$LATEST_SMBPROTO" >> requirements.txt
    fi
    # legacy fpdf2 falls es noch drin steht
    sed -i "s/^fpdf2==.*/fpdf2==$LATEST_FPDF2/" requirements.txt || true

    # Update Dockerfile
    sed -i "s/^FROM python:.*/FROM python:$LATEST_PYTHON/" Dockerfile

    # Update dieses Skript selbst (für die Frontend-Versionen)
    sed -i "s/^BOOTSTRAP_VER=\".*\"/BOOTSTRAP_VER=\"$LATEST_BOOTSTRAP\"/" "$0"
    sed -i "s/^SIGPAD_VER=\".*\"/SIGPAD_VER=\"$LATEST_SIGPAD\"/" "$0"

    echo "⬇️ Lade neue Frontend-Dateien herunter..."
    mkdir -p static/css static/js
    curl -sL "https://cdn.jsdelivr.net/npm/bootstrap@${LATEST_BOOTSTRAP}/dist/css/bootstrap.min.css" -o static/css/bootstrap.min.css
    curl -sL "https://cdn.jsdelivr.net/npm/signature_pad@${LATEST_SIGPAD}/dist/signature_pad.umd.min.js" -o static/js/signature_pad.umd.min.js

    echo "🏗️ Baue das Projekt zur Kontrolle..."
    if command -v podman-compose >/dev/null 2>&1; then
        podman-compose build || BUILD_FAILED=1
    else
        docker-compose build || BUILD_FAILED=1
    fi

    if [ -n "$BUILD_FAILED" ]; then
        echo "❌ Build fehlgeschlagen – rolle Änderungen zurück."
        mv requirements.txt.bak requirements.txt
        mv Dockerfile.bak Dockerfile
        [ -f frontend-backup.tar.gz ] && tar xfz frontend-backup.tar.gz
        exit 1
    fi

    echo "✅ Alle Abhängigkeiten wurden erfolgreich aktualisiert und Build ist ok!"
    echo "⚠️  WICHTIG: Bitte starte den Container neu, um die Backend- und Docker-Updates anzuwenden:"
    echo ""
    echo "   Befehl für podman-compose"
    echo "   podman-compose down && podman-compose up -d --build"
    echo ""
    echo "   Analog bei docker-compose"
    echo "   docker-compose down && docker-compose up -d --build"
else
    echo "❌ Abbruch. Es wurden keine Änderungen vorgenommen."
fi
