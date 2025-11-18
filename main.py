# main
"""
main.py -punkt startowy kodu tu odpalamy wszyskie funckje
Autor: Kacper Kaszuba
Rola: Backend / zarządzanie logiką
"""

# Importy

#z utils:
from utils.config import CONFIG
from utils.logger import get_logger

#funkcje
from backup_manager import BackupManager
from restore_manager import RestoreManager
from scheduler import BackupScheduler
from mail_notifier import MailNotifier 

def init_core():
    """
    Inicjalizuje główne komponenty systemu
    Używamy wspólnego CONFIG + loggera 'Main'
    Każdy manager tworzy własny dostęp do bazy
    """
    config = CONFIG.copy()
    logger = get_logger("Main")

    backup_manager = BackupManager(config=config, logger=logger)
    restore_manager = RestoreManager(config=config, logger=logger)
    scheduler = BackupScheduler(config=config, logger=logger)
    mailer = MailNotifier(config=config, logger=logger)

    return config, logger, backup_manager, restore_manager, scheduler, mailer

# Dodałem do nazw _main aby sie nie myłiło z tymi z innych plików

# 1. Tworzenie Backupu
def manual_backup_main(backup_manager: BackupManager):
    """
    Ręczne tworzenie backupu
    User może:
    - użyć ścieżek z CONFIG (source_directory)
    - podać własne ścieżki (pojedyncze lub kilka rozdzielone ';')
    """

    print("\n[1] Ręczne tworzenie backupu")
    # Potem zmiana na wykaz z bazy (podane na pooczątku)
    print("1) Użyj domyślnej konfiguracji (CONFIG['source_directory])")
    print("2) Podaj ścieżkę / ścieżki ręcznie")
    choice = input("Wybór (ENTER = 1): ").strip() or "1"

    if choice == "1":
        # BackupManager sam pobiera source_directory z CONFIG
        backup_manager.create_backup()
    elif choice == "2":
        raw = input("Podaj ścieżki do backupu (oddielone ';'): ").strip()
        sources = [p.strip() for p in raw.split(";") if p.strip()]
        if not sources:
            print("Nie podano żadnych ścieżek - przerwano.")
            return
        backup_manager.create_backup(sources=sources)
    else:
        print("Nieprawidłowy wybór - przerwano")

# 2. Pokazanie histori backupów
def show_backup_history_main(backup_manager: BackupManager):
    """
    Wypisuje ostatnie backupy z bazy danych w formacie tabelki
    Wykorzystuje db_manager.get_backup_history()
    """
    print("\n[2] Historia backupów (ostatnie wpisy)\n")

    history = backup_manager.db.get_backup_history(limit=10)

    if not history:
        print("Brak zapisanych backupów w bazie")
        return
    
    print(f"{'DATA':19} | {'NAZWA':35} | {'STATUS':8} | {'ROZMIAR [B]':11}")
    
    for name, date, path, size, status, sources in history:
        print(f"{date:19} | {name[:35]:35} | {status:8} | {size:11}")
        if sources:
            print(f"    źródła: {sources}")
    print()


# 3. PRzywracanie Backupu

def restore_interactive_main(restore_manager: RestoreManager):
    """
    Uruchamia tryn interaktywny restore:
    - wybór backupu z listy plików .zip
    - wybór pełnego lub częściowego przywracania (root katalogu)
    """
    print("\n[3] Przywracanie backupu (pełne / częściowe)")
    restore_manager.restore_interactive()


# 4. Scheduler
def run_scheduler_main(scheduler: BackupScheduler):
    """
    Uruchamia harmonogram backupów
    Uwaga!: funkcja blokuje wątek (while True z schedule.run_pending())
    Zatrzymanie Ctrl + C
    """
    print("\n[4] Uruchomienie harmonograu backupów")
    print("Wybierz częstotliwość:")
    print("1) Codziennie")
    print("2) Co tydzeń")
    print("3) Co miesiąc")
    choice = input("Wybór (Enter = 1): ").strip() or "1"

    freq = {
        "1": "daily",
        "2": "weekly",
        "3": "monthly"
    }
    frequency = freq.get(choice, "daily")

    scheduler.schedule_backup(frequency)
    scheduler.schedule_daily_report()
    scheduler.start_scheduler()
    
    print("Harmonogram został uruchomiony w tle")


# 5. Wysyłanie codziennych powiadomień
def send_daily_report_main(mailer: MailNotifier):
    """
    Wysyła raport dzienny e-mail
    """
    print("\n[5] Wysyłanie raportu dziennego e-mailem")
    if not hasattr(mailer, "send_daily_report"):
        print("MailNotifier nie ma metody send_daily_report() - zaimplementuj ją")
        return
    
    ok = mailer.send_daily_report()
    if ok:
        print("Raport dzienny został wysłany")
    else:
        print("Nie udało sięwysłać raportu dziennego - sprawdź logi!")


# 6. Menu
# Narazie w cmd

def print_menu():
    print("SYSTEM BACKUPÓW - MENU")
    print("1) Ręczne wykonanie backupu")
    print("2) Historia backupów (z bazy danych)")
    print("3) Przywracanie backupu (pełne / częściowe)")
    print("4) Uruchom harmonogram backupów (scheduler)")
    print("5) Wyślij raport dzienny e-mailem")
    print("0) Wyjście")

# 7. Main
def main():
    config,logger,backup_manager, restore_manager, scheduler, mailer = init_core()
    logger.info("Uruchomiono główne menu systemu backupów")

    while True:
        print_menu()
        choice = input("Wybierz opcję: ").strip()

        match choice:
            case "1":
                manual_backup_main(backup_manager)
            case "2":
                show_backup_history_main(backup_manager)
            case "3":
                restore_interactive_main(restore_manager)
            case "4":
                run_scheduler_main(scheduler)
            case "5":
                send_daily_report_main(mailer)
            case "0":
                print("Zamykanie programu")
                logger.info("Zamykanie programu z menu głównego")
                break
            case _:
                print("Nieprawidłowy wybór - spróbuj ponownie")


if __name__ == "__main__":
    main()
        
"""
Przeprowadzić test manualny czy dorbze działa 
Posuzkac błędów

Pomysł na roziwnięcie:
- Krok 6 wyswetlenie histori restore
"""
    