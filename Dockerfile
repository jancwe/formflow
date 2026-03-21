FROM python:3.14-slim

LABEL org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.title="formflow" \
      org.opencontainers.image.description="Dynamischer Formular- & PDF-Generator"

WORKDIR /app

# 1) System-Deps (ändert sich sehr selten)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2) Python-Deps NUR bei pyproject.toml-Änderung
#    Trick: Nur pyproject.toml kopieren + Dummy-Package,
#    damit pip install die Dependencies cached.
COPY pyproject.toml .
RUN mkdir -p src/formflow && \
    echo '__version__ = "0.1.0"' > src/formflow/__init__.py && \
    pip install --no-cache-dir . && \
    rm -rf src/formflow

# 3) Anwendungscode (ändert sich häufig)
COPY src/ src/
RUN pip install --no-cache-dir --no-deps .

# 4) Restliche Dateien (app.py, forms/, etc.)
COPY app.py .
COPY forms/ forms/

# 5) Statische Dateien + Verzeichnisse
RUN mkdir -p /app/static /data/forms /data/pdf_templates && \
    cp -r src/formflow/static/. /app/static/

EXPOSE 5000

# Verwende Gunicorn als Produktions-WSGI-Server
# -w 1: 1 Worker-Prozess – ausreichend für Low-Traffic-Intranet-Apps.
#        Jeder Worker lädt WeasyPrint (~150-300 MB), daher bewusst gering halten.
#        Für höheren Durchsatz: Wert auf (2 * CPU-Kerne + 1) erhöhen.
# --timeout 120: WeasyPrint-Rendering kann bei komplexen Templates >30s dauern.
# --max-requests 500: Worker wird nach 500 Requests graceful neu gestartet (Schutz gegen Memory Leaks).
# --max-requests-jitter 50: Zufälliger Versatz beim Restart (zukunftssicher bei mehreren Workern).
# -b 0.0.0.0:5000: Binde an alle Interfaces auf Port 5000
CMD ["gunicorn", "-w", "1", "--timeout", "120", "--max-requests", "500", "--max-requests-jitter", "50", "-b", "0.0.0.0:5000", "app:app"]
