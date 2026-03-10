# formflow: Dynamischer Formular- & PDF-Generator

**Version: 0.1.0**

formflow ist eine leichtgewichtige, dockerisierte Webanwendung zur digitalen Erfassung von Formulardaten inklusive digitaler Unterschrift. 

Die Anwendung generiert aus den eingegebenen Daten automatisch ein an die Corporate Identity angepasstes PDF-Dokument und speichert dieses auf dem Server.

## Hauptfunktionen

*   **Dynamische Formulare:** Formulare werden komplett über einfache YAML-Dateien definiert.
*   **Digitale Unterschrift:** Touch-optimiertes Unterschriftenfeld für Tablets und Smartphones.
*   **PDF-Generierung:** Erstellt automatisch PDFs basierend auf HTML-Templates und zeigt diese dem Benutzer zur Gegenprobe, bevor das Formular endgültig zum Speichern eingereicht wird.
*   **Corporate Identity:** Farben, Logos und Firmennamen können zentral konfiguriert werden.
*   **Offline-Fähig:** Alle Abhängigkeiten werden lokal ausgeliefert, ideal für Intranet-Umgebungen.

---

## Installation & Start

Das Projekt nutzt Docker (bzw. Podman) für ein einfaches Deployment.

### Fertiges Container-Image (empfohlen)

Das offizielle Image wird bei jedem Merge auf `main` automatisch gebaut und in die GitHub Container Registry gepusht.

```bash
# Image von GitHub Container Registry ziehen
docker pull ghcr.io/jancwe/formflow:latest

# Container starten
docker run -d \
  -p 8080:5000 \
  --env-file .env \
  -v ./forms:/app/forms:Z \
  -v ./pdf_output:/app/pdfs:Z \
  -v ./drafts:/app/drafts:Z \
  ghcr.io/jancwe/formflow:latest
```

### Produktionsumgebung

Für den normalen Betrieb wird die `docker-compose.yml` verwendet. Diese startet nur die `formflow-app`.

```bash
# Image aus der Registry ziehen und im Hintergrund starten
docker-compose pull && docker-compose up -d

# Anwendung aufrufen
# http://localhost:8080
```

> **Hinweis:** Alternativ kann in der `docker-compose.yml` `build: .` durch `image: ghcr.io/jancwe/formflow:latest` ersetzt werden, um das fertige Image aus der GitHub Container Registry zu verwenden, anstatt lokal zu bauen.

> **Hinweis:** Der Host-Port kann über die Variable `APP_HOST_PORT` in der `.env`-Datei konfiguriert werden (Standard: `8080`). Beispiel: `APP_HOST_PORT=9090`

> **Automatische Updates mit Podman:** Das Container-Label `io.containers.autoupdate=registry` ist gesetzt. Mit `podman auto-update` werden neue Image-Versionen aus der Registry automatisch erkannt und eingespielt.

### Entwicklungsumgebung (mit SMB-Testserver)

Für die lokale Entwicklung gibt es eine `docker-compose.dev.yml`-Datei. Diese startet zusätzlich einen Samba-Testserver, um den PDF-Upload auf einen SMB-Share zu simulieren.

Stelle sicher, dass deine `.env`-Datei die Konfiguration für den Testserver enthält:

```ini
APP_SMB__ENABLED=true
APP_SMB__SERVER=smb-server
APP_SMB__SHARE=pdfs
APP_SMB__FOLDER=
APP_SMB__USERNAME=testuser
APP_SMB__PASSWORD=testpass
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

*Hinweis: Wenn du Änderungen an `app.py`, `form_engine.py` oder den HTML-Templates im `templates/`-Ordner vornimmst, musst du den Container in der Entwicklungsumgebung neu bauen (`--build`). Änderungen in `forms/`, `pdf_templates/` oder `.env` werden nach einem einfachen Neustart (`docker-compose -f docker-compose.dev.yml restart formflow-app`) oder teilweise sofort wirksam. In der Produktionsumgebung wird das Image aus der Registry gezogen – dort ist kein lokaler Build nötig.*

---

## Konfiguration (Umgebungsvariablen / `.env`)

Die gesamte Konfiguration erfolgt über **Umgebungsvariablen** (optional aus einer `.env`-Datei im Projektverzeichnis, die von `docker-compose` automatisch geladen wird). [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) validiert und typisiert die Werte beim Start.

Eine Vorlage mit allen verfügbaren Variablen liegt in `.env.example`.

```ini
# Firma
APP_COMPANY__NAME="Musterfirma GmbH"
APP_COMPANY__ADDRESS="Musterstraße 123 &bull; 12345 Musterstadt"
APP_COMPANY__LOGO_FILENAME="logo.png"   # Dateiname des Logos im static/-Ordner neben docker-compose.yml

