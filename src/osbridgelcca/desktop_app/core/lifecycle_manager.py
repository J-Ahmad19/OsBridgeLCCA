import os
import json
import shutil
import sqlite3
import hashlib
import datetime
from .database import DatabaseManager

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECTS_ROOT = os.path.join(BASE_DIR, "projects")
DB_PATH = os.path.join(PROJECTS_ROOT, "project_manager.db")
BACKUP_DIR = os.path.join(PROJECTS_ROOT, "backups")

class LifecycleManager:
    def __init__(self):
        self.db = DatabaseManager(DB_PATH)
        self.active_project_id = None

    # =========================================================
    # 5. APP STARTUP & 7. CRASH RECOVERY (PDF Source 125, 202)
    # =========================================================
    def app_start(self):
        """
        Run this when the application launches.
        1. Checks DB existence.
        2. Detects crashed projects (Status='draft' + Temp File Exists).
        """
        if not os.path.exists(DB_PATH):
            return {"status": "first_run"}
        
        crashed_projects = self.get_crashed_projects_from_drafts()
        if crashed_projects:
            return {"status": "crash_detected", "projects": crashed_projects}
        
        return {"status": "normal"}

    def get_crashed_projects_from_drafts(self):
        """
        PDF Source 206: Identify Crashed Projects.
        Returns list of projects that are stuck in 'draft' mode with a temp file.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Fetch all projects marked as 'draft'
        cursor.execute("SELECT id, name, last_opened FROM projects WHERE status = 'draft'")
        drafts = cursor.fetchall()
        conn.close()

        crashed = []
        for pid, name, last_opened in drafts:
            temp_path = os.path.join(PROJECTS_ROOT, pid, "temp", "autosave.json")
            # PDF Source 208: Verify temp file exists
            if os.path.exists(temp_path):
                crashed.append({"id": pid, "name": name, "last_opened": last_opened})
        return crashed

    def recover_project(self, project_id):
        """
        PDF Source 213: Recover - Load the temp file.
        """
        # Logic: We simply open the project. The open_project logic handles 
        # reading from temp if it exists.
        return self.open_project(project_id)

    def discard_recovery(self, project_id):
        """
        PDF Source 214-216: Discard - Delete temp, revert to main.
        """
        project_folder = os.path.join(PROJECTS_ROOT, project_id)
        temp_path = os.path.join(project_folder, "temp", "autosave.json")
        main_path = os.path.join(project_folder, "main_file.json")

        # 1. Delete temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # 2. Revert DB status to 'saved' (if main exists) or delete record (if new project)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if os.path.exists(main_path):
            cursor.execute("UPDATE projects SET status='saved' WHERE id=?", (project_id,))
        else:
            # It was a new project that never got saved manually
            cursor.execute("DELETE FROM projects WHERE id=?", (project_id,))
            shutil.rmtree(project_folder, ignore_errors=True)
            
        conn.commit()
        conn.close()

    # =========================================================
    # 6.2 OPEN PROJECT (PDF Source 149)
    # =========================================================
    def open_project(self, project_id):
        """
        Opens a project for editing. 
        Crucial: Ensures we are working on a TEMP copy (autosave.json).
        """
        self.active_project_id = project_id
        project_folder = os.path.join(PROJECTS_ROOT, project_id)
        temp_path = os.path.join(project_folder, "temp", "autosave.json")
        main_path = os.path.join(project_folder, "main_file.json")

        # PDF Source 153: If temp missing, copy main -> temp
        if not os.path.exists(temp_path):
            if os.path.exists(main_path):
                shutil.copy2(main_path, temp_path)
            else:
                raise FileNotFoundError(f"No files found for project {project_id}")

        # PDF Source 163: Update last_opened and status='draft'
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute("UPDATE projects SET last_opened=?, status='draft' WHERE id=?", (now, project_id))
        conn.commit()
        conn.close()

        # Load content
        # UPDATED: Added encoding='utf-8' to prevent read errors
        with open(temp_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # =========================================================
    # 6.3 AUTOSAVE (PDF Source 164)
    # =========================================================
    # In lifecycle_manager.py

    def autosave(self, data_dict):
        """
        Writes real-time changes to autosave.json.
        """
        if not self.active_project_id:
            print("❌ Autosave failed: No active project ID")
            return

        # 1. Target the TEMP folder specifically
        project_folder = os.path.join(PROJECTS_ROOT, self.active_project_id)
        temp_folder = os.path.join(project_folder, "temp")
        
        # Ensure folder exists (Safety check)
        os.makedirs(temp_folder, exist_ok=True)
        
        temp_path = os.path.join(temp_folder, "autosave.json")
        
        # 2. Atomic Write (Prevents corruption if app crashes while writing)
        temp_path_tmp = temp_path + ".tmp"
        try:
            # UPDATED: Added encoding='utf-8' to fix 'charmap' codec error
            with open(temp_path_tmp, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=4, ensure_ascii=False)
            
            # Rename tmp to actual only after successful write
            os.replace(temp_path_tmp, temp_path)
            print(f"✅ Autosaved to: {temp_path}")
            
        except Exception as e:
            print(f"❌ Autosave File Error: {e}")
            
    # =========================================================
    # 6.4 MANUAL SAVE (PDF Source 195)
    # =========================================================
    def manual_save(self):
        """
        PDF Source 195: Promotes Temp -> Main.
        1. Copy autosave.json -> main_file.json
        2. Calculate Hash
        3. Update DB (status='saved')
        4. Trigger Backup
        """
        if not self.active_project_id:
            return

        project_folder = os.path.join(PROJECTS_ROOT, self.active_project_id)
        temp_path = os.path.join(project_folder, "temp", "autosave.json")
        main_path = os.path.join(project_folder, "main_file.json")

        # 1. Copy Temp -> Main
        if os.path.exists(temp_path):
            shutil.copy2(temp_path, main_path)

        # 2. Calculate Hash (PDF Source 201)
        sha256_hash = hashlib.sha256()
        with open(main_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()

        # 3. Update DB (PDF Source 198)
        now = datetime.datetime.now().isoformat()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE projects 
            SET status='saved', hash_key=?, saved_by_user=?, modified_on=? 
            WHERE id=?
        """, (file_hash, now, now, self.active_project_id))
        conn.commit()
        conn.close()

        # 4. Database Backup (PDF Source 228)
        self.create_db_backup()

    # =========================================================
    # 9. DATABASE BACKUP (PDF Source 228)
    # =========================================================
    def create_db_backup(self):
        if not os.path.exists(DB_PATH):
            return
        
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"project_manager_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        shutil.copy2(DB_PATH, backup_path)
        # Optional: Log backup creation

    # =========================================================
    # 8. APP EXIT (PDF Source 219)
    # =========================================================
    def on_app_exit(self):
        """
        Returns a list of unsaved project names to prompt the user.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM projects WHERE status='draft'")
        unsaved = cursor.fetchall() # List of (id, name)
        conn.close()
        
        return unsaved