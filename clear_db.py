import sqlite3

conn = sqlite3.connect('backup_app/backup_data.db')
cursor = conn.cursor()

# Sprawdź tabele
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', tables)

# Usuń rekordy
try:
    cursor.execute('DELETE FROM backups')
    deleted_backups = cursor.rowcount
    print(f'Deleted {deleted_backups} backup records')
except Exception as e:
    print(f'Error deleting from backups: {e}')

try:
    cursor.execute('DELETE FROM restores')
    deleted_restores = cursor.rowcount
    print(f'Deleted {deleted_restores} restore records')
except Exception as e:
    print(f'Error deleting from restores: {e}')

conn.commit()
conn.close()
print('Done!')