# Farben
APP_COLORS__PRIMARY="#0056b3"      # Hauptfarbe (Buttons, Header-Linie)
APP_COLORS__TEXT_DARK="#32373c"     # Dunkler Text (Überschriften)
APP_COLORS__TEXT_LIGHT="#6d6d6d"    # Heller Text (Tabellen-Header)
APP_COLORS__BG_LIGHT="#fdfdfd"     # Sehr heller Hintergrund
APP_COLORS__BG_GRAY="#f8f8f8"      # Grauer Hintergrund
```

> **Hinweis:** Sensible Werte wie SMB-Zugangsdaten sollten ausschließlich über die `.env`-Datei
> oder echte Umgebungsvariablen gesetzt werden:
> ```ini
> APP_SMB__ENABLED=true
> APP_SMB__SERVER=fileserver.domain.local
> APP_SMB__SHARE=Freigabe
> APP_SMB__FOLDER=PDFs
> APP_SMB__USERNAME=meinnutzer
> APP_SMB__PASSWORD=meinpasswort
> ```

---

## Formulare definieren (`forms/*.yaml`)

Neue Formulare werden einfach als `.yaml`-Datei im Ordner `forms/` abgelegt. Die Anwendung erkennt sie automatisch.

> **Hinweis:** Die Dateien in `forms/` (direkt, nicht in Unterverzeichnissen) werden **nicht** im Repository versioniert, damit in der Produktion individuelle Anpassungen möglich sind, ohne bei `git pull` Konflikte zu erzeugen.
>
> Beispiel-Vorlagen liegen unter `forms/examples/`. Zum Einrichten einfach die gewünschten Dateien nach `forms/` kopieren:
> ```bash
> cp forms/examples/*.yaml forms/
> ```

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

*   `title` (String, Pflicht): Titel des Formulars, wird im Browser und im PDF angezeigt.
*   `description` (String, Optional): Optionale Beschreibung, die unterhalb des Titels angezeigt wird.
*   `form_id` (String, Pflicht): Eindeutige ID des Formulars (keine Leerzeichen), wird in der URL und im Dateinamen verwendet.
*   `submit_button` (String, Pflicht): Beschriftung des Absenden-Buttons.
*   `pdf_template` (String, Optional): Dateiname des zu verwendenden PDF-Templates aus dem Ordner `pdf_templates/`. Standard: `default_pdf.html`.
*   `fields` (Liste, Pflicht): Liste der Felder des Formulars.

### Verfügbare Feld-Optionen

Jedes Feld unter `fields:` unterstützt folgende Basis-Attribute:

*   `type` (String, Pflicht): Der Datentyp des Feldes (siehe unten).
*   `name` (String, Pflicht): Der interne Variablenname (darf keine Leerzeichen enthalten).
*   `label` (String, Pflicht): Die Beschriftung, die dem Benutzer angezeigt wird.
*   `required` (Boolean, Optional): Wenn `true`, muss das Feld ausgefüllt werden.
*   `in_filename` (Boolean, Optional): Wenn `true`, wird der eingegebene Wert Teil des generierten PDF-Dateinamens.
*   `in_draft_title` (Boolean, Optional): Wenn `true`, wird der Wert dieses Feldes im Untertitel des Entwurfs in der Entwurfsübersicht angezeigt.

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
*   `placeholder` (String, Optional): Platzhaltertext, der im leeren Eingabefeld angezeigt wird. Nur für den Typ `text` relevant.

#### Feldtyp: `date`
Ein Datumsauswahlfeld.
```yaml
  - type: date
    name: handover_date
    label: Übergabedatum
    required: true
    default: today # Setzt automatisch das heutige Datum
```
*Hinweis: Aktuell wird als Wert für `default` ausschließlich `today` unterstützt.*

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
*   `options` (Liste von Strings, Pflicht): Die zur Auswahl stehenden Werte.

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
    signature_label: "Digital unterzeichnet von {user} am {date_today}"
```
*   `height` (String, Pflicht): Höhe des Zeichenbereichs als CSS-Wert, z.B. `200px`. Fehlt dieses Attribut, ist der Zeichenbereich unsichtbar.
*   `signature_label` (String, Optional): Beschriftungstext, der im PDF unterhalb des Unterschriftenfeldes erscheint.
    *   Unterstützt `{feldname}`-Platzhalter, die durch den Wert des gleichnamigen Formularfeldes ersetzt werden (z.B. wird `{user}` durch den Wert des Feldes `user` ersetzt).
    *   Der spezielle Platzhalter `{date_today}` wird durch das aktuelle Datum im Format `TT.MM.JJJJ` ersetzt.
    *   Beispiel mit Feldwert-Variable: `"Digital unterzeichnet von {user} am {date_today}"`
    *   Beispiel mit statischem Text: `"Ich bestätige die Richtigkeit der Angaben."`
    *   Unbekannte Platzhalter bleiben unverändert erhalten.
    *   Ohne Angabe wird ein systemseitiger Standardtext verwendet.
*Hinweis: Ein Formular kann beliebig viele Unterschriftsfelder enthalten.*
