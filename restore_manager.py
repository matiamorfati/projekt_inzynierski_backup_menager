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
# EDIT 4. 02.12.2025 Dodajemy pobierania z Google Drive
import os
import zipfile
from datetime import datetime

from db_manager import DatabaseManager
from mail_notifier import MailNotifier

from utils.logger import get_logger
from utils.checksum import verify_checksum
from utils.config import CONFIG

try:
    from cloud_storage import GoogleDriveStorage
except ImportError:
    GoogleDriveStorage = None

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

        # Integracja z Google Drive 
        self.cloud = None
        if self.config.get("enable_drive_upload") and GoogleDriveStorage is not None:
            creds_path = self.config.get("drive_credentials_path")
            folder_id = self.config.get("drive_folder_id")
            try:
                self.cloud = GoogleDriveStorage(credentials_path=creds_path, folder_id=folder_id, logger=self.logger)
                self.logger.info("RestoreManager: integracja z Google Drive została zainicjowana.")
            except Exception as e:
                self.logger.error(f"RestoreManager: nie udało się zainicjowaćGoogleDriveStorage: {e}")
        elif self.config.get("enable_drive_upload") and GoogleDriveStorage is None:
            self.logger.error("RostoreManager: enable_drive_upload=True, ale brak modułu cloud_storage / paczek Google API.")
        else:
            self.logger.info("RestoreManager: integracja z Google Drive jest wyłączona")

    
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

    def download_backup_from_drive(self, backup_name: str, destination_dir: str | None = None ) -> str | None:
        """
        Pobiera plik backup o zadanej nazwie z Google Drive do lokalnego katalogu
        :param backup_name: nazwa pliku .zip na Drive
        :param destination_dir: katalog, gdzie zapiszemy plik (domyślnie self.default_backup_dir)
        Zwraca ścieżke do pobranego pliku lub None
        """
        if not self.cloud:
            self.logger.error("Integracja z Google Drive nie jest dostępna - nie można pobrać backupu")
            return None
        
        destination_dir = destination_dir or self.default_backup_dir
        os.makedirs(destination_dir, exist_ok=True)

        # Szukanie pliku o takiej nazwie na Drive
        files = self.cloud.find_file_by_name(backup_name)
        if not files:
            self.logger.error(f"Na Google Drive nie znaleziono pliku backup o nazwie: {backup_name}")
            return None
        
        file_meta = files[0]
        file_id = file_meta["id"]

        local_path = os.path.join(destination_dir, backup_name)

        try:
            self.cloud.download_file(file_id, local_path)
            return local_path
        except Exception:
            # logowanie już jest w download_file
            return None
        
    def restore_from_drive(self, backup_name: str, destination: str | None = None, expected_hash: str | None = None) -> bool:
        """
        Pobiera wskazany plik ZIP z Google Drive
        Wywołuje standardowe restore_backup() na lokalnym pliku
        """
        self.logger.info(f"Przywracanie backupu z Google Drive: {backup_name}")

        local_path = self.download_backup_from_drive(backup_name)
        if not local_path:
            self.logger.error("Nie udało się pobrać backupu z Google Drive - przerwano przywracanie.")
            return False
        
        local_name = os.path.basename(local_path)
        return self.restore_backup(local_name, destination=destination, expected_hash=expected_hash)
    
    def restore_from_drive_with_choice(self, backup_name: str, destination: str | None = None, expected_hash: str | None = None) -> bool:
        """
        Pobiera plik ZIP z Google Drive i pozawala wybrać:
        1) Pełne przywrócenie
        2) przywrócenie tylko wybranego katalogu/elementu (root)
        """
        if not self.cloud:
            self.logger.error("Integracja z Google Drive nie jest dostępna")
            print("Integracja z Google Drive nie jest dostępna")
            return False
        
        self.logger.info(f"Przywracanie backupu z Google Drvie (z wyborem): {backup_name}")
        print(f"\n[Pobieranie backupu z Google Drive] {backup_name}")

        # 1. Pobieranie ZIP-a do lokalnego katalogu backups/
        local_path = self.download_backup_from_drive(backup_name)
        if not local_path:
            self.logger.error("Nie udało się pobraćbackupu z Google Drive.")
            print("Nie udało się pobrać backupu z Google Drvie (sprawdź logi)")
            return False
        
        local_name = os.path.basename(local_path)

        # 2. Podgląd zawartości ZIP-a
        contents = self.preview_backup_contents(local_name)
        if not contents:
            self.logger.error("Nie udało się odczytać zawartości backupu")
            print("Nie udało się odczytać zawartości backupu (albo plik nie jest ZIP-em).")
            return False
        
        # 3. Wyznaczenie "rootów" - główne katalogi / pliki z backupu
        roots: set[str] = set()
        for item in contents:
            parts = item.split("/", 1)
            roots.add(parts[0])

        roots = sorted(roots)

        print("\nZnaleziono następujące główne elementy w backupie: ")
        for idx, r in enumerate(roots, start=1):
            print(f"{idx}. {r}")

        # 4. Wybór trybu przywracania
        print("\nCo chcesz zrobić?")
        print("1) Przywróć cały backup")
        print("2) Przywróć tylko wybrany katalog/element")
        choice = input("Wybór (Enter = 1): ").strip() or "1"

        match choice:
            case "1":
                # Pełne przywrócenie więc używamy istniejącej już funkcji
                return self.restore_backup(local_name, destination=destination, expected_hash=expected_hash)

            case "2":
                choice_root = input("Podaj numery elementów do przywrócenia(np: 1, 2, 3): ").strip()
                
                if not choice_root:
                    print("Nie podano żadnych numerów - przerwano")
                    return False
                
                try:
                    indexes = {int(x) 
                               for x in choice_root.replace(" ", "").split(",") 
                               if x
                            }
                except ValueError:
                    print("Nieprawidłowy format - przerwano")
                    return False
                
                selected_roots: list[str] = []
                for idx in sorted(indexes):
                    if 1 <= idx <= len(roots):
                        selected_roots.append(roots[idx - 1])
                    else:
                        print(f"Numer {idx} jest poza zakresem - pominięty.")

                if not selected_roots:
                    print("Żaden numer nie był poprawny - przerwano")
                    return False
                
                print(f"Przywracanie Elementów: ")
                for r in selected_roots:
                    print(f" - {r}")
                                    
                return self.restore_selected(
                    backup_file=local_name,
                    selection=selected_roots,
                    destination=destination,
                    expected_hash=expected_hash
                )
            
            case _:
                print("Nieprawidłowy wybór - przerwano.")
                return False





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
# Test Manualny 1.
# if __name__ == "__main__":
#     config = {
#         "backup_directory": "backups",
#         "restore_directory": "restored_files",
#     }

#     manager = RestoreManager(config=config)
#     manager.restore_interactive()



# Test Manualny 2. dla samego restore from dirve
# if __name__ == "__main__":
#     logger = get_logger("RestoreTest")
#     rm = RestoreManager(config=CONFIG, logger=logger)

#     backup_name = input("Podaj nazwę pliku backupu na Drive: ").strip()
#     if not backup_name:
#         print("Nie podano nazwy pliku.")
#     else:
#         ok = rm.restore_from_drive(backup_name)
#         print(f"Przywracanie zakończone: {ok}")

# test Manualny 3. Dla restore from drive with choicce
if __name__ == "__main__":
    logger = get_logger("RestoreTest")
    rm = RestoreManager(config=CONFIG, logger=logger)

    backup_name = input("Podaj nazwę pliku backupu na Drive: ").strip()
    if not backup_name:
        print("Nie podano nazwy pliku.")
    else:
        ok = rm.restore_from_drive_with_choice(backup_name)
        print(f"Przywracanie zakończone: {ok}")
