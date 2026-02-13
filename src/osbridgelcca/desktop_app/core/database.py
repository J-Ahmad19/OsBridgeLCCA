import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes schema based on PDF Source 11 & 12."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fixed: Removed the inline comment on 'status' to prevent SQL syntax errors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, 
                name TEXT,
                main_path TEXT,
                temp_path TEXT,
                status TEXT,
                hash_key TEXT,
                user_name TEXT,
                sys_info TEXT,
                created_on TEXT,
                modified_on TEXT,
                saved_by_user TEXT,
                last_opened TEXT,
                version INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def insert_project(self, data):
        """Inserts a new project record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO projects (
                id, name, main_path, temp_path, status, 
                hash_key, user_name, sys_info, created_on, 
                modified_on, last_opened, version
            ) VALUES (
                :id, :name, :main_path, :temp_path, :status, 
                :hash_key, :user_name, :sys_info, :created_on, 
                :modified_on, :last_opened, :version
            )
        ''', data)
        
        conn.commit()
        conn.close()