"""
Skrypt do czyszczenia historii backupów z bazy danych
"""
import sqlite3
import os

# Ścieżka do bazy danych
DB_PATH = os.path.join("backup_app", "backup_data.db")

def clear_backup_history():
    """Usuwa wszystkie rekordy z tabeli backups"""
    try:
        # Połącz z bazą danych
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Usuń wszystkie rekordy z tabeli backups
        cursor.execute("DELETE FROM backups")
        deleted_count = cursor.rowcount
        
        # Zresetuj AUTO_INCREMENT (opcjonalnie)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='backups'")
        
        # Zatwierdź zmiany
        conn.commit()
        
        print(f"✅ Usunięto {deleted_count} rekordów z tabeli backups")
        print("✅ Historia backupów została wyczyszczona")
        
        # Zamknij połączenie
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Błąd podczas czyszczenia bazy danych: {e}")
    except FileNotFoundError:
        print(f"❌ Nie znaleziono bazy danych: {DB_PATH}")

if __name__ == "__main__":
    print("Czyszczenie historii backupów...")
    clear_backup_history()
