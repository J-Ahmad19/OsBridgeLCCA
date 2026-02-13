import sqlite3
import os

class MaterialDatabaseManager:
    def __init__(self, db_folder="user_databases"):
        self.db_folder = db_folder
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)
            
        # --- CHANGE 1: SINGLE MASTER DATABASE FILE ---
        self.master_db_path = os.path.join(self.db_folder, "Master_Library.db")
        self.init_db()

    def init_db(self):
        """Creates the tables in the single master database."""
        try:
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()
            
            # --- CHANGE 2: Table to track 'Virtual Database' names ---
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS library_names (
                    name TEXT PRIMARY KEY
                )
            ''')
            
            # Ensure 'Default_Library' always exists
            cursor.execute("INSERT OR IGNORE INTO library_names (name) VALUES ('Default_Library')")

            # --- CHANGE 3: Added 'library_name' column to main table ---
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS saved_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_name TEXT NOT NULL,
                    unit TEXT,
                    rate REAL,
                    rate_source TEXT,
                    carbon_emission TEXT,
                    carbon_source TEXT,
                    carbon_unit TEXT,
                    conversion_factor TEXT,
                    category TEXT,       -- e.g., 'Excavation', 'Concrete'
                    library_name TEXT,   -- REPLACES the old filename concept
                    FOREIGN KEY(library_name) REFERENCES library_names(name),
                    UNIQUE(material_name, rate, rate_source, library_name)
                )
            ''')
            conn.commit()
            conn.close()
            print(f"✅ [DB Manager] Master database ready at: {self.master_db_path}")
        except sqlite3.Error as e:
            print(f"❌ [DB Manager] Init Error: {e}")

    def get_available_databases(self):
        """
        Returns list of virtual libraries from the single DB.
        Structure matches your old return format so UI doesn't break.
        """
        conn = sqlite3.connect(self.master_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM library_names ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "name": row[0], 
                "path": self.master_db_path # All point to same file now
            })
        return results

    def create_new_database(self, db_name):
        """
        Instead of making a file, this just registers a new name in library_names.
        """
        clean_name = "".join(x for x in db_name if x.isalnum() or x in "_- ")
        if not clean_name: clean_name = "New_Library"
            
        conn = sqlite3.connect(self.master_db_path)
        try:
            conn.execute("INSERT INTO library_names (name) VALUES (?)", (clean_name,))
            conn.commit()
            print(f"✅ Created new library tag: {clean_name}")
        except sqlite3.IntegrityError:
            print(f"⚠️ Library '{clean_name}' already exists.")
        conn.close()
        
        return self.master_db_path

    def search_all_databases(self, query):
        """
        Much simpler now: Just one SELECT query with a LIKE clause.
        """
        results = []
        try:
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()
            
            sql = """
                SELECT material_name, library_name 
                FROM saved_materials 
                WHERE material_name LIKE ? 
                LIMIT 10
            """
            cursor.execute(sql, (f'%{query}%',))
            rows = cursor.fetchall()
            
            for row in rows:
                results.append({
                    'name': row[0], 
                    'db_name': row[1], # This is the library name
                    'db_path': self.master_db_path
                })
            conn.close()
        except Exception as e:
            print(f"❌ Search Error: {e}")
                
        return results

    def get_material_details(self, name):
        try:
            conn = sqlite3.connect(self.master_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # We select the first match (or you can refine to filter by library too)
            cursor.execute("SELECT * FROM saved_materials WHERE material_name = ?", (name,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                data = dict(row)
                data['origin_db_name'] = row['library_name']
                return data
        except Exception:
            pass
        return None