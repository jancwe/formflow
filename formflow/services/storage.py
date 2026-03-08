import glob
import logging
import os
import shutil
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PdfStorage:
    """Handles PDF storage: local file system and SMB share uploads."""

    def __init__(self) -> None:
        # SMB session is registered lazily on first use and reused for subsequent uploads.
        self._smb_session_registered: bool = False

    def store_pdf(self, temp_path: str, local_final: str, filename_parts: list[str], config: Dict[str, Any]) -> dict:
        """Speichert ein PDF entweder lokal oder auf dem SMB-Share.

        Wenn SMB deaktiviert ist, wird einfach umbenannt.
        Bei Netzwerk-Problemen wird lokal gespeichert und eine Warnung zurückgegeben.

        Returns:
            dict mit 'stored_via' ('smb' oder 'local') und optional 'warning'.
        """
        smb_config = config.get('smb', {})
        if not smb_config.get('enabled'):
            logger.info("SMB ist deaktiviert. Speichere PDF lokal.")
            os.rename(temp_path, local_final)
            return {"stored_via": "local", "filename": os.path.basename(local_final)}

        # Lazy import: only load smbprotocol when SMB is actually used
        import smbclient  # noqa: PLC0415

        logger.info("SMB ist aktiviert. Versuche Upload.")

        server = smb_config.get('server')
        share = smb_config.get('share')
        folder = smb_config.get('folder', '')
        username = smb_config.get('username')
        password = smb_config.get('password')

        if not (server and share and username and password):
            raise RuntimeError("SMB ist aktiviert, aber Zugangsdaten/Pfade fehlen.")

        try:
            # Register the SMB session lazily on first use; skip if already registered.
            if not self._smb_session_registered:
                smbclient.register_session(server, username=username, password=password)
                self._smb_session_registered = True

            folder_part = f"\\{folder}" if folder else ""
            remote_path = fr"\\{server}\{share}{folder_part}\{'_'.join(filename_parts)}.pdf"

            try:
                with open(temp_path, 'rb') as local_file:
                    with smbclient.open_file(remote_path, mode='wb') as remote_file:
                        shutil.copyfileobj(local_file, remote_file, length=65536)
            except Exception:
                # Session may have expired or been disconnected; attempt to re-register once.
                logger.info("SMB-Verbindung unterbrochen oder Session abgelaufen. Versuche erneute Session-Registrierung.")
                self._smb_session_registered = False
                smbclient.register_session(server, username=username, password=password)
                self._smb_session_registered = True
                with open(temp_path, 'rb') as local_file:
                    with smbclient.open_file(remote_path, mode='wb') as remote_file:
                        shutil.copyfileobj(local_file, remote_file, length=65536)

            logger.info(f"PDF erfolgreich auf SMB-Share gespeichert: {remote_path}")
            os.remove(temp_path)
            return {"stored_via": "smb", "filename": os.path.basename(remote_path)}
        except Exception as e:
            logger.warning(f"SMB-Upload fehlgeschlagen ({e}). Speichere PDF lokal als Fallback.")
            os.rename(temp_path, local_final)
            local_name = os.path.basename(local_final)
            return {
                "stored_via": "local",
                "filename": local_name,
                "warning": f"Der SMB-Server konnte nicht erreicht werden. Die Datei wurde lokal gespeichert unter: {local_name}"
            }

    def cleanup_temp_files(self, max_age_seconds: int = 3600) -> None:
        """Löscht verwaiste temporäre PDFs, die älter als max_age_seconds sind.

        Notwendig, da temp_*.pdf-Dateien bei Browser-Abbrüchen oder Session-Timeouts
        nie bereinigt werden und den Disk-Speicher des Hosts erschöpfen können.
        """
        now = time.time()
        cleaned = 0
        for path in glob.glob("pdfs/temp_*.pdf"):
            try:
                if now - os.path.getmtime(path) > max_age_seconds:
                    os.remove(path)
                    logger.info(f"Verwaiste temp-Datei gelöscht: {path}")
                    cleaned += 1
            except OSError as e:
                logger.warning(f"Konnte temp-Datei nicht löschen {path}: {e}")
        if cleaned:
            logger.info(f"Cleanup: {cleaned} verwaiste temp-Datei(en) gelöscht.")
