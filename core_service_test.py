# core_service_test

from core_service import (run_backup_from_sources, get_backup_history, restore_full)

if __name__ == "__main__":
    result = run_backup_from_sources(sources=[r"C:\Users\Admin\Desktop\STUDIA\Inzynierka\Skrypty\Backend\for zip"],
                                     destination="backups")
    
    print("Backup result:", result)

    # 2. Historia
    print("History:", get_backup_history(limit=5))

    last_name = result["backup"]["name"]
    restore_result = restore_full(
        backup_name=last_name,
        destination="restored_test"
    )
    print("Restore result:", restore_result)