FROM python:3.11-slim

WORKDIR /app

# Installiere Systemabhängigkeiten für WeasyPrint (Pango, Cairo, etc.)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

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
