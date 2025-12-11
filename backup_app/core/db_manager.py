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
# EDIT 4  29.11 dodanie logiki związaniem z tworzeniem tabeli do obsłógi urzytkowników

import os
import sqlite3
from datetime import datetime
from .utils.logger import get_logger


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

            # Wywołanie funkcji do tabeli urzytkowników
            self._create_backup_profiles_table()

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

    # Funkcja z tworzeniem tabel urzytkowników
    def _create_backup_profiles_table(self):
        """
        Tworzy tabelę 'backup_profiles' która przechowuje profile urzytkowników
        Jeden profil to zestaw ścieżek, katalogi, opcje schedulera/mailera
        Domyślnie ta tabela zastąpi CONFIG.py
        """
        try: 
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS backup_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    backup_directory TEXT,
                    restore_directory TEXT,
                    backup_frequency TEXT,
                    daily_report_enable INTEGER DEFAULT 0,
                    daily_report_time TEXT,
                    recipient_email TEXT,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL  
                ) 
            """)
            self.conn.commit()
            self.logger.debug("Tabela 'backup_profiles' została utworzona lub już istnieje")
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas tworzenia tabeli 'backup_profiles': {e}")

    # Funkcja do tworzenia profilu
    def create_backup_profile(
            self,
            name: str,
            sources: str,
            backup_directory: str | None = None,
            restore_directory: str | None = None,
            backup_frequency: str | None = None,
            daily_report_enable: bool = False,
            daily_report_time: str | None = None,
            recipient_email: str | None = None,
            is_default: bool = False
    ) -> int | None:
        """
        Tworzymy nowy profil w tabeli 'backup_profiles'
        :param name: nazwa profilu np.: 'Jacek Kowalski'
        :param sources: lista ścieżek
        :return: id nowego profilu lub None gdy błąd        
        """
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_at = created_at

        try:
            if is_default:
                # jeśli ustawiamy ten profil na domyslny inne przestają nim być
                self.cursor.execute("UPDATE backup_profiles SET is_default = 0")
            
            self.cursor.execute("""
                INSERT INTO backup_profiles (
                    name,
                    sources,
                    backup_directory,
                    restore_directory,
                    backup_frequency,
                    daily_report_enable,
                    daily_report_time,
                    recipient_email,
                    is_default,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,(
                name,
                sources,
                backup_directory,
                restore_directory,
                backup_frequency,
                int(daily_report_enable),
                daily_report_time,
                recipient_email,
                int(is_default),
                created_at,
                updated_at
            ))
            self.conn.commit()
            profile_id = self.cursor.lastrowid
            self.logger.info(f"Dodano profil backup '{name}' (id={profile_id})")
            return profile_id
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas dodawania profilu backup: {e}")
            return None
    

    # Pobieranie danego profilu
    def get_backup_profile(self, profile_id: int) -> dict | None:
        """
        Zwraca profil backup o podanym id w formacie słownika
        """
        try:
            self.cursor.execute("""
                SELECT
                    id,
                    name,
                    sources,
                    backup_directory,
                    restore_directory,
                    backup_frequency,
                    daily_report_enable,
                    daily_report_time,
                    recipient_email,
                    is_default,
                    created_at,
                    updated_at
                FROM backup_profiles    
                WHERE id = ?
                LIMIT 1
            """, (profile_id,))
            row = self.cursor.fetchone()
            if not row:
                self.logger.warning(f"Nie znaleziono profilu backup o id={profile_id}")
                return None
            
            return {
                "id": row[0],
                "name": row[1],
                "sources": row[2],
                "backup_directory": row[3],
                "restore_directory": row[4],
                "backup_frequency": row[5],
                "daily_report_enable": bool(row[6]),
                "daily_report_time": row[7],
                "recipient_email": row[8],
                "is_default": bool(row[9]),
                "created_at": row[10],
                "updated_at": row[11]
            }
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas pobierania profilu backupu (id={profile_id}): {e}")
            return None
        
    
    # Pobieranie domyslnego profilu
    def get_default_backup_profile(self) -> dict | None:
        """
        Zwraca profil oznaczony jako domyslny (is_default = 1)
        Jeśli jest kilka - bierze ostatni po id
        """
        try:
            self.cursor.execute("""
                SELECT
                    id,
                    name,
                    sources,
                    backup_directory,
                    restore_directory,
                    backup_frequency,
                    daily_report_enable,
                    daily_report_time,
                    recipient_email,
                    is_default,
                    created_at,
                    updated_at
                FROM backup_profiles
                WHERE is_default = 1
                ORDER BY id DESC
                LIMIT 1
            """)
            row = self.cursor.fetchone()
            if not row:
                self.logger.warning(f"Brak pofilu domyslnego w tabeli 'backup_profiles'")
                return None
            
            return {
                "id": row[0],
                "name": row[1],
                "sources": row[2],
                "backup_directory": row[3],
                "restore_directory": row[4],
                "backup_frequency": row[5],
                "daily_report_enable": bool(row[6]),
                "daily_report_time": row[7],
                "recipient_email": row[8],
                "is_default": bool(row[9]),
                "created_at": row[10],
                "updated_at": row[11]
            }
        except sqlite3.Error as e:
            self.logger.error(f"Bład podczas pobierania profilu domyślnego: {e}")
            return None
        

    # Lista profili
    def list_backup_profiles(self, limit: int = 50) -> list[dict]:
        """
        Zwraca listę profili backupu
        """
        try:
            self.cursor.execute("""
                SELECT
                    id,
                    name,
                    backup_frequency,
                    is_default
                FROM backup_profiles
                ORDER BY id ASC
                LIMIT ?
            """, (limit,))
            rows = self.cursor.fetchall()
            profiles: list[dict]  = []

            for row in rows:
                profiles.append({
                    "id": row[0],
                    "name": row[1],
                    "backup_frequency": row[2],
                    "is_default": bool(row[3])
                })

            self.logger.debug(f"Pobrano {len(profiles)} profili backupu z bazy.")
            return profiles
        
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas pobierania listy profili backupu: {e}")
            return []



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


    # 3. Tworzenie testowego profilu
    profile_id = db.create_backup_profile(
        name="Profil testowy",
        sources=r"C:\Users\Admin\Desktop\STUDIA\Inzynierka\Skrypty\Backend\for zip;"
        r"C:\Users\Admin\Desktop\STUDIA\Inzynierka\Skrypty\Backend\for zip2",   
        backup_directory="backups",
        restore_directory="restored_files",
        backup_frequency="daily",
        daily_report_enable=False,
        daily_report_time="08:00",
        recipient_email="backup.system.receiver@gmail.com",
        is_default=True,  # ten profil będzie domyślny
    )

    # 4. Wyświetlenie profilu
    profile = db.get_backup_profile(profile_id)
    print(profile)

    # 5. profil domyślny
    default_profile = db.get_default_backup_profile()
    print(default_profile)

    # 6. lista profili
    profiles = db.list_backup_profiles(limit=10)
    for p in profiles:
        print(p)

    # 7. Zamykami połączenia
    db.close()
    
# Program tworzy nam lokalną baze otwieramy ją przez vs code