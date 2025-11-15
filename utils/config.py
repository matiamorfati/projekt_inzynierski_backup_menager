#config
#trzymanie ścierzekm ustawień, e-mailim harmonogramów w jednym miejscu
#Bedziemy je inportować z tego pliku zamiast hardcodować

# Gdy przejdziemy do wersji "sieciowej" (nie lokalnej) to pozmieniamy cos

CONFIG = {
    # Ścieżki
    "source_directory": "test_data",
    "backup_directory": "backups",
    "restore_directory": "restored_files",
    "backup_frequency": "daily",

    # Baza danych
    # tu będzie ściezka do bazy (narazie jest lokalnie)

    # E-mail
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "backup.system.sender@gmail.com",
    "sender_password": "nzbe epxr nvir qosb",           # Hasło aplikacji do backup.system.sender@gmail.com
    "recipient_email": "backup.system.receiver@gmail.com",

    # Raporty e-mail
    "daily_report_enable": True,
    "daily_report_time": "8:00",

    #Ilosc max backupów
    #"max_backup": 10, # to się włączy po testach zeby nie suuneło backupów do pokazania 


    # Partycje 
    # w przyszłości
}