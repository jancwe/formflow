# formflow – Wiki

Willkommen im Wiki von **formflow**, dem dynamischen Formular- und PDF-Generator für professionelle Geschäftsprozesse.

---

## Über formflow

formflow ist eine leichtgewichtige, dockerisierte Webanwendung zur digitalen Erfassung von Formulardaten (z. B. Hardware-Übergabeprotokolle) inklusive digitaler Unterschrift. Die Anwendung generiert aus den eingegebenen Daten automatisch ein professionelles, an die Corporate Identity angepasstes PDF-Dokument und speichert dieses lokal oder auf einem SMB-Netzlaufwerk.

---

## Hauptfunktionen

| Funktion | Beschreibung |
|---|---|
| **Dynamische Formulare** | Formulare werden vollständig über YAML-Dateien definiert – kein Programmieren erforderlich |
| **Digitale Unterschrift** | Touch-optimiertes Unterschriftenfeld für Tablets und Smartphones |
| **PDF-Generierung** | Automatische PDF-Erstellung via WeasyPrint auf Basis von HTML-Templates |
| **Corporate Identity** | Farben, Logo und Firmenname werden zentral konfiguriert |
| **SMB-Upload** | Optionale automatische Ablage generierter PDFs auf einem Windows-Netzlaufwerk |
| **Offline-Fähig** | Alle Abhängigkeiten werden lokal ausgeliefert – ideal für Intranet-Umgebungen |

---

## Schnellstart

```bash
# Fertiges Image verwenden (empfohlen)
docker-compose pull
docker-compose up -d

# Oder: Container selbst bauen und starten
docker-compose up -d --build

# Anwendung aufrufen
# http://localhost:8080
```

Weitere Installations- und Konfigurationshinweise finden sich in der README-Datei des Haupt-Repositories (siehe Projekt-Hauptseite).

---

## Wiki-Inhalte

| Artikel | Beschreibung |
|---|---|
| [Architektur](Architektur.md) | Technische Architektur der Webanwendung mit UML-Diagrammen |
| <a>Branching-Strategie</a> | Branching-Modell und PR-Workflow für die Entwicklung |

---

## Technologie-Stack

| Schicht | Technologie |
|---|---|
| Web-Framework | [Flask](https://flask.palletsprojects.com/) 3.x |
| WSGI-Server | [Gunicorn](https://gunicorn.org/) |
| PDF-Rendering | [WeasyPrint](https://weasyprint.org/) |
| Template-Engine | [Jinja2](https://jinja.palletsprojects.com/) |
| Konfiguration | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Formulardefinitionen | YAML |
| SMB-Zugriff | [smbprotocol](https://github.com/jborean93/smbprotocol) |
| Containerisierung | Docker / Docker Compose |
| Container Registry | <a href="https://ghcr.io/jancwe/formflow">GitHub Container Registry</a> |
| Frontend-Framework | Bootstrap 5 |

---

## Projektstruktur

```
formflow/
├── app.py                  # Anwendungs-Einstiegspunkt
├── factory.py              # Flask Application Factory
├── config.py               # Konfigurationsmodelle (Pydantic)
├── form_engine.py          # Formular-Engine und URL-Routing
├── pdf_generator.py        # PDF-Generierung via WeasyPrint
├── services.py             # Hilfsfunktionen (Formulardaten)
├── forms/                  # YAML-Formulardefinitionen
├── templates/              # HTML-Templates (Jinja2) für die Web-UI
├── pdf_templates/          # HTML-Templates für PDF-Ausgabe
├── static/                 # Statische Assets (CSS, JS, Bilder)
├── tests/                  # Automatisierte Tests (pytest)
├── Dockerfile              # Container-Definition
├── docker-compose.yml      # Produktions-Compose-Konfiguration
└── docker-compose.dev.yml  # Entwicklungs-Compose (inkl. SMB-Testserver)
```
