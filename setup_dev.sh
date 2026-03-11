#!/bin/bash
set -e

echo "🚀 Richte die Entwicklungsumgebung für formflow ein..."

# --- 1. Python-Version prüfen ---
if ! command -v python3 &>/dev/null; then
    echo "❌ python3 nicht gefunden. Bitte Python 3.11+ installieren."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "   Python-Version: $PYTHON_VERSION"

# --- 2. Virtuelle Umgebung erstellen ---
if [ ! -d ".venv" ]; then
    echo "📦 Erstelle virtuelle Umgebung (.venv)..."
    python3 -m venv .venv
else
    echo "   .venv bereits vorhanden, überspringe Erstellung."
fi

# --- 3. Pip upgraden ---
echo "📥 Upgrade pip, setuptools und wheel..."
.venv/bin/python3 -m pip install --upgrade pip setuptools wheel

# --- 4. Abhängigkeiten installieren ---
echo "📥 Installiere Abhängigkeiten aus pyproject.toml..."
.venv/bin/pip install -e ".[dev]"

# --- 5. pre-commit-Hooks registrieren ---
echo "🔗 Registriere pre-commit-Hooks..."
.venv/bin/pre-commit install

# --- 6. .env-Datei anlegen ---
if [ ! -f ".env" ]; then
    echo "📄 Erstelle .env aus .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        echo "   ⚠️  .env.example nicht gefunden, überspringe .env-Erstellung."
    fi
else
    echo "   .env bereits vorhanden, überspringe Erstellung."
fi

echo ""
echo "✅ Entwicklungsumgebung bereit!"
echo ""
echo "   Virtuelle Umgebung aktivieren:"
echo "     source .venv/bin/activate"
echo ""
echo "   Docker-Entwicklungsumgebung starten:"
echo "     docker-compose -f docker-compose.dev.yml up -d --build"
