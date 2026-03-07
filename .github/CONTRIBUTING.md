# Contributing

## Repository-Einstellungen für Maintainer

### CI-Workflow für Copilot-PRs

Damit CI-Workflows bei von Copilot erstellten Pull Requests automatisch ohne manuelle Freigabe laufen, muss folgende Repository-Einstellung gesetzt sein:

**Settings → Actions → General → „Approval for running fork pull request workflows from contributors"**
→ Wert: **„Require approval for first-time contributors who are new to GitHub"**

Diese Einstellung kann nur über die GitHub-Weboberfläche vorgenommen werden. Sie stellt sicher, dass nur wirklich neue GitHub-Nutzer eine manuelle Freigabe benötigen, während bekannte Mitwirkende (inkl. Copilot nach einmaliger Freigabe) automatisch CI-Läufe erhalten.

> **Hinweis:** Copilot muss einmalig manuell freigegeben werden. Danach läuft der CI-Workflow bei jedem Copilot-PR automatisch.

## Coding-Stil & pre-commit-Hooks

Dieses Projekt verwendet [pre-commit](https://pre-commit.com/) zur automatischen Prüfung des Coding-Stils vor jedem Commit.

### Einmalige Einrichtung (nach dem Clonen)

```bash
bash setup_dev.sh
```

Oder manuell:

```bash
pip install pre-commit
pre-commit install
```

### Was wird geprüft?

| Hook | Prüft |
|---|---|
| `ruff` | Python-Linting (Fehler, Importe, Code-Qualität) |
| `ruff-format` | Python-Formatierung (konsistenter Stil) |
| `prettier` | JavaScript- und HTML-Formatierung |
| `trailing-whitespace` | Leerzeichen am Zeilenende |
| `end-of-file-fixer` | Fehlende Newline am Dateiende |
| `check-yaml` | YAML-Syntax |

### CI-Absicherung

Auch ohne lokale pre-commit-Installation prüft der CI-Workflow (GitHub Actions) bei jedem Pull Request automatisch den Code-Stil. Ein PR kann nur gemergt werden, wenn alle Checks grün sind.

