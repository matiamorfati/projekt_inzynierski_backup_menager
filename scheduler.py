# scheduler.py
"""
scheduler.py - moduł zarządzający harmonogramem automatycznych backupów.
Wersja 1.0 (Pythonowa)

W terj wersji:
- harmonogram uruchamiany lokalnie w tle (biblioteka schedule)
- częstotliwość backupów (daily, weekly, monthly)
- logowanie każdego uruchomienia
- integracja z BackupMnager, DatabaseManager i Logger

W przyszłości (Wersja 2.0):
- możliwość rejestrowania harmonogramu w systemie (cron / Task Scheduler)
- konfiguracja częstotliwości z gui lub bazy danych
"""

# EDIT 1. 25.10 Zaczęcie pisania programu przemiyslenie logiki (wydzielenie na 2 wersje)
# EDIT 2. 04.11 Kontynacja pisania programu przeporwadzenie testu działania
# EDIT 3. 13.11 Wprowadzenie wysyłania dayly maili
# Edit 4. 04.12 Wprowadzenie do 2.0


import time
import threading
import schedule
from datetime import datetime

from backup_manager import BackupManager
from db_manager import DatabaseManager
from utils.logger import get_logger
from utils.config import CONFIG
from mail_notifier import MailNotifier

class BackupScheduler:
    """
    Klasa odpowiedzialna za zarządzanie harmonogramem tworzenia backupów.
    """

    def __init__(self, config: dict = None, logger=None, db=None, backup_manager=None, mailer=None):
        """
        :param config: konfiguracja (źródło, folder backupów, interwał)
        :param logger: instancja loggera
        :param db: instancja bazy danych (DatabaseManager)
        :param backup_manager: instancja BackupManager
        :param mailer: instancja mail_notifier do wysyłania codziennych maili
        """

        self.config = config or CONFIG
        self.logger = logger or get_logger("BackupScheduler")
        self.db = db or DatabaseManager(logger=self.logger)
        self.backup_manager = backup_manager or BackupManager(config=self.config, logger=self.logger, db=self.db)
        self.mailer = mailer or MailNotifier(config=self.config, logger=self.logger, db=self.db)

        self.running = False
        self.thread = None
        self.frequency = self.config.get("backup_frequency", "daily") # Domyślnie codziennie

        # Mozna potem zmienić domyślne na weekly lub monthly !!

        self.logger.info(f"BackupScheduler zainicjalizowany (tryb: {self.frequency})")



    def load_from_profile(self, profile_id: int | None = None):
        """
        Ładuje ustawienia schedulera z profilu backupu w bazie.
        
        Jeżeli profil_id jest None: używa profilu domyslnego dzięki get_default_backup_profile()
        W przeciwnym razie: pobiera konkretny profgil przez get_backup_profile()
        """
        # 1. Pobranie profilu z bazy
        try:
            if profile_id is None:
                profile = self.db.get_default_backup_profile()
            else:
                profile = self.db.get_backup_profile(profile_id)
        except AttributeError:
            self.logger.error("Database manager niema metody get_default_backup_profile/get_backup_profile Sprawć wersje db_manager.")
            return
        
        if not profile:
            self.logger.warning("Brak profilu backup w bazie - Używamy ustawień z CONFIG")
            return
        
        # 2. Połączenie profilu z aktualnym configiem
        new_cfg = self.config.copy()

        # Ścieżki
        if profile.get("backup_directory"):
            new_cfg["backup_directory"] = profile["backup_directory"]
        if profile.get("restore_directory"):
            new_cfg["restore_directory"] = profile["restore_directory"]

        # Źródła
        if profile.get("sources"):
            new_cfg["default_sources"] = profile["sources"]

        # Częstotliwość backupu
        if profile.get("backup_frequency"):
            new_cfg["backup_frequency"] = profile["backup_frequency"]

        # Raport dzienny
        new_cfg["daily_report_enable"] = profile.get("daily_report_enable", False)
        if profile.get("daily_report_time"):
            new_cfg["daily_report_time"] = profile["daily_report_time"]


        # E-mail odbiorcy
        if profile.get("recipient_email"):
            new_cfg["recipient_email"] = profile["recipient_email"]


        # 3. Pobieranie config w schedulerze i zależnych obiektach
        self.config = new_cfg
        self.frequency = new_cfg.get("backup_frequency", self.frequency)
        
        self.backup_manager.config = self.config
        self.mailer.config = self.config

        self.logger.info(
            f"BackupScheduler: wczytano profil '{profile.get('name')}"
            f"(freq={self.frequency}, "
            f"daily_report={new_cfg.get('daily_report_enable')}, "
            f"time={new_cfg.get('daily_report_time', '8:00')})"
        )

    


    # 1. Planowanie zadań

    def schedule_backup(self, frequency: str = "daily"):
        """
        Ustawia częstotliwość backupów.
        Dostępne opcje: 'daily', 'weekly', 'monthly'
        """
        self.frequency = frequency
        schedule.clear() # usuwam poprzednie zadania

        # Dać tu case zamiast if
        # W wersji 2.0 czas (godzina) będzie pobierany z bazy lub config/ ustawiany na froncie
        if frequency == "daily":
            schedule.every(1).minutes.do(self._run_backup)
            # To skomentować dla testu szybkiego
            schedule.every().day.at("8:00").do(self._run_backup)
            self.logger.info("Ustawiono harmonogram: codnienny backup o 8:00")
        elif frequency == "weekly":
            schedule.every().monday.at("8:00").do(self._run_backup)
            self.logger.info("Ustawiono harmonogram: cotygodniowy backup (poniedziałek 8:00)")
        elif frequency == "monthly":
            schedule.every(30).days.at("8:00").do(self._run_backup)
            self.logger.info("Ustawiono harmonogram: comiesięczny backup (co 30 dni o 8:00)")
        else:
            self.logger.warning(f"Nieznana częstotliwość: {frequency}, ustawiono domyśnie 'daily'")
            schedule.every().day.at("8:00").do(self._run_backup)

    
    
    # 2. Stworzenie/Zlecenie backupu

    def _run_backup(self):
        """
        Funkcja wywoływania przez harmonogram
        Tworzy backup i zapisuje wynik w logach oraz bazie danych
        Źródła bierzemy z proiilu backup (DB) albo z CONFIG
        Jeżeli nic nie widzi nic nie robi iwyrzuca błąd
        """
        now_str = datetime.now().strftime("%H:%M:%S")
        self.logger.info(f"[{now_str}] Uruchomiono automatyczny backup")
        
        sources: list[str] =[]

        # 1. Próba brania ścieżki z profilu DB
        profile = None
        try:
            profile = self.db.get_default_backup_profile()
        except Exception as e:
            self.logger.error(f"Nie udało się pobrać profilu backupu z DB: {e}")

        if profile and profile.get("sources"):
            raw_sources = profile["sources"]
            if isinstance(raw_sources, (list, tuple)):
                items = raw_sources
            else:
                items = str(raw_sources).split(";")
                
            sources = [
                p.strip()
                for p in items
                if p.strip()
            ]

        # 2. Fallback do CONFIG jeśli w profilu nie było nic pomocnego
        if not sources:
            cfg_src = (self.config.get("source_directory"))
            
            
            if isinstance(cfg_src, (list, tuple)):
                items = cfg_src
            elif cfg_src:
                items = str(cfg_src).split(";")            
            else:
                items = []
                    
            sources = [
                str(p).strip()
                for p in items
                if str(p).strip()
            ]
        
        # 3. Jeśli dalej brak źródeł - Tworzenie backupu przerwane
        if not sources:
            self.logger.error("Brak zdefiniowanych ścieżek do backupu (profil DB / CONFIG). - zadanie pominięte")
            return
        
        # 4. Uruchomienie backupu 
        try:
            self.backup_manager.create_backup(sources=sources)
            self.logger.info("Automatyczny backup zakończony sukcesem")
        except Exception as e:
            self.logger.error(f"Błąd podczas automatycznego backupu: {e}")

    # 3. Uruchamianie  harmonogramu

    def start_scheduler(self):
        """
        Uruchamia harmonogram w osobnym wątku
        """
        if self.running:
            self.logger.warning("Harmonogram juz działa")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.logger.info("Harmonogram backupów został uruchomiony w tle")
        

    # 4. Zatrzymywanie harmonogramu

    def stop_scheduler(self):
        """
        Zatrzymuje harmonogram
        """
        if not self.running:
            self.logger.warning("Harmonogram nie jest aktywny")
            return
        
        self.running = False
        self.logger.info("Harmonogram backupów został zatrzymany")

    def _run_loop(self):
        """
        Wewnętrzna pętla dzaiłająca w tle: sprawdza zaplanowane zadania
        """
        self.logger.debug("Scheduler loop startuje")
        while self.running:
            schedule.run_pending()
            time.sleep(1)
        self.logger.debug("Scheduler loop zakończony")

    # 5. Dayly mailer

    def schedule_daily_report(self):
        if not self.config.get("daily_report_enable", False):
            self.logger.info("Raport dzienny wyłączony w konfiguracji")
            return
        time_str = self.config.get("daily_report_time", "8:00")
        schedule.every(2).minutes.at(time_str).do(self._run_daily_report)
        # To skomentować dla testu szybkiego
        schedule.every().day.at(time_str).do(self._run_daily_report)
        self.logger.info(f"Ustawiono raport dzienny o {time_str}")

    def _run_daily_report(self):
        self.logger.info("Uruchomiono wysyłanie raportu dziennego")
        if not self.mailer.send_daily_report():
            self.logger.error("Nie udało się wysłać raportu dziennego")


    def schedule_from_profile(self,profile_id: int | None = None):
        """
        Funkcja pomocnicza
        - Ładuje profil z bazy
        - ustawia harmonogram backupu
        - ustawia harmonogram raportu dziennego (jeśli włączony)
        """
        self.load_from_profile(profile_id=profile_id)
        self.schedule_backup(self.frequency)
        self.schedule_daily_report()

