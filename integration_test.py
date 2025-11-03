"""
integration_test.py - test integrujący BackupManager i RestoreManager
Sprawdza:
1. Tworzenie backupu
2. Zapis do Bazy
3. Przywracanie backupu
4. Weryfikacje integralności

Aby sprawdzić dzaiąłnie wrzuce do foleru plik txt, folder, zdjęcie, vieo, skrypt pythona
"""

from backup_manager import BackupManager
from restore_manager import RestoreManager
from db_manager import DatabaseManager
from utils.logger import get_logger


def run_integral_test():
    logger = get_logger("IntegrationTest")

    config = {
        "source_directory": "test_data",
        "backup_directory": "backups",
        "restore_directory": "restored_files"
    }

    logger.info("ROZPOCZYNAMY TEST INTEGRACYJNY")

    # 1. Tworzymy instancje
    db = DatabaseManager(logger=logger)
    backup_manager = BackupManager(config=config, logger=logger, db=db)
    restore_manager = RestoreManager(config=config, logger=logger, db=db)

    # 2. Tworzymy nowy backup
    logger.info("[KROK 1] Tworzenie nowego backupu")
    backup_manager.create_backup()

    # 3. Pobieramy ostatni backup z bazy danych
    history = db.get_backup_history(limit=1)
    if not history:
        logger.error("Brak rekordów w bazie - test przerwany.")
        return
    
    last_backup = history[0]
    name, date, path, size, status = last_backup
    logger.info(f"[KROK 2] Ostatny backup w bazie: {name} ({status})")

    # 4. Weryfikacja integralności (hash w bazie)
    db.cursor.execute("SELECT hash FROM backups WHERE name = ?", (name,))
    hash_row = db.cursor.fetchone()
    hash_value = hash_row[0] if hash_row else None

    if not hash_value:
        logger.warning("Brak sumy kontrolnej w bazie - pomijamy weryfikację hash.")
    else:
        logger.info(f"[KROK 3] Hash z bazy: {hash_value}")

    # 5. Przywróć backup
    logger.info("[KROK 4] Przywracanie backupu")
    restore_manager.restore_backup(name, expected_hash=hash_value)

    # 6. Zakończenie testu
    logger.info("TEST INTEGRACYJNY ZAKOŃCZONY")


if __name__ == "__main__":
    run_integral_test()
