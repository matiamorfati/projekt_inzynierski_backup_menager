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
# Edit 5. 16.12 dodanie dodawania opisu do backupu
# Edit 6. 17.12 Dodanie customowej nazwy backupu (do wyśwetlenia w historii): custom_name

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
                    custom_name TEXT,
                    date TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER,
                    hash TEXT,
                    status TEXT,
                    sources TEXT,
                    description TEXT
                )
            """)
            self.conn.commit()
            self.logger.debug("Tabela 'backups' została utworzona lub już istnieje.")
            self._ensure_sources_column()

            # Wywołanie funkcji do tabeli urzytkowników
            self._create_backup_profiles_table()
            self._ensure_backup_profile_columns()

        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas tworzenia tabeli: {e}")
        

    def _ensure_sources_column(self):
        """
        Upewnia się, że w tabeli 'backups' istnieje kolumna 'sources' oraz description.
        Jeśli baza była utworzona wcześniej, dodaje kolumnę ALTER TABLE.
        """
        try:
            self.cursor.execute("PRAGMA table_info(backups)")
            cols = [row[1] for row in self.cursor.fetchall()]
            if "sources" not in cols:
                self.cursor.execute("ALTER TABLE backups ADD COLUMN sources TEXT")
                self.conn.commit()
                self.logger.info("Dodano kolumnę 'sources' do tabeli 'backups'.")

            if "description" not in cols:
                self.cursor.execute("ALTER TABLE backups ADD COLUMN description TEXT")
                self.conn.commit()
                self.logger.info("Dodano kolumnę 'description' do tabeli 'backups'.")  

            if "custom_name" not in cols:
                self.cursor.execute("ALTER TABLE backups ADD COLUMN custom_name TEXT")
                self.conn.commit()
                self.logger.info("Dodano kolumnę 'custom_name' do tabeli 'backups'.")  
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
                    custom_name TEXT,
                    description  TEXT,
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

    def _ensure_backup_profile_columns(self):
        """
        Upewnia się że w tabeli są custom_name i description
        """
        try:
            self.cursor.execute("PRAGMA table_info(backup_profiles)")
            cols = [row[1] for row in self.cursor.fetchall()]
            if "custom_name" not in cols:
                self.cursor.execute("ALTER TABLE backup_profiles ADD COLUMN custom_name TEXT")
                self.conn.commit()
                self.logger.info("Dodano kolumne 'custom_name' do 'backup_profiles'")
            if "description" not in cols:
                self.cursor.execute("ALTER TABLE backup_profiles ADD COLUMN description TEXT")
                self.conn.commit()
                self.logger.info("Dodano kolumne 'description' do 'backup_profiles'")
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas aktualizowania schematu 'backup_profiles': {e}")

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
            is_default: bool = False,
            custom_name: str | None = None,
            description: str | None = None
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
                    custom_name,
                    description,
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,(
                name,
                custom_name,
                description,
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
                    custom_name,
                    description,
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
                "custom_name": row[2],
                "description": row[3],
                "sources": row[4],
                "backup_directory": row[5],
                "restore_directory": row[6],
                "backup_frequency": row[7],
                "daily_report_enable": bool(row[8]),
                "daily_report_time": row[9],
                "recipient_email": row[10],
                "is_default": bool(row[11]),
                "created_at": row[12],
                "updated_at": row[13]
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
                    custom_name,
                    description,
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
                "custom_name": row[2],
                "description": row[3],
                "sources": row[4],
                "backup_directory": row[5],
                "restore_directory": row[6],
                "backup_frequency": row[7],
                "daily_report_enable": bool(row[8]),
                "daily_report_time": row[9],
                "recipient_email": row[10],
                "is_default": bool(row[11]),
                "created_at": row[12],
                "updated_at": row[13]
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
                    custom_name,
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
                    "custom_name": row[2],
                    "backup_frequency": row[3],
                    "is_default": bool(row[4])
                })

            self.logger.debug(f"Pobrano {len(profiles)} profili backupu z bazy.")
            return profiles
        
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas pobierania listy profili backupu: {e}")
            return []



    def add_backup_record(self, 
                          name: str, 
                          path: str, 
                          size: int, 
                          hash_value: str = None, 
                          status: str = "OK", 
                          sources: str | None = None,
                          description: str | None = None,
                          custom_name: str | None = None):
        """
        Dodaje nowy wpis o backupie do bazy danych.
        :param name: nazwa pliku backupu
        :param path: ścieżka do pliku backupu
        :param size: rozmiar pliku (w bajtach)
        :param hash_value: suma kontrolna pliku (obcjonalnie)
        :param status : status (np.: 'OK', 'FAILED')
        :param sources: lista ścieżek źródłowych jako teskt
        :param description: opis dodany do backupu
        :param custom_name: dodatkowa customowa nazwa backupu
        """

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            self.cursor.execute("""
                INSERT INTO backups (name, custom_name, date, path, size, hash, status, sources, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, custom_name, date_str, path, size, hash_value, status, sources, description))
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
                SELECT name, custom_name, date, path, size, status, sources, description FROM backups
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            results = self.cursor.fetchall()
            self.logger.debug(f"Pobrano {len(results)} rekordów z historii backupów.")
            return results
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas odczytu historii: {e}")
            return []

    def get_backup_stats(self):
        """
        Zwraca podstawowe statystyki dotyczące backupów:
        - total: liczba rekordów
        - storage_used: suma rozmiarów (w bajtach)
        - success_count: liczba rekordów ze statusem 'OK'
        """
        try:
            self.cursor.execute("SELECT COUNT(1), COALESCE(SUM(size),0) FROM backups")
            total_row = self.cursor.fetchone() or (0, 0)
            total = total_row[0] or 0
            storage_used = total_row[1] or 0

            self.cursor.execute("SELECT COUNT(1) FROM backups WHERE status = ?", ("OK",))
            success_row = self.cursor.fetchone() or (0,)
            success_count = success_row[0] or 0

            return {
                "total": total,
                "storage_used": storage_used,
                "success_count": success_count,
            }
        except sqlite3.Error as e:
            self.logger.error(f"Błąd podczas pobierania statystyk backupów: {e}")
            return {"total": 0, "storage_used": 0, "success_count": 0}
        
    def get_backup_by_name(self, name: str):
        """
        Zwraca pojedynczy rekord backupu o podanej nazwie
        Jeśli jest kilka rekordów o tej samej nazwie - bierze ostatni (po id)
        :param name: nazwa pliku backupu
        """
        try:
            self.cursor.execute("""
                SELECT name, custom_name, date, path, size, hash, status, sources, description
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
                "custom_name": row[1],
                "date": row[2],
                "path": row[3],
                "size": row[4],
                "hash": row[5],
                "status": row[6],
                "sources": row[7],
                "description": row[8]
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
        custom_name="Test_Backup",
        path="backups/Backup_2025_10_23.zip",
        size=2048,
        hash_value="abc123def456",
        status="OK",
        sources="/C/test",
        description="Testowy backup"
    )


    # 2. Pobranie i wyświetlenie historii
    history = db.get_backup_history(limit=5)
    for record in history:
        print(record)


    # 3. Tworzenie testowego profilu
    profile_id = db.create_backup_profile(
        name="Profil testowy",
        custom_name="Testowa nazwa profilu",
        description="Opis profilu",
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