# data base manager
"""
db_manager.py - moduł odpowiedzialny za zarządzanie bazą danych (SQLite).
Tworzy bazę, tabele oraz obsługuje zapis historii backupów.
Każde działanine jest logowane przy pomocy utils/logger.py
"""
# Edit 1 4.011 dodałem w self.conn (punkt 2. inicjalizacja połączenia) check_same_thread=False
# Na wypadek gdyby 2 rzeczy chciały wysłać komunikat co będzie błędem
# Edit 2. 15.11 Dodajemy kolumne sources do bazy danych
# Edit 3. 17.11 dodajemy metode do pobierania nazw danych w backupie (get_backup_name)

import os
import sqlite3
from datetime import datetime
from utils.logger import get_logger


class DatabaseManager:
    """
    Klasa obsługująca połączenie z bazą SQLite oraz wykonywanie operacji CRUD.
    """

    def __init__(self, db_path: str = "backup_data.db", logger=None):        
        """
        Konstruktor klasy Database Manager.
        :param db_path: ścieżka do pliku bazy danych.
        :param logger: instancja loggera (jeśli nie podano, tworzy nowy).
        """

        self.db_path = db_path
        self.logger = logger or get_logger("DatabaseManager")

        # 1. Upewniamy się, że katalog dla bazy istnieje
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

        # 2. Inicjalizacja połączenia
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.logger.info(f"Połączono z bazą danych: {self.db_path}")
            self._create_table()
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas łączenia z bazą danych: {e}")
    
    def _create_table(self):
        """
        Tworzy tabelę 'backups' jesli nie istnieje.
        """

        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER,
                    hash TEXT,
                    status TEXT,
                    sources TEXT
                )
            """)
            self.conn.commit()
            self.logger.debug("Tabela 'backups' została utworzona lub już istnieje.")
            self._ensure_sources_column()
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas tworzenia tabeli: {e}")
        

    def _ensure_sources_column(self):
        """
        Upewnia się, że w tabeli 'backups' istnieje kolumna 'sources'.
        Jeśli baza była utworzona wcześniej, dodaje kolumnę ALTER TABLE.
        """
        try:
            self.cursor.execute("PRAGMA table_info(backups)")
            cols = [row[1] for row in self.cursor.fetchall()]
            if "sources" not in cols:
                self.cursor.execute("ALTER TABLE backups ADD COLUMN sources TEXT")
                self.conn.commit()
                self.logger.info("Dodano kolumnę 'sources' do tabeli 'backups'.")
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas sprawdzania/aktualizacji schematu tabeli 'backups': {e}")

    def add_backup_record(self, name: str, path: str, size: int, hash_value: str = None, status: str = "OK", sources: str | None = None):
        """
        Dodaje nowy wpis o backupie do bazy danych.
        :param name: nazwa pliku backupu
        :param: path: ścieżka do pliku backupu
        :param: size: rozmiar pliku (w bajtach)
        :param: hash_value: suma kontrolna pliku (obcjonalnie)
        :param: status : status (np.: 'OK', 'FAILED')
        :param: sources: lista ścieżek źródłowych jako teskt
        """

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            self.cursor.execute("""
                INSERT INTO backups (name, date, path, size, hash, status, sources)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, date_str, path, size, hash_value, status, sources))
            self.conn.commit()
            self.logger.info(f"Dodano wpis do bazy: {name} ({status})")
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas dodawania wpisu do bazy: {e}")

    
    def get_backup_history(self, limit: int = 10):
        """
        Pobiera listę ostatnich backupów z bazy danych.
        :param limit: ile ostatnich rekordów pobrać (domyślnie 10)
        :return: lista krotek (name, date, path, size, status)
        """

        try:
            self.cursor.execute("""
                SELECT name, date, path, size, status, sources FROM backups
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            results = self.cursor.fetchall()
            self.logger.debug(f"Pobrano {len(results)} rekordów z historii backupów.")
            return results
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas odczytu historii: {e}")
            return []
        
    def get_backup_by_name(self, name: str):
        """
        Zwraca pojedynczy rekord backupu o podanej nazwie
        Jeśli jest kilka rekordów o tej samej nazwie - bierze ostatni (po id)
        :param name: nazwa pliku backupu
        """
        try:
            self.cursor.execute("""
                SELECT name, date, path, size, hash, status, sources
                FROM backups
                WHERE name = ?
                ORDER BY id DESC
                LIMIT 1
            """, (name,))
            row = self.cursor.fetchone()
            if not row:
                return None

            return {
                "name": row[0],
                "date": row[1],
                "path": row[2],
                "size": row[3],
                "hash": row[4],
                "status": row[5],
                "sources": row[6]
            }
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas pobierania backupu '{name}' z bazy: {e}")
            return None

    def close(self):
        """
        Zamyka połączenie z bazą danych.
        """
        try:
            self.conn.close()
            self.logger.info("Połączenie z bazą danych zostało zamknięte.")
        except Exception as e:
            self.logger.error(f"Błąd przy zamykaniu połączenia: {e}")

        
#Test Manualny (samodzielne uruchomienie)

if __name__ == "__main__":
    logger = get_logger("DBTest")
    db = DatabaseManager(logger=logger)

    # 1. Dodanie testowego wpisu
    db.add_backup_record(
        name="Backup_2025_10_23.zip",
        path="backups/Backup_2025_10_23.zip",
        size=2048,
        hash_value="abc123def456",
        status="OK",
        sources="/C/test"
    )


    # 2. Pobranie i wyświetlenie historii
    history = db.get_backup_history(limit=5)
    for record in history:
        print(record)

    # 3. Zamykami połączenia
    db.close()
    
# Program tworzy nam lokalną baze otwieramy ją przez vs code