# formflow: Dynamischer Formular- & PDF-Generator

formflow ist eine leichtgewichtige, dockerisierte Webanwendung zur digitalen Erfassung von Formulardaten (z.B. Hardware-Übergabeprotokolle) inklusive digitaler Unterschrift. 

Die Anwendung generiert aus den eingegebenen Daten automatisch ein professionelles, an die Corporate Identity angepasstes PDF-Dokument und speichert dieses auf dem Server.

## Hauptfunktionen

*   **Dynamische Formulare:** Formulare werden komplett über einfache YAML-Dateien definiert. Kein Programmieren nötig!
*   **Digitale Unterschrift:** Touch-optimiertes Unterschriftenfeld für Tablets und Smartphones.
*   **PDF-Generierung:** Erstellt automatisch saubere PDFs (via WeasyPrint) basierend auf HTML-Templates.
*   **Corporate Identity:** Farben, Logos und Firmennamen können zentral konfiguriert werden.
*   **Offline-Fähig:** Alle Abhängigkeiten werden lokal ausgeliefert, ideal für Intranet-Umgebungen.

---

## Installation & Start

Das Projekt nutzt Docker (bzw. Podman) für ein einfaches Deployment.

### Produktionsumgebung

Für den normalen Betrieb wird die `docker-compose.yml` verwendet. Diese startet nur die `formflow-app`.

```bash
# Container bauen und im Hintergrund starten
docker-compose up -d --build

# Anwendung aufrufen
# http://localhost:8080
```

### Entwicklungsumgebung (mit SMB-Testserver)

Für die lokale Entwicklung gibt es eine `docker-compose.dev.yml`-Datei. Diese startet zusätzlich einen Samba-Testserver, um den PDF-Upload auf einen SMB-Share zu simulieren.

Stelle sicher, dass deine `.env`-Datei die Konfiguration für den Testserver enthält:

```ini
SMB_ENABLED=true
SMB_SERVER=smb-server
SMB_SHARE=pdfs
SMB_FOLDER=
SMB_USERNAME=testuser
SMB_PASSWORD=testpass
```

**Starten der Entwicklungsumgebung:**

```bash
# Alle Container der Entwicklungsumgebung starten
docker-compose -f docker-compose.dev.yml up -d --build
```

**Stoppen der Entwicklungsumgebung:**

```bash
# Alle Container der Entwicklungsumgebung stoppen und entfernen
docker-compose -f docker-compose.dev.yml down
```

*Hinweis: Wenn du Änderungen an `app.py`, `form_engine.py` oder den HTML-Templates im `templates/`-Ordner vornimmst, musst du den Container neu bauen (`--build`). Änderungen in `forms/`, `pdf_templates/` oder `config.yaml` werden nach einem einfachen Neustart (`docker-compose restart formflow-app`) oder teilweise sofort wirksam.*

---

## Konfiguration (`config.yaml`)

Die Datei `config.yaml` im Hauptverzeichnis steuert das globale Aussehen der Web-App und der generierten PDFs.

```yaml
company:
  name: "Musterfirma GmbH"
  address: "Musterstraße 123 &bull; 12345 Musterstadt"
  logo_filename: "logo.png" # Muss im Ordner static/ liegen

colors:
  primary: "#0056b3"      # Hauptfarbe (Buttons, Header-Linie)
  text_dark: "#32373c"    # Dunkler Text (Überschriften)
  text_light: "#6d6d6d"   # Heller Text (Tabellen-Header)
  bg_light: "#fdfdfd"     # Sehr heller Hintergrund
  bg_gray: "#f8f8f8"      # Grauer Hintergrund
```

---

## Formulare definieren (`forms/*.yaml`)
> **Hinweis:** Sensible Werte wie SMB-Zugangsdaten sollten nicht in der Compose- oder
> Konfigurationsdatei stehen. Lege im einfachsten Fall stattdessen eine `.env`-Datei im Projektverzeichnis an
> (wird von `docker-compose` automatisch geladen) und definiere dort z. B.:
> ```ini
> SMB_ENABLED=true
> SMB_SERVER=fileserver.domain.local
> SMB_SHARE=Freigabe
> SMB_FOLDER=PDFs
> SMB_USERNAME=meinnutzer
> SMB_PASSWORD=meinpasswort
> ```
> Die Anwendung liest diese Umgebungsvariablen beim Start und übergibt sie an den
> SMB-Upload.

### Formulare definieren (`forms/*.yaml`)
Neue Formulare werden einfach als `.yaml`-Datei im Ordner `forms/` abgelegt. Die Anwendung erkennt sie automatisch.

### Grundstruktur eines Formulars

```yaml
title: Notebook Übergabe
description: Formular zur Erfassung der Übergabe eines Notebooks
form_id: notebook_handover # Eindeutige ID (wichtig!)
submit_button: Vorschau anzeigen
pdf_template: default_pdf.html # Optional: Spezifisches PDF-Template
fields:
  # ... Feld-Definitionen ...
```

### Verfügbare Feld-Optionen

Jedes Feld unter `fields:` unterstützt folgende Basis-Attribute:

*   `type` (String, Pflicht): Der Datentyp des Feldes (siehe unten).
*   `name` (String, Pflicht): Der interne Variablenname (darf keine Leerzeichen enthalten).
*   `label` (String, Pflicht): Die Beschriftung, die dem Benutzer angezeigt wird.
*   `required` (Boolean, Optional): Wenn `true`, muss das Feld ausgefüllt werden.
*   `in_filename` (Boolean, Optional): Wenn `true`, wird der eingegebene Wert Teil des generierten PDF-Dateinamens.

#### Feldtyp: `text`
Ein einfaches einzeiliges Textfeld.
```yaml
  - type: text
    name: user
    label: Benutzername
    required: true
    placeholder: Vollständiger Name des Benutzers
    in_filename: true
```

#### Feldtyp: `date`
Ein Datumsauswahlfeld.
```yaml
  - type: date
    name: handover_date
    label: Übergabedatum
    required: true
    default: today # Setzt automatisch das heutige Datum
```

#### Feldtyp: `select`
Ein Dropdown-Menü oder eine Checkbox-Liste.
```yaml
  - type: select
    name: condition
    label: Zustand
    required: true
    options:
      - Neuwertig
      - Gebrauchsspuren
      - Defekt
```
**Mehrfachauswahl:** Füge `multiple: true` hinzu, um das Feld als Liste von Checkboxes zu rendern, bei denen der Benutzer mehrere Optionen wählen kann.
```yaml
  - type: select
    name: accessories
    label: Zubehör
    multiple: true
    options:
      - Netzteil
      - Maus
      - Tasche
```

#### Feldtyp: `signature`
Ein Zeichenfeld für digitale Unterschriften.
```yaml
  - type: signature
    name: signature_employee
    label: Unterschrift Mitarbeiter
    required: true
    height: 200px # Höhe des Zeichenbereichs
```
*Hinweis: Ein Formular kann beliebig viele Unterschriftsfelder enthalten.*