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

    # E-mail
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "backup.system.sender@gmail.com",
    "sender_password": "nzbe epxr nvir qosb",           # Hasło aplikacji do backup.system.sender@gmail.com
    "recipient_email": "backup.system.receiver@gmail.com"   
}