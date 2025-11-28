# Backup_manager
# moduł odpowiedzialny za tworzenie kopi zapasowych 
# Główny segment Całego porgramu

# dodać w przyszłości import shutil 

# ogolne
import os
import zipfile
from datetime import datetime

# moduły projektu
from db_manager import DatabaseManager
from mail_notifier import MailNotifier

# Utils
from utils.logger import get_logger
from utils.checksum import calculate_checksum, verify_checksum
from utils.checksum import build_dir_manifest, save_manifest
from utils.config import CONFIG


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
        -parametrów funkcji (source / sources)
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
if __name__ == "__main__":
    config = {
        # "source_directory": "test_data",  # fodler do zbacupowania
        # Narazie ukrywamy dla testu wyboru folderu
        "backup_directory": "backups",  # tu zapisujemy backup
    }

    manager = BackupManager(config=config)

    # list afoldeów do balcup
    test_sources = [
        "for zip",
        "for zip2"
    ]

    # Tworzymy backup
    manager.create_backup(sources=test_sources)  

    # Sprawdamy co jest w bazie
    print("Ostatnie backupy")
    history = manager.db.get_backup_history(limit=5)
    for name, date, path, size, status, sources in history:
        print(f"{date} | {name} | {status} | {size} B")
        print(f"sources: {sources}")

