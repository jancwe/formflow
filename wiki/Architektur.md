# Architektur

Dieser Artikel beschreibt die technische Architektur der **formflow**-Webanwendung nach gängigen Software-Engineering-Standards.

---

## Inhaltsverzeichnis

1. [Überblick](#1-überblick)
2. [Schichtenarchitektur](#2-schichtenarchitektur)
3. [Komponentendiagramm](#3-komponentendiagramm)
4. [Klassendiagramm](#4-klassendiagramm)
5. [Sequenzdiagramm – Formular einreichen](#5-sequenzdiagramm--formular-einreichen)
6. [Deployment-Diagramm](#6-deployment-diagramm)
7. [Datenfluss](#7-datenfluss)
8. [Konfigurationsmodell](#8-konfigurationsmodell)

---

## 1. Überblick

formflow folgt einem klassischen **dreischichtigen Architekturmuster** (3-Tier Architecture) innerhalb einer einzelnen Flask-Anwendung:

| Schicht | Verantwortung |
|---|---|
| **Präsentationsschicht** | HTML-Templates (Jinja2), Bootstrap-Frontend, Signatur-Canvas |
| **Anwendungsschicht** | Flask-Routing, Formular-Engine, Formularverarbeitung, PDF-Workflow |
| **Datenschicht** | YAML-Formulardefinitionen, generierte PDF-Dateien, Entwürfe (JSON), SMB-Netzlaufwerk |

Die Anwendung wird als **Docker-Container** betrieben und über **Gunicorn** als WSGI-Server ausgeliefert.

---

## 2. Schichtenarchitektur

```
┌────────────────────────────────────────────────────────────┐
│                    Präsentationsschicht                     │
│   Bootstrap-Frontend · Jinja2-Templates · Signature-Pad    │
├────────────────────────────────────────────────────────────┤
│                    Anwendungsschicht                        │
│   Flask (WSGI) · FormEngine · PdfGenerator · Services      │
├────────────────────────────────────────────────────────────┤
│                    Datenschicht                             │
│   YAML-Formulare · PDF-Dateien (lokal) · Entwürfe (JSON) · SMB-Netzlaufwerk  │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Komponentendiagramm

Das folgende Diagramm zeigt die Hauptkomponenten der Anwendung und ihre Abhängigkeiten.

```mermaid
graph TD
    Browser["🌐 Browser\n(Client)"]

    subgraph Docker-Container
        Gunicorn["Gunicorn\n(WSGI-Server)"]

        subgraph Flask-Anwendung
            AppFactory["factory.py\nApplication Factory"]
            AppSettings["config.py\nAppSettings"]
            FormEngine["form_engine.py\nFormEngine"]
            PdfGenerator["pdf_generator.py\nPdfGenerator"]
            Services["services.py\nHilfsfunktionen"]
        end

        subgraph Dateisystem
            Forms["forms/\nYAML-Definitionen"]
            PdfTemplates["pdf_templates/\nHTML-Templates"]
            PdfsDir["pdfs/\ngenerierte PDFs"]
            DraftsDir["drafts/\nEntwürfe (JSON)"]
            Static["static/\nCSS · JS · Bilder"]
            Templates["templates/\nWeb-Templates"]
        end
    end

    SMB["SMB-Netzlaufwerk\n(optional)"]

    Browser -- "HTTP-Request" --> Gunicorn
    Gunicorn -- "WSGI" --> AppFactory
    AppFactory -- "lädt" --> AppSettings
    AppFactory -- "initialisiert" --> FormEngine
    FormEngine -- "liest" --> Forms
    FormEngine -- "delegiert PDF-Erstellung" --> PdfGenerator
    FormEngine -- "nutzt" --> Services
    FormEngine -- "rendert" --> Templates
    PdfGenerator -- "liest" --> PdfTemplates
    PdfGenerator -- "schreibt" --> PdfsDir
    Services -- "liest/schreibt" --> DraftsDir
    FormEngine -- "speichert PDF via SMB" --> SMB
    Browser -- "lädt" --> Static
```

---

## 4. Klassendiagramm

Das Klassendiagramm zeigt die zentralen Klassen und ihre Beziehungen.

```mermaid
classDiagram
    class AppSettings {
        +CompanyConfig company
        +ColorsConfig colors
        +SmbConfig smb
    }

    class CompanyConfig {
        +str name
        +str address
        +str logo_filename
    }

    class ColorsConfig {
        +str primary
        +str text_dark
        +str text_light
        +str bg_light
        +str bg_gray
    }

    class SmbConfig {
        +bool enabled
        +str server
        +str share
        +str folder
        +str username
        +str password
    }

    class FormEngine {
        +str forms_dir
        +Dict forms
        +PdfGenerator pdf_generator
        +init_app(app: Flask)
        -_load_forms()
        -_register_routes()
        -_generate_filename_parts()
        -_sanitize_for_filename()
        -_store_pdf()
    }

    class PdfGenerator {
        +str templates_dir
        +generate(form_def, form_data, output_filename, config)
    }

    class Services {
        +collect_form_data(form_def, request_form) Dict
        +save_draft(drafts_dir, form_id, form_data) str
        +load_draft(drafts_dir, draft_id) dict
        +list_drafts(drafts_dir, forms) list
        +delete_draft(drafts_dir, draft_id) None
    }

    AppSettings "1" *-- "1" CompanyConfig
    AppSettings "1" *-- "1" ColorsConfig
    AppSettings "1" *-- "1" SmbConfig
    FormEngine "1" *-- "1" PdfGenerator
    FormEngine ..> Services : nutzt
    FormEngine ..> AppSettings : liest Konfiguration
```

---

## 5. Sequenzdiagramm – Formular einreichen

Das folgende Diagramm beschreibt den vollständigen Ablauf vom Aufrufen eines Formulars bis zur Speicherung des PDFs.

```mermaid
sequenceDiagram
    actor Nutzer
    participant Browser
    participant Flask as Flask\n(FormEngine)
    participant PdfGen as PdfGenerator
    participant FS as Dateisystem
    participant SMB as SMB-Server\n(optional)

    Nutzer->>Browser: Öffnet /forms
    Browser->>Flask: GET /forms
    Flask-->>Browser: Formularliste (HTML)

    Nutzer->>Browser: Wählt Formular
    Browser->>Flask: GET /form/{form_id}
    Flask-->>Browser: Formular-HTML (mit Feldern)

    Nutzer->>Browser: Füllt Formular aus & klickt "Vorschau"
    Browser->>Flask: POST /preview/{form_id}
    Flask->>PdfGen: generate(form_def, form_data, temp_file)
    PdfGen->>FS: Schreibt temp_{uuid}.pdf
    Flask-->>Browser: Vorschau-HTML (mit PDF-Link)

    alt Nutzer bestätigt
        Nutzer->>Browser: Klickt "Bestätigen"
        Browser->>Flask: POST /confirm/{form_id}/{file_id}
        alt SMB aktiviert
            Flask->>SMB: Lädt PDF hoch
            SMB-->>Flask: Erfolg / Fehler
        else SMB deaktiviert oder Fehler
            Flask->>FS: Umbenennen zu finalem Dateinamen
        end
        Flask-->>Browser: Erfolgsseite (HTML)
    else Nutzer bearbeitet erneut
        Nutzer->>Browser: Klickt "Zurück"
        Browser->>Flask: POST /edit/{form_id}/{file_id}
        Flask->>FS: Löscht temporäres PDF
        Flask-->>Browser: Redirect zu /form/{form_id}
    end
```

---

## 6. Deployment-Diagramm

Das Deployment-Diagramm zeigt die Laufzeitumgebung in Produktion und Entwicklung.

```mermaid
graph TD
    subgraph Host-System
        subgraph Produktions-Stack["docker-compose.yml"]
            AppProd["ghcr.io/jancwe/formflow:latest\nformflow-app Container\n:8080→5000"]
        end

        subgraph Dev-Stack["docker-compose.dev.yml"]
            AppDev["formflow-app\nContainer\n:8080→5000"]
            SmbDev["smb-server\nContainer\n(dperson/samba)"]
            AppDev -- "SMB :445" --> SmbDev
        end

        subgraph Volumes
            V1["./pdf_output → /app/pdfs"]
            V2["./forms → /app/forms"]
            V3["./pdf_templates → /app/pdf_templates"]
            V4["./static → /app/static"]
            V5["./drafts → /app/drafts"]
        end
    end

    Client["Client-Browser"]
    NetSMB["Netzwerk-SMB-Share\n(Produktion)"]

    Client -- "HTTP :8080" --> AppProd
    AppProd --> V1
    AppProd --> V2
    AppProd --> V3
    AppProd --> V4
    AppProd --> V5
    AppProd -- "SMB (optional)" --> NetSMB
```

### Hinweise zum Deployment

| Umgebung | Compose-Datei | Besonderheiten |
|---|---|---|
| **Produktion** | `docker-compose.yml` | Image wird aus `ghcr.io/jancwe/formflow:latest` gezogen (kein lokaler Build); SMB über externe Netzwerkfreigabe; automatische Updates via `podman auto-update` möglich |
| **Entwicklung** | `docker-compose.dev.yml` | Lokaler Build via `build: .`; zusätzlicher `smb-server`-Container zum Testen des SMB-Uploads |

Der Anwendungsserver **Gunicorn** wird mit 2 Worker-Prozessen gestartet (`-w 2`), um parallele Anfragen zu bedienen.

---

## 7. Datenfluss

### Formular-Definition (YAML → Web-Formular)

```mermaid
flowchart LR
    YAML["forms/*.yaml\nFormulardefinition"]
    FormEngine["FormEngine\n_load_forms()"]
    Jinja["Jinja2\ndynamic_form.html"]
    Browser["Browser\nWeb-Formular"]

    YAML --> FormEngine --> Jinja --> Browser
```

### PDF-Generierung (Formulardaten → PDF)

```mermaid
flowchart LR
    FormData["Formulardaten\n(POST-Request)"]
    Services["services.py\ncollect_form_data()"]
    PdfGen["PdfGenerator\ngenerate()"]
    Template["pdf_templates/\nHTML-Template"]
    WeasyPrint["WeasyPrint\nHTML → PDF"]
    Output["pdfs/\n*.pdf"]

    FormData --> Services --> PdfGen
    Template --> PdfGen
    PdfGen --> WeasyPrint --> Output
```

---

## 8. Konfigurationsmodell

Die gesamte Konfiguration der Anwendung erfolgt über **Umgebungsvariablen** (optional aus einer `.env`-Datei). Pydantic Settings validiert und typisiert die Werte beim Start.

```mermaid
graph TD
    EnvFile[".env-Datei\n(optional)"]
    EnvVars["Umgebungsvariablen\nAPP_COMPANY__NAME\nAPP_COLORS__PRIMARY\nAPP_SMB__ENABLED\n..."]
    Pydantic["AppSettings\n(Pydantic BaseSettings)"]
    CompanyConf["CompanyConfig"]
    ColorConf["ColorsConfig"]
    SmbConf["SmbConfig"]
    FlaskConf["app.config['formflow']"]

    EnvFile --> EnvVars
    EnvVars --> Pydantic
    Pydantic --> CompanyConf
    Pydantic --> ColorConf
    Pydantic --> SmbConf
    Pydantic --> FlaskConf
```

### Umgebungsvariablen-Referenz

| Variable | Typ | Beschreibung |
|---|---|---|
| `APP_COMPANY__NAME` | String | Firmenname (erscheint in Web-UI und PDFs) |
| `APP_COMPANY__ADDRESS` | String | Firmenadresse (Footer) |
| `APP_COMPANY__LOGO_FILENAME` | String | Logo-Dateiname (muss in `static/` liegen) |
| `APP_COLORS__PRIMARY` | String | Primärfarbe als Hex-Code (z. B. `#0056b3`) |
| `APP_COLORS__TEXT_DARK` | String | Textfarbe dunkel |
| `APP_COLORS__TEXT_LIGHT` | String | Textfarbe hell |
| `APP_COLORS__BG_LIGHT` | String | Heller Hintergrund |
| `APP_SMB__ENABLED` | Boolean | SMB-Upload aktivieren (`true`/`false`) |
| `APP_SMB__SERVER` | String | Hostname/IP des SMB-Servers |
| `APP_SMB__SHARE` | String | Name der SMB-Freigabe |
| `APP_SMB__FOLDER` | String | Unterordner innerhalb der Freigabe (optional) |
| `APP_SMB__USERNAME` | String | SMB-Benutzername |
| `APP_SMB__PASSWORD` | String | SMB-Passwort |

---

*Zurück zur [Wiki-Startseite](Home.md)*
