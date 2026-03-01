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
