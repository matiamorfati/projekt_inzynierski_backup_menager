# Backup_manager
# moduł odpowiedzialny za tworzenie kopi zapasowych 
# Główny segment Całego porgramu

# ogolne
import os
import shutil 
import zipfile
from datetime import datetime

# moduły projektu
from utils.logger import get_logger
from utils.checksum import calculate_checksum
from utils.checksum import build_dir_manifest, save_manifest
from db_manager import DatabaseManager



# Edit 1. 21.10.2025 16:00 NARAZIE ROBIMY SZKIC STRUKTURY
# Edit 2. 21.10.2025 19:00 Zaczynamy wporwaadzać podstawwoe funkcjonalności
# Edit 3. 22.10.2025 19:00 Kończymy tworzyć funkcje
# Edit 4. dodajemy checksum.py, logger.py, db_manager do skryptu

class BackupManager:
    # Klasa zarządzająca procesem tworzenia kopii zapasowych
    # Na ten Moment (Edit 2.) obsługuje lokalny Backup katalogu / pliku. Oraz brak połączenia z bazą

    def __init__(self, config: dict = None, logger = None, db = None):
        """
        Konstruktor.
        :param config: słownik konfiguracji (ścieżki, opcje, limity)
        :param logger: instalacja loggera
        :param db: inicjalizacja DatabaseManager do zapisu histori bacupów
        """
        self.config = config or {}
        self.logger = logger or get_logger("BackupManager")
        self.db = db or DatabaseManager(logger=self.logger)

        # Ścieżka domyślna do backupów
        self.default_backup_dir = self.config.get("backup_directory", "backups")

        # Tworzenie katalogu backupów, jeśli nie istnieje
        os.makedirs(self.default_backup_dir, exist_ok=True)   
        self.logger.info(f"BackupManager zainicjowany. Folder backupów: {self.default_backup_dir}") 
        
    def create_backup(self, source: str = None, destination: str = None):
        """
        Główna metoda tworzenia backupu.
        :param source: ścieżka źródłowa (jeśli różna od domyślej w config)
        :param destination: ścieżka docelowa backupu (jeśli różna od domyślej w config)
        """
        # proces dziaąłnia
        # 1. Ustal ścieżki źródłowe i doeclowe
        # 2. Sprawdź czy źródło istnieje
        # 3. Utwórz nazwę katalogu/archiwum backupu (np. z timestampem)
        # 4. Wykonaj kopiowanie / archiwizacje
        # 5. Oblicz sumę kontrolną backupu
        # 6. Zapisz wpis w bazie danych (data, ścieżkam, rozmiar, hash, status)
        # 7. Obsłuż ewentualne błędy: logowanie + powiadomienie

        # 1. Ustalenie ścieżki 
        source = source or self.config.get("source_directory", ".")
        destination = destination or self.default_backup_dir

        # 2. Sprawdzamy czy źródło istnieje
        if not os.path.exists(source):
            self.logger.error(f"Ścieżka źródłowa '{source}' nie istnieje!")
            return
        
        # 3. Tworzymy nazwe pliku backup (backup_2025_10_22.zip)
        # ZASTANOWIĆ SIĘ CZY CHCEMY Z GODZINA/MINUTA/SEKONDA CZY SAMA DATA!!!
        timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        backup_name = f"Backup_{timestamp}.zip"
        backup_path = os.path.join(destination, backup_name)
        self.logger.info(f"Tworzenie backupu: {backup_name}")

        # 3.5 Tworzenie manifestu i dodanie go tam gdzie robi sie backup
        try:
            # Tworzenie manifestu dla źródłowego katalogu
            manifest = build_dir_manifest(source, logger=self.logger)
            manifest_name = f"manifest_{timestamp}.json"
            manifest_dir = os.path.join(destination, "manifests")
            os.makedirs(manifest_dir, exist_ok=True)
            manifest_path = os.path.join(manifest_dir, manifest_name)
            save_manifest(manifest, manifest_path)

            self.logger.info(f"Zapisano manifest: {manifest_path}")

        except Exception as e:
            self.logger.error(f"Błąd przy tworzeniu manifestu: {e}")

        """
        Manifest ma dane o plikach wewnątrz zipa (tak dla dodatkowej kontroli)
        """

        # 4. Archiwizacja
        try: 
            # Archiwizacja katalogu lub pliku
            self._archive_directory(source, backup_path)

            # dodane z checksum.py: Obliczanie rozmiaru i hash
            size_bytes = os.path.getsize(backup_path)
            file_hash = calculate_checksum(backup_path, logger=self.logger)
            
            # Zapis do logów i bazy
            self.logger.info(f"Backup zakończony: {backup_path} rozmiar={size_bytes}B, hash={file_hash})")

            self.db.add_backup_record(
                name=backup_name,
                path=backup_path,
                size=size_bytes,
                hash_value=file_hash,
                status="OK"                
            )

        except Exception as e:
            self.logger.error(f"Wystąpił problem przy tworzeniu backupu: {e}")
            self.db.add_backup_record(
                name=backup_name,
                path=backup_path,
                size=0,
                hash_value=None,
                status="FAILED"
            )
    

    def _archive_directory(self, source: str, destination_zip: str):
        """
        Archiwizuje katalog (np.: zip/tar) lub kopiuje zawartość.
        Zwraca ścierzke do utworzonego archiwum/backupu
        :param source: ścieżka źródłowa do zarchiwizowania
        :param destination_zip: ścieżka docelwoa pliku ZIP
        """
        
        if os.path.isdir(source):
            with zipfile.ZipFile(destination_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(source):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source)
                        zipf.write(full_path, rel_path)
            self.logger.debug(f"Zarchiwizowano katalog: {source}")
        else:
            with zipfile.ZipFile(destination_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(source, os.path.basename(source))
            self.logger.debug(f"Zarchiwizowano plik: {source}")
  
    def _cleanup_old_backups(self, limit: int = 5):
        """
        Obcjonalne: Usuwa stare backupy, Jeśli przekroczonyt został limit liczby/czasu
        :param limit: maksymalna liczba plików backupów, któe mają pozostać
        """
        
        backups = sorted(
            [
                os.path.join(self.default_backup_dir, f)
                for f in os.listdir(self.default_backup_dir)
                if f.endswith(".zip")
            ],
            key=os.path.getmtime,
        )
        
        if len(backups) > limit:
            to_delete = backups[: len(backups) - limit]
            for file_path in to_delete:
                try:
                    os.remove(file_path)
                    self.logger.info(f"Usunięto stary backup: {file_path}")
                except Exception as e:
                    self.logger.error(f"Nie można usunąć {file_path}: {e}")
              

    def _verify_backup(self, backup_path: str, expected_hash: str) -> bool:
        """
        Werifikuje integralność backupu (hash) - czy sie nie uszkodził.
        :param backup_path: ścierzka do pliku/archiwum backupu
        :param expected_hash: wcześniej obliczona suma kontrolna
        :return: True jeśli wszystko ok, False w przeciwnym razie
        """
        if not os.path.exists(backup_path):
            self.logger.error(f"Plik backup nie istnieje: {backup_path}")
            return False
        return True


"""
Uwagi do struktury:
- create_backup() - Główna metoda któą będziemy wywoływać w main.py
- Prywatne metody (prefix _) służą do wydzolonych konkretnych zadań
- W konstruktorze przekazujemy: konfigurację, logger i dostęp do bazy - dzięki temu klasa wspułpracuje z innymi
- Ważne aby pamiętac o logwaniu i o dostępu do bazy aby system mogl śledzić historie i wyłapywać błędy
"""
# Test nr 1
if __name__ == "__main__":
    config = {
        "source_directory": "test_data",  # fodler do zbacupowania
        "backup_directory": "backups",  # tu zapisujemy backup
    }

    manager = BackupManager(config=config)
    manager.create_backup()  # utworzy plik ZIP w folderze "backups"
    manager._cleanup_old_backups(limit=5)

