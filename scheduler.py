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



    # def load_from_profile(self):
    #     profile = self.db.get_ac


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
        """
        self.logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] Uruchomiono automatyczny backup")
        try:
            self.backup_manager.create_backup()
            self.logger.info("Automatyczny backup zakończony sukcesem")
        except Exception as e:
            self.logger.error(f"Błąd podczas automatycznego backupu {e}")


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
        schedule.every().day.at(time_str).do(self._run_daily_report)
        self.logger.info(f"Ustawiono raport dzienny o {time_str}")

    def _run_daily_report(self):
        self.logger.info("Uruchomiono wysyłanie raportu dziennego")
        if not self.mailer.send_daily_report():
            self.logger.error("Nie udało się wysłać raportu dziennego")

# Test Manualny

if __name__ == "__main__":
    config = {
        "source_directory": "test_data",
        "backup_directory": "backups",
        "backup_frequency": "daily"
    }

    scheduler = BackupScheduler(config=config)
    scheduler.schedule_backup("daily")
    scheduler.start_scheduler()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop_scheduler()
        print("Zatrzymano harmonogram")