"""
Test integracyjny nr.2. 
11.11.2025
test będzie:
- uruchomi harmonogram
- tworzy backup
- wczyta dane
- zapisze dane do bazy
- wysle e-mail 

"""

from utils.logger import get_logger
from utils.config import CONFIG
from backup_manager import BackupManager
from restore_manager import RestoreManager
from db_manager import DatabaseManager
from scheduler import BackupScheduler
from mail_notifier import MailNotifier

def run_integration_test_v2():
    logger = get_logger("IntegrationTestv2")

    logger.info("Test Integracyjny v2")

    # 1. Inicjalizacja zmiennych
    db = DatabaseManager(logger=logger)
    mailer = MailNotifier(config=CONFIG, logger=logger, db=db)
    backup_manager = BackupManager(config=CONFIG, logger=logger, db=db, mailer=mailer)
    restore_manager = RestoreManager(config=CONFIG, logger=logger, db=db)
    scheduler = BackupScheduler(config=CONFIG, logger=logger, db=db, backup_manager=backup_manager)

    # 2. Uruchamiamy harmonogram (ręcznie narazie)
    scheduler._run_backup()

    # 3. Sprawdzanie czy powstał nowy plik backup
    backups = restore_manager.list_backups()
    if not backups:
        logger.error("Nie znaleziono żadnych backupów po uruchomieniu harmonogramu")
        return
    last_backup = sorted(backups)[-1]
    logger.info(f"Ostatni znaleziony bakcup: {last_backup}")

    # 4. Przywracanie danych z ostatniego backupu
    result = restore_manager.restore_backup(last_backup)
    if result:
        logger.info("Prywracanie zakończone pomyslnie")
    else:
        logger.error("Przywracanie zakończyło się błędem")

    # 5. Sprawdzanie czy wpis backup istnieje w bazie
    history = db.get_backup_history(limit=5)
    if history:
        logger.info("Ostatnie wpisy w bazie: ")
        for record in history:
            logger.info(str(record))
    else:
        logger.warning("Brak wpisów w bazie" )
    
    
    #6. Zakkończenie testu
    logger.info("Test v2 zakończony")
    db.close()


if __name__ == "__main__":
    run_integration_test_v2()

