# mail_notifier

# EDIT 1.  08.11  Wersja 1.0
# EDIT 2.  13.11  Wprowadzenie do wersji 2.0 (lepszy dayly sender oraz dodawanie załączników)
# EDIT 3.  17.11  Wprowadzenie notyfikacji po przywróceniu
"""
mail_notifier.py - Wysyła powaidomienia e-mail 
Wersja 1.0: Wysyła wiadomość o stanie backupu

Plan na wersje 2.0: 
- Raporty cykliczne (integracja z scheduler)
- załączniki (logi, manifesty)
- podawanie emaila odbiorcy z 
- Wysyłanie powiadomień o błędzie
"""

import smtplib
import os
from email.message import EmailMessage
from datetime import datetime

from utils.logger import get_logger
from db_manager import DatabaseManager
from utils.config import CONFIG

class MailNotifier:
    """
    Klasa odpowiedzialna za wysyłanie powiadomień e-mail
    """

    def __init__(self, config: dict = None, logger=None, db=None):
        """
        Inicjacja klasy MailNotifier
        :param config: słownik z konfiguracją SMTP i odbiorcami
        :param logger: instancja loggera
        :param db: instacja bazy danych
        """
        self.config = config or CONFIG
        self.logger = logger or get_logger("MailNotifier")
        self.db = db or DatabaseManager(logger=self.logger)

        self.smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.sender_email = self.config.get("sender_email", "").strip()         # Ustawnione na maila gmail         
        self.sender_password = self.config.get("sender_password", "")                               # Ustawnione na maila gmail 
        self.recipient_email = self.config.get("recipient_email", "backup.system.receiver@gmail.com").strip()    # Ustawnione na maila gmail 
        
        self.logger.info("MailNotifier zainicjalizowany")

    # 1. Wysyłanie maila
    def send_email(self, subject: str, body: str, attachments: list[str] = None):
        """
        Wysyła waidomość e-mail z podanym tematem i treścią
        """
        try:
            msg = EmailMessage()
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg["Subject"] = subject
            msg.set_content(body)

            # dodanie załącznika
            if attachments:
                for path in attachments:
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                        msg.add_attachment(
                            data,
                            maintype="application",
                            subtype="octet-stream",
                            filename=os.path.basename(path)
                        )
                    except Exception as e:
                        self.logger.error(f"Nie udało się dodać załącznika {path}: {e}")

            # Wysyłanie maila
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            self.logger.info(f"E-mail wysłano do: {self.recipient_email} ({subject})")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas wysyłania e-maila: {e}")
            return False
        
        

    # 2. Wysyłanie powiadomienia o backupie
    def notify_backup_result(self, backup_name: str, status: str, details: str= "", attachments: list[str] | None = None):
        """
        Wysyła powiadominie e-mail po zakończonym backupie
        :param backup_name: Nazwa pliku backup
        :param status: 'Ok' lub 'FAILED'
        :param details: dodatkowe info (hash, rozmiar)
        """

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"[Backup System] Status: {status} ({backup_name})"
        body = (
            f"Data: {date_str}\n"
            f"Nazwa backup: {backup_name}\n"
            f"Status: {status}\n"
            f"Szczegóły:\n{details}\n"
        )

        return self.send_email(subject, body, attachments=attachments)
    
    # 3. Wysyłanie raportu dziennego
    # Można dać to jako obcjonalne ON/OFF
    def send_daily_report(self):
        """
        Wysyła dzienny raporty o wykonanych backupach
        """

        try:
            self.db.cursor.execute("""
                SELECT name, date, status FROM backups
                WHERE date >= datetime('now', '-1 day')
            """)
            records = self.db.cursor.fetchall()

            if not records:
                body = "Brak backupów wykonanych w ostatnich 24 godzinach"
            else:
                body = "Backupy wykonane w ostatnich 24H:\n"
                for name, date, status in records:
                    body += f"- {name} | {date} | {status}\n"

            return self.send_email("[Backup System] Raport dzienny", body)
        
        except Exception as e:
            self.logger.error(f"Błąd podczas generowania raportu dziennego: {e}")
            return False
        
    # 4. Powiadomoenie po przywróceniu
    def notify_restore_result(self, backup_name: str, status: str, destination: str, details: str = "", attachments: list[str] | None=None):
        """
        Wysyła powiadomienia e-mail po zakończonym przywracaniu
        :param backup_name: nazwa pliku backupu
        :param status: 'OK', 'FAILED', 'OK_PARTIAL', itd.
        :param destination: ścieżka katalogu, do którego przywrócilśmy dane
        :param details: dodatkowe informacje (jakie foldery, ile plików)
        :param attachments: lista ścieżek do załączników
        """
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subject = f"[Backup SYstem] Restore: {status} ({backup_name})"
        body = (
            f"Data: {date_str}\n"
            f"Nazwa backupu: {backup_name}\n"
            f"Status przywracania: {status}\n"
            f"Folder docelowy: {destination}\n"
            f"Szczegóły: \n{details}\n"
        )

        return self.send_email(subject, body, attachments=attachments)


# Test Manualny
if __name__ == "__main__":
    notifier = MailNotifier(config=CONFIG) # Kożystamy z config.py
    notifier.notify_backup_result("Backup_test2.zip", "OK", "Rozmiar: 5 MB, Hash: abcd123ef")
