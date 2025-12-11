# Backup_manager
# moduł odpowiedzialny za tworzenie kopi zapasowych 
# Główny segment Całego porgramu

# dodać w przyszłości import shutil 

# ogolne
import os
import zipfile
from datetime import datetime

# moduły projektu
from .db_manager import DatabaseManager
from .mail_notifier import MailNotifier

# Utils
from .utils.logger import get_logger
from .utils.checksum import calculate_checksum, verify_checksum
from .utils.checksum import build_dir_manifest, save_manifest
from .utils.config import CONFIG

# Do google drive
try:
    from cloud_storage import GoogleDriveStorage
except ImportError:
    GoogleDriveStorage = None

# Edit 1. 21.10.2025 16:00 NARAZIE ROBIMY SZKIC STRUKTURY
# Edit 2. 21.10.2025 19:00 Zaczynamy wporwaadzać podstawwoe funkcjonalności
# Edit 3. 22.10.2025 19:00 Kończymy tworzyć funkcje
# Edit 4. dodajemy checksum.py, logger.py, db_manager do skryptu
# Edit 5. Test integracyjny backup manager i restore manager
# Edit 6. 04.11.2025 Rozszerzenie porgramu o możliwość wybrania pliku do backupu
# Edit 7. 08.11.2025 Dodajemy funkcje wysyłania miali z mail_notifier
# Edit 8. 11.11.2025 Proba naprawy wysyłania maila
# Edit 9. 13.11.2025 Ogolne poprawki, dodanie usuwania manifestów
# Edit 10. 15.11.2025 Dodanie wyboru wielu źródeł i zapis ścieżek do bazy danych
# Edit 11. 29.11.2025 Dodanie logiki do obsługi nowych funkcji bazy danych
# Edit 12. 30.11.2025 Dodanie funkcji wysyłania backupu na Google Drive urzywając nowgo skryptu c;oud_storage.py


"""
Notka 1. z 04.11.2025 17:20 odapalając test wybierania folderu nie zkomentowałem usuwania starych backupów
więc te z 2025-10-25 od 15:35-20:28 (5 roznych) zostało usunięte
Narazie zachowam manifesty ale potem dodam funkcje które je ususwa wraz z usunięciem backupów

# To Do dodać manifest dla wielokrotnych wątków!
"""

