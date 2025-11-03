#logger
#Centralne zarządzanie logowaniem
"""
logger.py - moduł odpowiedzialny za logowanie zdarzeń w sytstemie backupowym.
Używany przez wsztskie komponenty (backup_manager, restore_manager, scheduler, itd.)
"""


import logging
import os
from datetime import datetime


class ColorFormatter(logging.Formatter):
    """
    Formatter z kolorami dla poziomów logów.
    Uzywamy kodów ANSI do printowania kolorowych logów.
    """
    COLORS = {
        "DEBUG": "\033[94m",    # Niebieski
        "INFO": "\033[92m",     # Zielony
        "WARNING": "\033[93m",  # Żółty
        "ERROR": "\033[91m",    # Czerwony
        "CRITICAL": "\033[95m", # Fioletowy
    }

    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{log_color}{message}{self.RESET}"


def get_logger(name: str = "BackupSystem"):
    """
    Tworzy i zwraca skonfigurowany obiekt loggera.
    Logger zapisuje logi zarówno do pliku, jak i na konsolę.
    :param name: nazwa loggera (np. "BackupManager" lub "DBManager")
    :return: instancja loggera
    """

    # 1. Utworzenie folderu na logi (jeśli nie istnieje)
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)


    # 2. Nazwa pliku log - z datą, np. "backup-log-2025-10-23.log"
    currnet_date = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"backup_log_{currnet_date}.log")


    # 3. Utworzenie loggera o podanej nazwie
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # zapisujemy wszyskie poziomy (DEBUG, INFO, WARNING, ERROR)


    # 4. Zapobiaganie duplikowaniu logów przy wielokrotnym imporcie
    if logger.handlers:
        return logger


    # 5. Format logów

    # a) Format bez kolorów
    plain_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # b) Format kolorowy
    color_formatter = ColorFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )



    # 6. Handler do pliku (zapis logów do logs/backup_log_YYYY-MM-DD.log)
    # Bez kolorów
    file_handler = logging.FileHandler(log_file, encoding="utf-8")    
    file_handler.setFormatter(plain_formatter)
    file_handler.setLevel(logging.DEBUG)


    # 7. Handelr do konsoli (czytelne komuniakty w terminalu)
    # Kolorowy
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)
    console_handler.setLevel(logging.INFO)


    # 8. Dodanie handlerów do loggera
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


    # 9. Informacja startowa
    logger.info(f"Logger '{name}' został zainicjalizowany - zapisywanie do pliku: {log_file}")

    return logger


# 10. Test modułu (uruchamiaby tylko jeśli plik logger.py jest odplony samodzielnie)
if __name__ == "__main__":
    # Tworzymy testow logger i zapisujemy kilka przykłądowych komunikatów
    test_logger = get_logger("TestLogger")

    test_logger.debug("To jest komunikat DEBUG - szczegóły działania programu.")
    test_logger.info("To jest komunikat INFO - informacja ogólna.")
    test_logger.warning("To jest komuniakt WARNING - ostrzeżenmie.")
    test_logger.error("To jest komuniakt ERROR - błąd krytyczny.")


#DODAĆ IMPLEMENTACJE LOGGERA DO BACKUP_MANAGER!!!