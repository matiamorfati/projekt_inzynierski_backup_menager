# Restore_manager

"""
restore_manager.py = moduł odpowiedizalny za przywracanie danythc z kopii zapasowych (ZIP).
Integruje się z:
- utils.logger (logowanie operacji)
- utils.checksum (weryfikacja integralności)
- db_manger (rejestracja historii przywracania)
"""
# Dodać import shutil
# EDIT 2. 17.11.2025 Dodajemy ulepszenia: Podgląd zawartości backupu, wybór elementu do przywrócenia
# EDIT 3. 17.11.2025 Dodajemy powiadomienia mailwoe oraz wprowadzenie pobierania z bazy danych nazw plików/folderów z ZIP
import os
import zipfile
from datetime import datetime

from db_manager import DatabaseManager
from mail_notifier import MailNotifier

from utils.logger import get_logger
from utils.checksum import verify_checksum
from utils.config import CONFIG

class RestoreManager:
    """
    Klasa odpowiedzilna za przywracanie kopii zapasowych.
    obsługuje:
    - rozpakowywanie archiwum ZIP
    - weryfikację integralność backupu
    - rejestrację przywracania w bazie danych.
    """

    def __init__(self, config: dict = None, logger=None, db=None, mailer=None):
        """
        Konstruktor klasy RestoreManager.
        :param config: słownik konfiguracji (ścieżki domyślne, np. restore_directory)
        :param logger: instancja loggera
        :param db: instancja bazy danych (DatabaseManager)
        :param mailer: instancja MailNotifier
        """
        # Uzywamy tego samego co w backup_manager
        # Bez tego powoduje błędy z wysyłaniem maila
        base_config = CONFIG.copy()
        if config:
            base_config.update(config)

        self.config = base_config
        self.logger = logger or get_logger("RestoreManager")
        self.db = db or DatabaseManager(logger=self.logger)
        self.mailer = mailer or MailNotifier(config=self.config, logger=self.logger, db=self.db)
        
        self.default_backup_dir = self.config.get("backup_directory", "backups")
        self.default_restore_dir = self.config.get("restore_directory", "restored_files")

        # Utworzenie katalogu do przywracania, jeśli nie istnieje
        os.makedirs(self.default_restore_dir, exist_ok=True)
        self.logger.info(f"RestoreManager zainicjalizowany. Folder przywracania: {self.default_restore_dir}")
    
    def _get_today_log_path(self) -> str | None:
        """
        Zwraca ścieżkę do dzisiejszego pliku logów (jeśli istnieje)
        Zakładamy format jak w logger.py
        """
        logs_dir = self.config.get("log_directory", "logs")
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file = f"backup_log_{today_str}.log"
        path = os.path.join(logs_dir, log_file)
        return path if os.path.exists(path) else None

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
            
            # 1.5. Pobieramy expected_hash 
            if expected_hash is None:
                meta = self.db.get_backup_by_name(backup_file)
                if meta and meta.get("hash"):
                    expected_hash = meta["hash"]
                    self.logger.info("Pobrano hash backup z bazy danych")

            self.logger.info(f"Rozpoczynam przywracanie backupu: {backup_path}")
            
            # 2. Weryfikajca integralności (jeśli mamy hash)
            if expected_hash:
                ok = verify_checksum(backup_path, expected_hash, logger=self.logger)
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

            # 5. Powiadomienia e-mail o powodzeniu
            try:
                if getattr(self, "mailer", None):
                    log_path = self._get_today_log_path()
                    attachments = [log_path] if log_path else None

                    details = f"Pełne przywrócenie backup do katalogu: {destination}"
                    self.mailer.notify_restore_result(
                        backup_name=backup_file,
                        status="OK",
                        destination=destination,
                        details=details,
                        attachments=attachments
                    )
            except Exception as e:
                self.logger.error(f"Nie udało się wysłać powiadomienia e-mail (restore OK): {e}")
            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas przywracania backupu: {e}")
            dest = destination or self.default_restore_dir
            self._register_restore(backup_file, dest, "FAILED")

            # Powiadomienie e-mail o błędzie
            try:
                if getattr(self, "mailer", None):
                    log_path = self._get_today_log_path()
                    attachments = [log_path] if log_path else None

                    details = f"Błąd podczas przywracania backupu: {e!r}"
                    self.mailer.notify_restore_result(
                        backup_name=backup_file,
                        status="FAILED",
                        destination=dest,
                        details=details,
                        attachments=attachments
                    )
            except Exception as e2:
                self.logger.error(f"Nie udało się wysłać powiadomienie e-mail (restore FAILED): {e2}")
            
            return False
        
    # Wewnętrzne funckej pomocnicze
    def list_backups(self):
        """
        Zwraca listę dostępnych backupów w folderze backups/
        """
        if not os.path.isdir(self.default_backup_dir):
            self.logger.warning(f"Folder backupów nie istnieje: {self.default_backup_dir}")
            return []

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

    # Nowe Podgląd zawartości ZIP
    def preview_backup_contents(self, backup_file: str) -> list[str]:
        """
        Zwraca listę plików z archiwum ZIP (pełne ścieżki)
        :param backup_file: nazwa pliku backup
        """
        backup_path = os.path.join(self.default_backup_dir, backup_file)
        if not os.path.exists(backup_path):
            self.logger.error(f"Plik backup nie istnieje: {backup_path}")
            return []
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                names = zip_ref.namelist()
            self.logger.info(f"Zawartość backupu {backup_file}: {len(names)} elementów")
            return names
        except Exception as e:
            self.logger.error(f"Błąd podczas odczytu zawartości backupu: {e}")
            return []
        
    # Przywracanie danego katalogu/pliku z ZIPa
    def restore_selected(self, backup_file: str, selection: list[str], destination: str = None, expected_hash: str = None) -> bool:
        """
        Przywraca tylko wybrane pliki/foldery z ZIP
        :param backup_file: nazwa pliku
        :param selection: lista prefixów ścieżek wewnątrz ZIP któe przywracamy
        :param destination: katalog docelowy
        """
        destination = destination or self.default_restore_dir
        os.makedirs(destination, exist_ok=True)

        backup_path = os.path.join(self.default_backup_dir, backup_file)
        if not os.path.exists(backup_path):
            self.logger.error(f"Plik backup nie istnieje: {backup_path}")
            return False
        
        self.logger.info(f"Przywracamy WYBRANE elementy z backup: {backup_path}")
        self.logger.info(f"Wybrane prefiksy: {selection}")

        try:
            # 1. Weryfikacja integralności 
            if expected_hash:
                ok = verify_checksum(backup_path, expected_hash, logger=self.logger)
                if not ok:
                    self.logger.error(f"Integralność backupu niepoprawna, plik mógł zostać zmieniony: {backup_file}")
                    self._register_restore(backup_file, destination, "FAILED_HASH_PARTIAL")
                    return False
                else:
                    self.logger.info("Weryfikacja integralności zakończona pomyślnie")
                
            # 2. Wyciągnięcie tylko pasujących elementów
            with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                all_members = zip_ref.namelist()
                to_extract = []

                # jeśli user poda katalog baz '/' dodajemy go
                normalized_roots = []
                for pref in selection:
                    if not pref:
                        continue
                    pref_norm = pref.replace("\\", "/").rstrip("/")
                    normalized_roots.append(pref_norm)

                for member in all_members:
                    m_norm = member.replace("\\", "/")
                    for root in normalized_roots:
                        if m_norm == root:
                            to_extract.append(member)
                            break
                        if m_norm.startswith(root + "/"):
                            to_extract.append(member)
                            break
                                # tu
                if not to_extract:
                    self.logger.warning("Brak plików pasujących do wskazanych prefiksów - nic nie przywrócono")
                    return False

                for member in to_extract:
                    zip_ref.extract(member, destination)

            self.logger.info(f"Przywrócono {len(to_extract)} elementów do: {destination}")
            self._register_restore(backup_file, destination, "OK_PARTIAL")

            try:
                if getattr(self, "mailer", None):
                    log_path = self._get_today_log_path()
                    attachments = [log_path] if log_path else None
                    
                    chosen = selection or []
                    details = f"Częściowe przywrócenie z backupu\nWybranie elementy:\n" + "\n".join(chosen)
                    self.mailer.notify_restore_result(
                        backup_name=backup_file,
                        status="OK_PARTIAL",
                        destination=destination,
                        details=details,
                        attachments=attachments
                    )
            except Exception as e:
                self.logger.error(f"Nie udało się wysłać powiadomienia e-mail (restore partial): {e}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas częściowego przywracania backupu: {e}")
            self._register_restore(backup_file, destination, "FAILED_PARTIAL")
            return False

    # Wybieranie co przywracamy
    def restore_interactive(self):
        """
        Prosty tryb interaktywny:
        - pokozuje listę dostępnych bakcupów
        - pozwala wybrać jeden
        - pokazuje główne katalogi/plik w backupie
        - pozwala wybrać, co przywróćić
        """
        backups = self.list_backups()
        if not backups:
            print("Brak dostępnych backupów")
            return
        
        print("Dostępne backupy:")
        for idx, name in enumerate(backups, start=1):
            print(f"{idx}. {name}")

        choice = input("Wybierz numer backupu do przywrócenia (Enter = ostatni): ").strip()
        if not choice:
            backup_file = backups[-1]
        else:
            try:
                idx = int(choice)
                backup_file = backups[idx - 1]
            except (ValueError, IndexError):
                print("Nieprawidłowy wybór.")
                return
            
        # Podgląd zawartości  
        contents = self.preview_backup_contents(backup_file)
        if not contents:
            print("Nie udało się odczytać zawartości backupu")
            return
        
        # Wyznacz "rooty" (główne katalogi/pliki)
        roots = set()
        for item in contents:
            parts = item.split("/", 1)
            roots.add(parts[0])

        roots = sorted(roots)
        print("\nGłówne elementy w backupie:")
        for idx, r in enumerate(roots, start=1):
            print(f"{idx}. {r}")

        choice_root = input("Wybierz numer katalogu/elementu do przywrócenia (Enter = ostatni): ").strip()
        if not choice_root:
            # Wtedy prełne przywrócenie
            self.restore_backup(backup_file)
            return

        try:
            idx = int(choice_root)
            selected_root = roots[idx - 1]
        except (ValueError, IndexError):
            print("Nieprawidłowy wybór")
            return
        

        # Przywrócenie wybranego "roota"
        print(f"Przywracanie tylko: {selected_root}")
        self.restore_selected(backup_file, [selected_root])


# Przeporwadzić test 
# Test Manualny
if __name__ == "__main__":
    config = {
        "backup_directory": "backups",
        "restore_directory": "restored_files",
    }

    manager = RestoreManager(config=config)
    manager.restore_interactive()