class BackupManager:
    # Klasa zarządzająca procesem tworzenia kopii zapasowych

    def __init__(self, config: dict = None, logger = None, db = None, mailer = None):
        """
        Konstruktor.
        :param config: słownik konfiguracji (ścieżki, opcje, limity)
        :param logger: instalacja loggera
        :param db: inicjalizacja DatabaseManager do zapisu histori bacupów
        : param mailer: instancja mailera
        """
        base_config = CONFIG.copy()
        if config:
            base_config.update(config) # Nadpisuje tylko to co podamy

        self.config = base_config
        self.logger = logger or get_logger("BackupManager")
        self.db = db or DatabaseManager(logger=self.logger)
        self.mailer = mailer or MailNotifier(config=self.config, logger=self.logger, db=self.db)

        # Ścieżka domyślna do backupów
        self.default_backup_dir = self.config.get("backup_directory", "backups")

        # Tworzenie katalogu backupów, jeśli nie istnieje
        os.makedirs(self.default_backup_dir, exist_ok=True)   
        self.logger.info(f"BackupManager zainicjowany. Folder backupów: {self.default_backup_dir}") 

        # Integracja z Google Drive
        self.cloud = None
        if self.config.get("enable_drive_upload") and GoogleDriveStorage is not None:
            creds_path = self.config.get("drive_credentials_path")
            folder_id = self.config.get("drive_folder_id")
            try:
                self.cloud = GoogleDriveStorage(credentials_path=creds_path, folder_id=folder_id, logger=self.logger)
                self.logger.info("Integracja z Google Drive została zainicjowana pomyslnie.")
            except Exception as e:
                self.logger.error(f"Nie udało się zainicjować GoogleDriveStorage: {e}")
        elif self.config.get("enable_drive_upload") and GoogleDriveStorage is None:
            self.logger.error("enable_drive_upload=True, ale brak modułu cloud_storage / wymaganych paczek Google API.")
        else:
            self.logger.info("Integracja z Google Drive jest wyłączona (enable_drive_upload=False).")

        
    def create_backup(self, source: str = None, destination: str = None, sources: list[str] | None = None):
        """
        Główna metoda tworzenia backupu.
        :param source: ścieżka źródłowa (jeśli różna od domyślej w config)
        :param sources: LISTA ścieżek źródłowych
        :param destination: ścieżka docelowa backupu (jeśli różna od domyślej w config)
        """

        # 1. Ustalenie ścieżki 
        # Source
        
        sources_list = self._collect_sources(source, sources)

        if not sources_list:
            self.logger.error("Brak poprawnych ścieżek tworzenie backupu przerwane")
            return
                 

        # 2. Ustalenie katalogu docelowego
        destination = destination or self.default_backup_dir
        os.makedirs(destination, exist_ok=True)

        
        
        # 3. Tworzymy nazwe pliku backup (backup_2025_10_22-10_23_11.zip)  
        timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        backup_name = f"Backup_{timestamp}.zip"
        backup_path = os.path.join(destination, backup_name)
        self.logger.info(f"Tworzenie backupu: {backup_name}")

        # 3.5 Tworzenie manifestu i dodanie go tam gdzie robi sie backup
        # Gdy mamy JEDEN katalog źródłowy
        # To można rozwinąć później
        # To Do dodać manifest dla wielokrotnych wątków!
        manifest_path = None
        if len(sources_list) == 1 and os.path.isdir(sources_list[0]):
            try:
                # Tworzenie manifestu dla źródłowego katalogu
                source_dir = sources_list[0]
                manifest = build_dir_manifest(source_dir, logger=self.logger)
                manifest_name = f"manifest_{timestamp}.json"
                manifest_dir = os.path.join(destination, "manifests")
                os.makedirs(manifest_dir, exist_ok=True)
                manifest_path = os.path.join(manifest_dir, manifest_name)
                save_manifest(manifest, manifest_path)
                self.logger.info(f"Zapisano manifest: {manifest_path}")
            except Exception as e:
                self.logger.error(f"Błąd przy tworzeniu manifestu: {e}")
        else:
            self.logger.info("Pominięto manifest: backup zawiera wiele ścieżek lub pojedyńcze pliki.")


        # 4. Archiwizacja
        try: 
            # Archiwizacja katalogów / plików do jedengo ZIP
            self._archive_sources(sources_list, backup_path)

            # 5. Obliczanie rozmiaru i hash backupu
            size_bytes = os.path.getsize(backup_path)
            file_hash = calculate_checksum(backup_path, logger=self.logger)
            
            # 5.5 Opcjonalny upload na Google Drive
            drive_link = None
            if self.cloud and self.config.get("enable_drive_upload", False):
                try:
                    drive_link = self.cloud.upload_file(backup_path)
                    self.logger.info(f"Bakup wysłany na Google Drive: {drive_link}")
                except Exception as e:
                    self.logger.error(f"Błąd podczas wysyłania backupu na Google Drive {e}")


            # Zapis listy ścieżek w formie tekstu
            sources_str = ";".join(os.path.abspath(p) for p in sources_list)

            # Zapis do logów i bazy
            self.logger.info(f"Backup zakończony: {backup_path} rozmiar={size_bytes}B, hash={file_hash}")

            self.db.add_backup_record(
                name=backup_name,
                path=backup_path,
                size=size_bytes,
                hash_value=file_hash,
                status="OK",
                sources=sources_str        
            )

            # Powiadomienie e-mail
            details = (f"Rozmiar: {size_bytes}B\n"
                       f"Hash: {file_hash}\n"
                       f"Ścieżka Backupu: {backup_path}\n"
                       f"Źródła:\n" + "\n".join(f"- {p}" for p in sources_list)
                       )

            if drive_link:
                details += f"\nLink Google Drive: {drive_link}"

            attachments = []

            if manifest_path and os.path.exists(manifest_path):
                attachments.append(manifest_path)

            log_dir = "logs"
            current_date = datetime.now().strftime("%Y-%m-%d")
            log_path = os.path.join(log_dir, f"backup_log_{current_date}.log")
            if os.path.exists(log_path):
                attachments.append(log_path)
            
            if not attachments:
                attachments = None

            self.mailer.notify_backup_result(
                backup_name,
                "OK",
                details,
                attachments = attachments
            )

        except Exception as e:
            self.logger.error(f"Wystąpił problem przy tworzeniu backupu: {e}")
            sources_str = ";".join(os.path.abspath(p) for p in sources_list)

            self.db.add_backup_record(
                name=backup_name,
                path=backup_path,
                size=0,
                hash_value=None,
                status="FAILED",
                sources=sources_str
            )
            self.mailer.notify_backup_result(
                backup_name,
                "FAILED",
                f"Błąd podczas tworzenia backupu: {e}"
            )
    
    def _collect_sources(self, source: str | None, sources: list[str] | None) -> list[str]:
        """
        Zbiera liste ścieżek do backupu na podstawie:
        - parametrów funkcji (source / sources)
        - confingu
        - interaktytwnego inputu
        """

        result: list[str] = []

        # 1. Jeśli jawnie podano listę źródeł - używamy jej
        if sources:
            result.extend(sources)

        # 2. Zgodność wsteczna: pojedyńczy 'source' (pn. z config lub wywołania)
        if source and source not in result:
            result.append(source)

        # 3. Jeśli nadal nic nie mamy - biezemy z config
        if not result:
            cfg_cource = self.config.get("source_directory")
            if cfg_cource:
                use_cfg = input(f"Użyć ścieżki z config ({cfg_cource}) jako źródła backupa? [T/n]: ").strip().lower()
                if use_cfg in ("", "t", "tak", "y", "yes"):
                    result.append(cfg_cource)

        # 4. Tryb interaktywny: pozwala dodać wiele ścieżęk
        if not result:
            self.logger.info("Tryb wyboru wielu ścieżęk. Pusta linia kończy dodawanie")
            while True:
                path = input("Podaj ścieżkę do pliku/folderu (ENTER kończy): ").strip()
                if not path:
                    break
                result.append(path)
        
        # 5. Walidacja - zostawiamy tylko istniejące ścieżki
        valid_sources: list[str] = []
        for path in result:
            if os.path.exists(path):
                valid_sources.append(path)
            else:
                self.logger.error(f"Ścieżka źródłowa nie istnieje i zostanie pominięta: {path}")

        return valid_sources

    
    def _archive_sources(self, sources: list[str], destination_zip: str):
        """
        Archiwizuje wiele katalogów / plikó do jednego archiwum ZIP.
        Każdy katalog trafia do osobnego folderu w ZIP (po nazwie katalogu)
        :param sources: lista ścieżek (pliki lub katalogi)
        :param destination_zip: ścieżka docelowa pliku ZIP
        """

        destination_abs = os.path.abspath(destination_zip)

        with zipfile.ZipFile(destination_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for src in sources:
                src_abs = os.path.abspath(src)
            
                if os.path.isdir(src_abs):
                    base_name = os.path.basename(src_abs.rstrip(os.sep)) or "root"
                    for root, _, files in os.walk(src_abs):
                        for file in files:
                            full_path = os.path.join(root, file)                        

                            # Nie pakujemy pliku ZIP do samego siebie
                            if os.path.abspath(full_path) == destination_abs:
                                self.logger.debug(f"Pominięto plik backupa wewnątrz katalogu: {full_path}")
                                continue

                            rel_path = os.path.relpath(full_path, src_abs)
                            archname = os.path.join(base_name, rel_path)
                            zipf.write(full_path, archname)
                    self.logger.debug(f"Zarchiwizowano katalog: {src_abs}")
                else:
                    # Pojedyńczy plik
                    archname = os.path.basename(src_abs)
                    if src_abs == destination_abs:
                        self.logger.debug(f"Pominięto plik backupa wewnątrz jatakigu: {src_abs}")
                        continue
                    zipf.write(src_abs, archname)
                    self.logger.debug(f"Zarchiwiziowano plik: {src_abs}")


  
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
                    # Usuwanie manifestów po nazwie backupu
                    base_name = os.path.basename(file_path)
                    ts = base_name.replace("Backup_", "").replace(".zip", "")
                    manifest_name = f"manifest_{ts}.json"
                    manifest_path = os.path.join(self.default_backup_dir, "manifests", manifest_name)
                    if os.path.exists(manifest_path):
                        os.remove(manifest_path)
                        self.logger.info(f"Usunięto powiązany manifest: {manifest_path}")
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
        return verify_checksum(backup_path, expected_hash, logger=self.logger)


    
    def _apply_profile_overrides(self, profile: dict):
        """
        Obcjonalnie nadpisuje kilka ustawień z profilu backup
        np.: odbiorce maila, ale nie rozwalając CONFIG
        """
        if not profile:
            return
        
        # Mail - jeśli w profilu jest recipient_email to go użyj
        recipient = profile.get("recipient_email")
        if recipient:
            self.config["recipient_email"] = recipient
            try:
                # Jeśli MailNotifier trzyma te dane w atrybucie
                self.mailer.recipient_email = recipient
            except AttributeError:
                self.logger.warning("Nie udało się ustawić recipient_email w mailerze z profilu.")
        # Narazie tylko mailer bo reszta jest obsłógiwana przy tworzeniu backupu
        # Gdy dodamy scheduler 2.0 można dodać np: backup_frequency, daily_report_


    # Nowa metoda do tworzenia backupu z profilu
    def create_backup_from_profile(self, profile_id: int | None = None):
        """
        Tworzy backup na podstawie profilu backupu zapisanego w bazie
        Jeśli profil_id = None, używa profilu domyslnego (is_default = 1)
        """
        # Upewnienie się że DatabaseManger ma odpowienie metody
        if not hasattr(self.db, "get_backup_profile") or not hasattr(self.db, "get_default_backup_profile"):
            self.logger.error("DatabaseManger nie obsługuje profili backupu (brak metod get_backup_profile/get_default_backup_profile).")
            return
        
        # 1. Pobieranie profili
        if profile_id is None:
            profile = self.db.get_default_backup_profile()
            if not profile:
                self.logger.error("Brak domyslnego profilu backupu w bazie danych")
                return
        else:
            profile = self.db.get_backup_profile(profile_id)
            if not profile:
                self.logger.error(f"Nie znaleziono profilu backupu o id={profile_id}.")
                return
            
        p_id = profile.get("id")
        p_name = profile.get("name")

        # 2. Pobieranie źródła 
        sources_str = profile.get("sources") or ""
        sources_list = [p.strip() for p in sources_str.split(";") if p.strip()]

        if not sources_list:
            self.logger.error(f"Profil backupu (id={p_id}, name={p_name}) nie ma zdefiniowanych źródeł.")
            return 

        # 3. Katalog docelowy
        destination = profile.get("backup_directory") or self.default_backup_dir

        # 4. Nadpisanie konfiguracji mailer 
        self._apply_profile_overrides(profile)

        self.logger.info(f"Tworzenie backupu na podstawie profilu (id={p_id}, name={p_name}) do katalogu: {destination}")

        # 5. Użycie creator_backup
        self.create_backup(destination=destination, sources=sources_list)
"""
Uwagi do struktury:
- create_backup() - Główna metoda któą będziemy wywoływać w main.py
- Prywatne metody (prefix _) służą do wydzolonych konkretnych zadań
- W konstruktorze przekazujemy: konfigurację, logger i dostęp do bazy - dzięki temu klasa wspułpracuje z innymi
- Ważne aby pamiętac o logwaniu i o dostępu do bazy aby system mogl śledzić historie i wyłapywać błędy
"""
# Test nr 2 
"""
Test na robienie backupa z kilku folderów
"""
# if __name__ == "__main__":
#     config = {
#         # "source_directory": "test_data",  # fodler do zbacupowania
#         # Narazie ukrywamy dla testu wyboru folderu
#         "backup_directory": "backups",  # tu zapisujemy backup
#     }

#     manager = BackupManager(config=config)

#     # list afoldeów do balcup
#     test_sources = [
#         "for zip",
#         "for zip2",
#         "NOwe.txt"
#     ]

#     # Tworzymy backup
#     manager.create_backup(sources=test_sources)  

#     # Sprawdamy co jest w bazie
#     print("Ostatnie backupy")
#     history = manager.db.get_backup_history(limit=5)
#     for name, date, path, size, status, sources in history:
#         print(f"{date} | {name} | {status} | {size} B")
#         print(f"sources: {sources}")

# Test 3 
if __name__ == "__main__":
    logger = get_logger("BackupTest")
    db = DatabaseManager(logger=logger)

    profile_id = db.create_backup_profile(
        name="Adam Mickiewicz",
        sources=r"C:\Users\Admin\Desktop\STUDIA\Inzynierka\Skrypty\Backend\for zip;"
        r"C:\Users\Admin\Desktop\STUDIA\Inzynierka\Skrypty\Backend\for zip2;"
        r"C:\Users\Admin\Desktop\STUDIA\Inzynierka\Skrypty\Backend\NOwe.txt;"
        r"C:\Users\Admin\Desktop\STUDIA\Inzynierka\Skrypty\Backend\drive_test_file.txt",
        backup_directory="backups_test_profile",
        backup_frequency="daily",
        daily_report_enable=False,
        recipient_email="backup.system.receiver@gmail.com",
        is_default=True,
    )

    manager = BackupManager(config=CONFIG, logger=logger, db=db)

    manager.create_backup_from_profile(profile_id)

    db.close()

