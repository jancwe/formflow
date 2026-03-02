# Contributing

## Repository-Einstellungen für Maintainer

### CI-Workflow für Copilot-PRs

Damit CI-Workflows bei von Copilot erstellten Pull Requests automatisch ohne manuelle Freigabe laufen, muss folgende Repository-Einstellung gesetzt sein:

**Settings → Actions → General → „Approval for running fork pull request workflows from contributors"**
→ Wert: **„Require approval for first-time contributors who are new to GitHub"**

Diese Einstellung kann nur über die GitHub-Weboberfläche vorgenommen werden. Sie stellt sicher, dass nur wirklich neue GitHub-Nutzer eine manuelle Freigabe benötigen, während bekannte Mitwirkende (inkl. Copilot nach einmaliger Freigabe) automatisch CI-Läufe erhalten.

> **Hinweis:** Copilot muss einmalig manuell freigegeben werden. Danach läuft der CI-Workflow bei jedem Copilot-PR automatisch.
