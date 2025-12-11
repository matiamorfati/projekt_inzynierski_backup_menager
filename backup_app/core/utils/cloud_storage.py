# cloud_storage.py
"""
Obsługuje wysyłanie backupu na Google Drive

Wymagane paczki:
py -m pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib
"""

# Edit 1. 30.11.2025 Stworzenie głównej kalsy i integracja z Drive
# Edit 2. 02.12.2025 Poprawa niedziałjącego wysyłania do drive i dodanie fuinkcji pobierania z Drive

from __future__ import annotations

from utils.logger import get_logger
from utils.config import CONFIG

import os
import io
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from googleapiclient.http import MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveStorage:
    """
    Wrapper na Google Drive API do wysyłania plików
    Używa OAuth (działa jako zwykły użytkownik Google, nie service account)
    """

    def __init__(self, credentials_path: str, folder_id: Optional[str] = None, logger=None, token_path: Optional[str] = None):
        """
        :param credentials_path: ścieżka do pliku JSON z kluczem konta serwisowego
        :param folder_id: ID folderu w google Drive, do którego mają trafić pliki
        :param token_path: ścieżka do pliku token.json
        """
        self.logger = logger or get_logger("GoogleDriveStorage")
        self.client_secret_path = credentials_path
        self.folder_id = folder_id

        if token_path is None:
            # Domyślnie zapisuje token obok client_secret.json
            base_dir = os.path.dirname(self.client_secret_path) or "."
            token_path = os.path.join(base_dir, "token.json")
        self.token_path = token_path

        # Upewnienie się że folder client_secret/token istnieje
        Path(os.path.dirname(self.client_secret_path) or ".").mkdir(parents=True, exist_ok=True)

        if not os.path.exists(credentials_path):
            self.logger.error(f"Nie znaleziono pliku z kluczem Google Drive: {credentials_path}")
            raise FileNotFoundError(f"Nie znaleziono pliku z kluczem Google Drive: {credentials_path}")

        

        self.creds: Credentials | None = None
        self._load_credentials()

        self.service = build("drive", "v3", credentials=self.creds)
        self.logger.info("Zainicjowano połączenie z Google Drive API (OAuth)")

    def _load_credentials(self) -> None:
        """
        Ładuje token z pliku lub przechodzi proces OAuth (przeglądarka + logowanie), a następnie 
        zapisuje token do pliku
        """
        creds: Credentials | None = None

        # 1. Próba wczytania istniejącego tokenu
        if os.path.exists(self.token_path):
            self.logger.debug(f"Ładowanie istniejącego tokena z: {self.token_path}")
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                self.logger.error(f"Nie udało się wczytać istniejącego tokena OAuth: {e}")
                creds = None
            
        # 2. Jeśli nie mamy ważnych credów - odświeżamy lub przechodzimy pełny flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Token OAuth wygasł - próba odświeżenia")
                try: 
                    creds.refresh(Request())
                    self.logger.info("Token OAuth został odświeżony")
                except Exception as e:
                    self.logger.error(f"Nie udało się odswieżyć tokenu OAuth: {e}")

            if not creds or not creds.valid:
                # Pełny flow OAuth - otworzy przeglądarke
                self.logger.info("Proces OAuth rozpoczęty - ootworzy się przeglądarka do logowania")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0)
                self.logger.info("Proces OAuth zakończony pomyślnie")

                # Zapisanie tokenu
                try:
                    with open(self.token_path, 'w', encoding="utf-8") as token_file:
                        token_file.write(creds.to_json())
                    self.logger.info(f"Zapisano nowy token OAuth do pliku: {self.token_path}")
                except Exception as e:
                    self.logger.error(f"Nie udało się zapisać tokena OAuth do pliku: {e}")

        self.creds = creds


    def upload_file(self, local_path: str, remote_name: str | None = None, folder_id: str | None = None) -> str:
        """
        Wysyła plik na Google Drive (Zalogowanego użytkownika)
        :param local_path: lokalna ścieżka do pliku
        :param remote_name: nazwa pliku na Drive
        :param folder_id: ID folderu 
        Zwraca link do podglądu
        """
        if not os.path.exists(local_path):
            self.logger.error(f"Plik do wysłania nie istnieje: {local_path}")
            raise FileNotFoundError(f"Plik do wysłania nie istnieje: {local_path}")
        
        file_name = remote_name or os.path.basename(local_path)
        target_folder = folder_id or self.folder_id

        file_metadata: dict = {"name": file_name}
        if target_folder:
            file_metadata["parents"] = [target_folder]
        
        media = MediaFileUpload(local_path, resumable=False)

        created = self.service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields= "id, webViewLink"
            ).execute()

        
        file_id = created.get("id")
        web_link = created.get("webViewLink")

        self.logger.info(f"Wysłano plik na Google Drive: name={file_name}, id={file_id}")
        if web_link:
            self.logger.info(f"Link do pliku: {web_link}")
        
        return web_link or file_id
        
    def find_file_by_name(self, name: str) -> list[dict]:
        """
        Szuka plików o podanej nazwie na Google Drive
        Zwraca listę słowników z polami: id, name, modifiedTime, size
        """
        query = f"name = '{name}' and trashed = false"

        try:
            response = self.service.files().list(
                q=query,
                spaces = "drive",
                fields = "files(id, name, modifiedTime, size)",
                orderBy = "modifiedTime desc",
            ).execute()

            files = response.get("files", [])
            if not files:
                self.logger.warning(f"Nie znaleziono pliku o nazwie: {name} na Google Drive")
            else:
                self.logger.info(f"Znaleziono {len(files)} o nazwie {name} na Google Drive")
            return files
        except Exception as e:
            self.logger.error(f"Błąd podczas wyszukiwania pliku na Google Drive: {e}")
            return []
        
    
    def download_file(self, file_id: str, local_path: str) -> str:
        """
        Pobiera plik z Google Drive ba dysk lokalny.
        :param file_id: ID pliku na Drive
        :param: local_path: ścieżka, pod którą zapiszemy plik .zip
        Zwraca lokalną ścieżkę do pobranego pliku
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(local_path, "wb")
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    self.logger.debug(f"Pobieranie z Drive: {int(status.progress() * 100)}%")

            self.logger.info(f"Pobrano plik z Google Drive id={file_id} -> {local_path}")
            return local_path
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania pliku z Google Drive: {e}")
            raise
    
    

if __name__ == "__main__":
    """
    Prosty test: wysyła malutki plik testowy na Google Drive,
    używając ścieżek z CONFIG.
    """
    

    logger = get_logger("DriveTest")

    creds_path = CONFIG.get("drive_credentials_path", "credentials/client_secret.json")
    folder_id = CONFIG.get("drive_folder_id")

    storage = GoogleDriveStorage(
        credentials_path=creds_path,
        folder_id=folder_id,
        logger=logger
    )

    test_filename = "drive_test_file.txt"
    with open(test_filename, "w", encoding="utf-8") as f:
        f.write("Test wysyłania pliku na Google Drive z BackupManagera.\n")

    link = storage.upload_file(test_filename)
    logger.info(f"Testowy plik wysłany. Link/id: {link}")
