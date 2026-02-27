FROM python:3.14-slim

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
# -w 4: 4 Worker-Prozesse (gut für parallele Anfragen)
# -b 0.0.0.0:5000: Binde an alle Interfaces auf Port 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
