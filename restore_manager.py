# Restore_manager

"""
restore_manager.py = moduł odpowiedizalny za przywracanie danythc z kopii zapasowych (ZIP).
Integruje się z:
- utils.logger (logowanie operacji)
- utils.checksum (weryfikacja integralności)
- db_manger (rejestracja historii przywracania)
"""

import os
import shutil
import zipfile
from datetime import datetime

from utils.logger import get_logger
from utils.checksum import verify_chcecksum
from db_manager import DatabaseManager


class RestoreManager:
    """
    Klasa odpowiedzilna za przywracanie kopii zapasowych.
    obsługuje:
    - rozpakowywanie archiwum ZIP
    - weryfikację integralność backupu
    - rejestrację przywracania w bazie danych.
    """

    def __init__(self, config: dict = None, logger=None, db=None):
        """
        Konstruktor klasy RestoreManager.
        :param config: słownik konfiguracji (ścieżki domyślne, np. restore_directory)
        :param logger: instancja loggera
        :param db: instancja bazy danych (DatabaseManager)
        """
        self.config = config or {}
        self.logger = logger or get_logger("RestoreManager")
        self.db = db or DatabaseManager(logger=self.logger)

        self.default_backup_dir = self.config.get("backup_directory", "backups")
        self.default_restore_dir = self.config.get("restore_directory", "restored_files")

        # Utworzenie katalogu do przywracania, jeśli nie istnieje
        os.makedirs(self.default_backup_dir, exist_ok=True)
        self.logger.info(f"RestoreManager zainicjalizowany. Folder przywracania: {self.default_restore_dir}")

    # Główna funkcja - przywracanie backup
    def restore_backup(self, backup_file: str, destination: str=None, expected_hash: str=None):
        """
        Główna funkcja przywracania backupu ZIP.
        :param backup_file: ścieżka do pliku ZIP (backup)
        :param destination: katalog docelowy (obcjonalne)
        :param expected_hash: oczekiwany hash do weryfikacji integralności
        """

        try:
            # 1. Ustalamy ścieżke
            destination = destination or self.default_restore_dir
            os.makedirs(destination, exist_ok=True)
            
            backup_path = os.path.join(self.default_backup_dir, backup_file)
            if not os.path.exists(backup_path):
                self.logger.error(f"Plik backup nie istnieje: {backup_path}")
                return False
            
            self.logger.info(f"Rozpoczynam przywracanie backupu: {backup_path}")
            
            # 2. Weryfikajca integralności (jeśli mamy hash)
            if expected_hash:
                ok = verify_chcecksum(backup_path, expected_hash, logger=self.logger)
                if not ok:
                    self.logger.error(f"Integralność backupu niepoprawna! Plik mógł zostać zmieniony: {backup_file}")
                    self._register_restore(backup_file, destination, "FAILED_HASH")
                    return False
                else:
                    self.logger.info("Weryfikacja integralności zakończona pomyślnie")
                
            # 3. Rozpakowanie archiwum ZIP
            with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                zip_ref.extractall(destination)
                self.logger.info(f"Backup został rozpakowany do: {destination}")

            # 4. Zarejestrowaie operacji w bazie
            self._register_restore(backup_file, destination, "OK")

            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas przywracania backupu: {e}")
            self._register_restore(backup_file, destination, "FAILED")
            return False
        
    # Wewnętrzne funckej pomocnicze
    def list_backups(self):
        """
        Zwraca listę dostępnych backupów w folderze backups/
        """

        backups = [
            f for f in os.listdir(self.default_backup_dir)
            if f.endswith(".zip")
        ]
        self.logger.debug(f"Znaleziono {len(backups)} backupów w katalogu {self.default_backup_dir}")
        return backups
    
    def _register_restore(self, backup_name: str, destination: str, status: str):
        """
        Zapisuje informacje o operacji przywracania do bazy dancyh
        """
        try:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db.cursor.execute("""
               CREATE TABLE IF NOT EXISTS restores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_name TEXT,
                date TEXT,                 
                destination TEXT,
                status TEXT
                )
            """)
            self.db.cursor.execute("""
                INSERT INTO restores (backup_name, date, destination, status)
                VALUES (?, ?, ?, ?)
            """, (backup_name, date_str, destination, status))
            self.db.conn.commit()
            self.logger.info(f"Zarejestrowano operację przywracania: {backup_name} ({status})")
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisu do bazy danych: {e}")


# Test Manualny
if __name__ == "__main__":
    config = {
        "backup_directory": "backups",
        "restore_directiory": "restored_files",
    }

    manager = RestoreManager(config=config)
    backups = manager.list_backups()
    print("\nDostępne backupy:", backups)

    if backups:
        test_file = backups[-1] # ostatni backup
        manager.restore_backup(test_file)