# # Test Manualny 1.
# if __name__ == "__main__":
#     config = {
#         "source_directory": "test_data",
#         "backup_directory": "backups",
#         "backup_frequency": "daily"
#     }

#     scheduler = BackupScheduler(config=config)
#     scheduler.schedule_backup("daily")
#     scheduler.start_scheduler()

#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         scheduler.stop_scheduler()
#         print("Zatrzymano harmonogram")


# Test Manualny 2.
# Test Manualny

if __name__ == "__main__":
    # 1. Bierzemy config z utils.config
    config = CONFIG.copy()
    logger = get_logger("SchedulerTest")

    # 2. Tworzymy scheduler (on sam tworzy DatabaseManager, BackupManager i MailNotifier)
    scheduler = BackupScheduler(config=config, logger=logger)

    # 3. Ładujemy ustawienia z profilu z bazy
    #    - jeśli masz ustawiony profil domyślny → wywołaj bez argumentu
    #    - jeśli chcesz konkretny profil → podaj ID
    scheduler.schedule_from_profile(profile_id=1)   # albo: scheduler.schedule_from_profile()

    # 4. Odpalamy scheduler w tle
    scheduler.start_scheduler()
    print("Scheduler działa, czekam na pierwsze zaplanowane zadanie... (Ctrl+C żeby przerwać)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop_scheduler()
        print("Zatrzymano harmonogram")
