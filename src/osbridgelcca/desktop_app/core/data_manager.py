import uuid
import datetime
import traceback
import sqlite3
import os
import json
from .lifecycle_manager import LifecycleManager

class ProjectDataManager:
    def __init__(self):
        self.lifecycle = LifecycleManager()
        # SINGLE DATABASE ARCHITECTURE:
        # We now point exclusively to one master database file.
        self.master_db_path = os.path.join("user_databases", "Master_Library.db")

    # --- DATABASE HELPER METHODS ---

    def _save_to_user_library(self, material_values, category_tag, target_library_name):
        """
        Inserts a material into the Master Database, tagged with the specific Library Name.
        """
        if not target_library_name:
            return

        try:
            # Connect to the single Master DB
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()

            # Ensure the table exists with the new 'library_name' column
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
                    category TEXT,
                    library_name TEXT,
                    UNIQUE(material_name, rate, rate_source, library_name)
                )
            ''')

            # Insert data including the library_name tag
            cursor.execute('''
                INSERT OR IGNORE INTO saved_materials (
                    material_name, unit, rate, rate_source, 
                    carbon_emission, carbon_source, carbon_unit, 
                    conversion_factor, category, library_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                material_values.get('type') or material_values.get('material_name', 'Unknown'),
                material_values.get('unit_m3') or material_values.get('unit_A', ''),
                material_values.get('rate', 0),
                material_values.get('rate_data_source', ''),
                material_values.get('carbon_emission', ''),
                material_values.get('carbon_source', ''),
                material_values.get('carbon_unit', ''),
                material_values.get('conversion_factor', ''),
                category_tag,        # Material Category (e.g. 'Concrete')
                target_library_name  # Virtual Library Name (e.g. 'My Project Lib')
            ))
            
            conn.commit()
            if cursor.rowcount > 0:
                print(f"✅ [DB] Successfully saved '{material_values.get('type')}' to Library: {target_library_name}")
            else:
                print(f"ℹ️ [DB] '{material_values.get('type')}' already exists in Library: {target_library_name}")
                
            conn.close()
        except Exception as e:
            print(f"❌ [DB Save Error]: {e}")

    # --- SCHEMA HELPER ---

    def _create_item_structure(self, raw_inputs, is_new=True):
        """
        Internal Helper: Converts raw flat data into strict PDF Schema.
        Structure: { id, values, meta, state }
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Determine the origin strictly
        # If is_custom is True, it is User Defined.
        # If is_custom is False, it came from a DB/SOR.
        is_custom_flag = raw_inputs.get("is_custom", True)

        # 1. VALUES: Pure Business Data (The "What")
        # Updated to include recyclability data inside 'values' as per requirements
        values_data = {
            "material_name": raw_inputs.get("type") or raw_inputs.get("material_name"),
            "quantity": raw_inputs.get("quantity"),
            "unit": raw_inputs.get("unit_m3") or raw_inputs.get("unit"),
            "rate": raw_inputs.get("rate"),
            "rate_source": raw_inputs.get("rate_data_source") or raw_inputs.get("rate_source"),
            "carbon_emission": raw_inputs.get("carbon_emission", "not_available"),
            "carbon_unit": raw_inputs.get("carbon_unit", ""),
            "conversion_factor": raw_inputs.get("conversion_factor", ""),
            "carbon_source": raw_inputs.get("carbon_source", ""),
            "grade": raw_inputs.get("grade", "Standard"),
            "type": raw_inputs.get("type", "material"),
            
            # --- MOVED FROM STATE TO VALUES (MATCHING PHOTO) ---
            "is_recyclable": raw_inputs.get("recyclable", False),
            "scrap_rate": raw_inputs.get("scrap_rate", 5), # Defaulting to 5 or 0 based on input
            "recyclability_percentage": raw_inputs.get("recycle_percentage", 80)
        }

        # 2. META: Origin & Lifecycle (The "Who/When/Where")
        meta_data = {
            "created_on": raw_inputs.get("created_on", timestamp) if not is_new else timestamp,
            "modified_on": timestamp,
            "is_user_defined": is_custom_flag,       # True if Custom
            "is_from_db": not is_custom_flag,        # True ONLY if NOT Custom (Mutual Exclusivity) 
            "source_version": "v1.0"
        }

        # 3. STATE: Application Logic & Flags (The "Status")
        state_data = {
            "is_active": True,
            "removed_by_user": False,
            "included_in_carbon_emission": True,
            # Kept solely as a logic flag, though data is now in values['is_recyclable']
            "included_in_recyclability": raw_inputs.get("recyclable", False)
        }

        # Combine into final strict structure
        return {
            "id": raw_inputs.get("id", str(uuid.uuid4())),
            "values": values_data,
            "meta": meta_data,
            "state": state_data
        }

    # --- CORE METHODS ---

    def bulk_import_excel_data(self, project_id, parsed_data):
        """
        Takes the raw list of sections from the Excel Parser, converts them 
        to the strict schema, and saves them directly to autosave.json.
        """
        if not project_id:
            print("❌ [Import] No Active Project ID found.")
            return False

        try:
            # 1. Open the existing project data (autosave.json)
            project_data = self.lifecycle.open_project(project_id)
            
            # Ensure the structure exists
            if "input_param" not in project_data: 
                project_data["input_param"] = {}
            if "construction_work_data" not in project_data["input_param"]:
                project_data["input_param"]["construction_work_data"] = {}

            # 2. Map Excel Sheet Names to your JSON Schema Keys
            sheet_map = {
                "foundation": "foundation",
                "sub structure": "sub_structure",
                "sub-structure": "sub_structure",
                "substructure": "sub_structure",
                "super structure": "super_structure", 
                "super-structure": "super_structure",
                "superstructure": "super_structure",
                "miscellaneous": "other",
                "auxiliary works": "other",
                "auxiliary": "other"
            }

            items_added_count = 0

            # 3. Iterate through the parsed Excel sections
            for section in parsed_data:
                raw_sheet_name = str(section.get('sheetName', '')).lower().strip()
                
                # Find the target sub-category (e.g., 'foundation')
                target_sub_cat = None
                for key_alias, key_real in sheet_map.items():
                    if key_alias in raw_sheet_name:
                        target_sub_cat = key_real
                        break
                
                if not target_sub_cat:
                    print(f"⚠️ [Import] Skipped unknown sheet: {raw_sheet_name}")
                    continue

                # Ensure the path exists in project_data
                if target_sub_cat not in project_data["input_param"]["construction_work_data"]:
                    project_data["input_param"]["construction_work_data"][target_sub_cat] = {"items": []}
                
                target_list = project_data["input_param"]["construction_work_data"][target_sub_cat].setdefault("items", [])

                # 4. Process individual rows
                for row in section.get('data', []):
                    # Prepare data dictionary for _create_item_structure
                    # MAPPING UPDATED TO MATCH PARSED EXCEL KEYS FROM TERMINAL
                    mapped_data = {
                        "type": row.get("name"),           
                        "material_name": row.get("name"),
                        "quantity": row.get("quantity"),
                        "unit_m3": row.get("unit"),        
                        "rate": row.get("rate"),
                        "rate_data_source": row.get("rate_src"),
                        "carbon_emission": row.get("carbon_emission", "not_available"),
                        "carbon_source": row.get("carbon_emission_src", ""),
                        "carbon_unit": row.get("carbon_emission_units", ""), # Updated Key
                        "conversion_factor": row.get("conversion_factor", ""),
                        # Logic check for recyclable string to boolean
                        "recyclable": row.get("recycleable") == "recyclable", 
                        "scrap_rate": row.get("scrap_rate", 5),
                        "recycle_percentage": row.get("recycle_percentage", 80),
                        "is_custom": True # Imported data is treated as user-defined
                    }

                    # Create the strict schema item
                    new_item = self._create_item_structure(mapped_data, is_new=True)
                    
                    # Append to list
                    target_list.append(new_item)
                    items_added_count += 1

            # 5. TRIGGER AUTOSAVE (Write to autosave.json)
            self.lifecycle.active_project_id = project_id 
            self.lifecycle.autosave(project_data)
            
            print(f"✅ [Import] Successfully saved {items_added_count} items to autosave.json")
            return True

        except Exception as e:
            print(f"❌ [Import Error] {e}")
            traceback.print_exc()
            return False

    def add_material_item(self, project_id, category, sub_category, material_data):
        try:
            # 1. Open the project
            project_data = self.lifecycle.open_project(project_id)

            # 2. Ensure Schema Exists
            if "input_param" not in project_data: project_data["input_param"] = {}
            if category not in project_data["input_param"]: project_data["input_param"][category] = {}
            if sub_category not in project_data["input_param"][category]: project_data["input_param"][category][sub_category] = {}
            
            target_node = project_data["input_param"][category][sub_category]
            if "items" not in target_node: target_node["items"] = []

            # 3. Create the Record using strict Schema Helper
            new_item = self._create_item_structure(material_data, is_new=True)

            # 4. Append
            target_node["items"].append(new_item)

            # 5. TRIGGER AUTOSAVE
            self.lifecycle.active_project_id = project_id 
            self.lifecycle.autosave(project_data)

            # 6. DATABASE SYNC (Single DB Logic)
            # We use raw material_data['target_db'] here because 'meta.source_db' might be cleared 
            # if is_user_defined is True, but we still might want to SAVE it to the DB.
            raw_target = material_data.get("target_db")
            
            if raw_target:
                target_library_name = os.path.splitext(os.path.basename(raw_target))[0]
                self._save_to_user_library(material_data, sub_category, target_library_name)

            return new_item["id"]

        except Exception as e:
            print(f"❌ Data Manager Error: {e}")
            traceback.print_exc()
            return None
        
    def update_material_item(self, project_id, category, sub_category, item_id, updated_values):
        """
        Updates an existing material item.
        """
        if not project_id: return False

        try:
            project_data = self.lifecycle.open_project(project_id)
            
            # Safe Navigation
            try:
                items_list = project_data["input_param"][category][sub_category]["items"]
            except KeyError:
                print(f"❌ Error: Path {category}/{sub_category}/items not found.")
                return False
            
            for item in items_list:
                if item["id"] == item_id:
                    # Update Logic:
                    # 1. Update 'values' dictionary
                    if "values" in item:
                        current_keys = item["values"].keys()
                        safe_updates = {k: v for k, v in updated_values.items() if k in current_keys}
                        item["values"].update(safe_updates)

                        # Handle special mapped keys
                        if "type" in updated_values and "material_name" in item["values"]:
                            item["values"]["material_name"] = updated_values["type"]
                        if "unit_m3" in updated_values and "unit" in item["values"]:
                            item["values"]["unit"] = updated_values["unit_m3"]
                        if "rate_data_source" in updated_values and "rate_source" in item["values"]:
                            item["values"]["rate_source"] = updated_values["rate_data_source"]
                        
                        # --- MAPPING RECYCLABILITY UPDATES TO 'VALUES' ---
                        if "recyclable" in updated_values:
                            item["values"]["is_recyclable"] = updated_values["recyclable"]
                            # Also update the logic flag in state if it exists
                            if "state" in item: item["state"]["included_in_recyclability"] = updated_values["recyclable"]
                        
                        if "scrap_rate" in updated_values:
                            item["values"]["scrap_rate"] = updated_values["scrap_rate"]
                            
                        if "recycle_percentage" in updated_values:
                            item["values"]["recyclability_percentage"] = updated_values["recycle_percentage"]

                    # 3. Update Timestamp
                    item["meta"]["modified_on"] = datetime.datetime.now().isoformat()
                    
                    # Save immediately
                    self.lifecycle.active_project_id = project_id
                    self.lifecycle.autosave(project_data)
                    print(f"✅ Item {item_id} updated.")

                    # DATABASE SYNC (Single DB Logic)
                    raw_target = item["values"].get("target_db") or updated_values.get("target_db")
                    if raw_target:
                        target_library_name = os.path.splitext(os.path.basename(raw_target))[0]
                        full_data_for_db = item["values"].copy()
                        full_data_for_db.update(updated_values)
                        self._save_to_user_library(full_data_for_db, sub_category, target_library_name)

                    return True
            
            print(f"⚠️ Item {item_id} not found.")
            return False

        except Exception as e:
            print(f"❌ Update Error: {e}")
            traceback.print_exc()
            return False

    def get_all_materials(self, project_id, category, sub_category):
        """Helper to populate UI tables."""
        if not project_id: return []
        
        try:
            project_data = self.lifecycle.open_project(project_id)
            return project_data.get("input_param", {}).get(category, {}).get(sub_category, {}).get("items", [])
        except Exception:
            return []
        
    def soft_delete_material_item(self, project_id, category, sub_category, item_id):
        """
        1. Updates the item state to marked as removed (for bin snapshot).
        2. Saves the item to the recycle bin.
        3. PERMANENTLY REMOVES it from autosave.json (restoring hard delete behavior).
        """
        if not project_id: return False

        try:
            # 1. Open Project
            project_data = self.lifecycle.open_project(project_id)
            
            # 2. Navigate to the list
            try:
                target_node = project_data["input_param"][category][sub_category]
                items_list = target_node.get("items", [])
            except KeyError:
                print(f"⚠️ Path {category}/{sub_category} not found.")
                return False

            # 3. Find the specific item to backup
            item_to_delete = None
            for item in items_list:
                if item["id"] == item_id:
                    item_to_delete = item
                    break

            if item_to_delete:
                # --- FIX START: UPDATE STATE IN MEMORY BEFORE BINNING ---
                # We modify the object in memory so the bin snapshot reflects the deleted status.
                if "state" in item_to_delete:
                    item_to_delete["state"]["removed_by_user"] = True
                    item_to_delete["state"]["is_active"] = False
                
                # A. SAVE TO BIN (Now it will have 'removed_by_user': true)
                self._save_to_recycle_bin(project_id, item_to_delete, category, sub_category)
                
                # B. REMOVE FROM AUTOSAVE.JSON (Hard Delete)
                target_node["items"] = [item for item in items_list if item["id"] != item_id]
                
                # C. SAVE CHANGES
                self.lifecycle.active_project_id = project_id 
                self.lifecycle.autosave(project_data)
                
                print(f"🗑️ Item {item_id} archived to bin and permanently deleted from autosave.json.")
                return True
            else:
                print(f"⚠️ Item {item_id} not found for deletion.")
                return False

        except Exception as e:
            print(f"❌ Delete Error: {e}")
            traceback.print_exc()
            return False

    def _save_to_recycle_bin(self, project_id, item_data, category, sub_category):
        """Helper to append deleted item to a bin file"""
        
        # --- PATH FIX: Calculate Absolute Path based on file location ---
        current_dir = os.path.dirname(os.path.abspath(__file__)) 
        desktop_app_dir = os.path.dirname(current_dir)           
        package_dir = os.path.dirname(desktop_app_dir)           
        projects_root = os.path.join(package_dir, "projects")
        
        project_path = os.path.join(projects_root, project_id)

        # Fallback safety check
        if not os.path.exists(project_path):
             print(f"⚠️ Warning: Project path not found at {project_path}. Attempting to save anyway.")

        bin_folder = os.path.join(project_path, "bin")
        os.makedirs(bin_folder, exist_ok=True)
        
        bin_file = os.path.join(bin_folder, "recycle_bin.json")
        
        bin_data = []
        if os.path.exists(bin_file):
            try:
                with open(bin_file, 'r') as f:
                    bin_data = json.load(f)
            except json.JSONDecodeError:
                bin_data = []

        # Add metadata about deletion
        deletion_entry = {
            "deleted_at": datetime.datetime.now().isoformat(),
            "original_category": category,
            "original_sub_category": sub_category,
            "item_data": item_data
        }
        
        bin_data.append(deletion_entry)
        
        with open(bin_file, 'w') as f:
            json.dump(bin_data, f, indent=4)