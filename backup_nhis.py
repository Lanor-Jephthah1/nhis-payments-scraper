import shutil
import time
from datetime import datetime

# Configuration
CSV_SOURCE = "nhis_payments_all.csv"  # Original CSV
BACKUP_DIR = "backups"                # Backup folder

def backup_csv():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{BACKUP_DIR}/nhis_backup_{timestamp}.csv"
    shutil.copy(CSV_SOURCE, backup_name)
    print(f"Backup saved: {backup_name}")

if __name__ == "__main__":
    import os
    os.makedirs(BACKUP_DIR, exist_ok=True)
    while True:
        backup_csv()
        time.sleep(300)  # Backup every 5 minutes (adjust as needed)