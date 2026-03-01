import os
import subprocess
import time
import pytest
import requests

import shutil

# Integrationstest für den SMB-Upload
def test_smb_upload():
    """Testet den gesamten Prozess vom Ausfüllen des Formulars bis zum SMB-Upload."""
    # 1. Vorschau anfordern und file_id extrahieren
    preview_response = requests.post(
        "http://localhost:8080/preview/notebook_handover",
        data={
            "user": "test-user",
            "handover_date": "2026-03-01",
            "condition": "Neuwertig",
            "accessories": "Netzteil",
            "signature_employee": "Test Signature"
        }
    )
    assert preview_response.status_code == 200

    # Extrahiere die file_id aus der Antwort
    file_id = ""
    for line in preview_response.text.splitlines():
        if "/confirm/notebook_handover/" in line:
            file_id = line.split("/confirm/notebook_handover/")[1].split("\"")[0]
            break
    
    assert file_id, "Konnte die file_id nicht aus der Vorschau-Antwort extrahieren."

    # 2. Bestätigung senden
    confirm_response = requests.post(
        f"http://localhost:8080/confirm/notebook_handover/{file_id}",
        data={
            "user": "test-user",
            "handover_date": "2026-03-01",
            "condition": "Neuwertig",
            "accessories": "Netzteil",
            "signature_employee": "Test Signature"
        }
    )
    assert confirm_response.status_code == 200

    # 3. Überprüfen, ob die Datei im smb_data-Verzeichnis existiert
    # Warte kurz, um sicherzustellen, dass die Datei geschrieben wurde
    time.sleep(2)
    smb_files = os.listdir("smb_data")
    assert any("notebook_handover_test-user" in f for f in smb_files), "PDF-Datei wurde nicht im smb_data-Verzeichnis gefunden."


def test_smb_fallback_when_server_offline():
    """Testet, dass bei nicht erreichbarem SMB-Server lokal gespeichert wird
    und der Benutzer eine Warnung mit Download-Link erhält."""

    # 1. SMB-Server stoppen
    subprocess.run(["docker", "stop", "formflow_smb-server_1"], check=False, capture_output=True)
    # Kurz warten bis der Container tatsächlich gestoppt ist
    time.sleep(2)

    try:
        # 2. Vorschau anfordern
        preview_response = requests.post(
            "http://localhost:8080/preview/notebook_handover",
            data={
                "user": "fallback-test",
                "handover_date": "2026-03-01",
                "condition": "Neuwertig",
                "accessories": "Netzteil",
                "signature_employee": "Test Signature"
            }
        )
        assert preview_response.status_code == 200

        # file_id extrahieren
        file_id = ""
        for line in preview_response.text.splitlines():
            if "/confirm/notebook_handover/" in line:
                file_id = line.split("/confirm/notebook_handover/")[1].split("\"")[0]
                break
        assert file_id, "Konnte die file_id nicht aus der Vorschau-Antwort extrahieren."

        # 3. Bestätigung senden
        confirm_response = requests.post(
            f"http://localhost:8080/confirm/notebook_handover/{file_id}",
            data={
                "user": "fallback-test",
                "handover_date": "2026-03-01",
                "condition": "Neuwertig",
                "accessories": "Netzteil",
                "signature_employee": "Test Signature"
            }
        )
        assert confirm_response.status_code == 200

        html = confirm_response.text

        # 4. Warnung wird angezeigt
        assert "alert-warning" in html, "Fallback-Warnung wird nicht angezeigt."
        assert "SMB-Server konnte nicht erreicht werden" in html, "Warnungstext fehlt."

        # 5. Download-Button ist vorhanden
        assert "PDF herunterladen" in html, "Download-Button fehlt."
        assert 'download' in html, "Download-Attribut fehlt."

        # 6. Dateiname aus der Warnung extrahieren und prüfen ob die Datei lokal existiert
        # Der Dateiname steht im HTML nach "gespeichert unter: "
        import re
        match = re.search(r'gespeichert unter: (notebook_handover_fallback-test[^<\s]+\.pdf)', html)
        assert match, "Dateiname konnte nicht aus der Warnung extrahiert werden."
        local_filename = match.group(1)

        time.sleep(1)
        pdf_files = os.listdir("pdf_output")
        assert local_filename in pdf_files, f"PDF '{local_filename}' wurde nicht in pdf_output gefunden. Vorhanden: {pdf_files}"

        # 7. Download-Link zeigt auf die richtige Datei
        assert f"/pdf/{local_filename}" in html, "Download-Link verweist nicht auf die korrekte Datei."

    finally:
        # SMB-Server wieder starten
        subprocess.run(["docker", "start", "formflow_smb-server_1"], check=False, capture_output=True)
        time.sleep(3)
