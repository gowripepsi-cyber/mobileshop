import shutil
import os
import datetime

DB_FILE = "inventory.db"

def backup_db(destination_dir):
    """
    Copies the sqlite db file to destination_dir with a timestamp.
    """
    if not os.path.exists(DB_FILE):
        return False, "Database file does not exist."
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"inventory_backup_{timestamp}.db"
    destination_path = os.path.join(destination_dir, backup_filename)
    
    try:
        shutil.copy2(DB_FILE, destination_path)
        return True, destination_path
    except Exception as e:
        return False, str(e)

def restore_db(backup_file_path):
    """
    Overwrites the current db file with the backup_file_path.
    """
    if not os.path.exists(backup_file_path):
        return False, "Selected backup file does not exist."
    
    try:
        # Before copy, check if destination exists and make a temp backup just in case
        if os.path.exists(DB_FILE):
            temp_backup = DB_FILE + ".tmp"
            shutil.copy2(DB_FILE, temp_backup)
        
        shutil.copy2(backup_file_path, DB_FILE)
        
        # Clean up temp
        if os.path.exists(DB_FILE + ".tmp"):
            os.remove(DB_FILE + ".tmp")
            
        return True, "Database restored successfully. Please restart the application to reload changes."
    except Exception as e:
        # Rollback temp backup if copy failed
        if os.path.exists(DB_FILE + ".tmp"):
            shutil.copy2(DB_FILE + ".tmp", DB_FILE)
            os.remove(DB_FILE + ".tmp")
        return False, f"Failed to restore: {e}"
