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
        if not target_library_name: return

        try:
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()

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
                category_tag,
                target_library_name
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
        timestamp = datetime.datetime.now().isoformat()
        is_custom_flag = raw_inputs.get("is_custom", True)

        values_data = {
            "material_name": raw_inputs.get("type") or raw_inputs.get("material_name"),
            "quantity": raw_inputs.get("quantity"),
            "unit": raw_inputs.get("unit_m3") or raw_inputs.get("unit") or raw_inputs.get("unit_A"),
            "rate": raw_inputs.get("rate"),
            "rate_source": raw_inputs.get("rate_data_source") or raw_inputs.get("rate_source"),
            "carbon_emission": raw_inputs.get("carbon_emission", "not_available"),
            "carbon_unit": raw_inputs.get("carbon_unit", ""),
            "conversion_factor": raw_inputs.get("conversion_factor", ""),
            "carbon_source": raw_inputs.get("carbon_source", ""),
            "grade": raw_inputs.get("grade", "Standard"),
            "type": raw_inputs.get("type", "material"),
            "is_recyclable": raw_inputs.get("recyclable", False),
            "scrap_rate": raw_inputs.get("scrap_rate", 5),
            "recyclability_percentage": raw_inputs.get("recycle_percentage", 80)
        }

        meta_data = {
            "created_on": raw_inputs.get("created_on", timestamp) if not is_new else timestamp,
            "modified_on": timestamp,
            "is_user_defined": is_custom_flag,
            "is_from_db": not is_custom_flag,
            "source_version": "v1.0"
        }

        state_data = {
            #"is_active": True,
            "removed_by_user": False,
            "included_in_carbon_emission": True,
            "included_in_recyclability": raw_inputs.get("recyclable", False)
        }

        return {
            "id": raw_inputs.get("id", str(uuid.uuid4())),
            "values": values_data,
            "meta": meta_data,
            "state": state_data
        }

    # --- CORE METHODS ---

    def add_material_item(self, project_id, category, sub_category, material_data):
        """
        Adds a single material item.
        CRITICAL UPDATE: Now checks for duplicates before adding.
        If found (even if deleted), it updates/resurrects the existing item.
        """
        try:
            # 1. Open the project
            project_data = self.lifecycle.open_project(project_id)

            # 2. Ensure Schema Exists
            if "input_param" not in project_data: project_data["input_param"] = {}
            if category not in project_data["input_param"]: project_data["input_param"][category] = {}
            if sub_category not in project_data["input_param"][category]: project_data["input_param"][category][sub_category] = {}
            
            target_node = project_data["input_param"][category][sub_category]
            if "items" not in target_node: target_node["items"] = []

            # 3. CHECK FOR DUPLICATES (The Fix)
            # Normalize name for comparison (strip whitespace)
            new_name = (material_data.get("type") or material_data.get("material_name") or "").strip()
            
            existing_item = None
            for item in target_node["items"]:
                current_name = (item.get("values", {}).get("material_name") or "").strip()
                if current_name == new_name:
                    existing_item = item
                    break
            
            if existing_item:
                # --- UPDATE EXISTING ITEM ---
                print(f"🔄 Item '{new_name}' exists. Updating ID: {existing_item['id']}")
                
                # Update Values
                existing_item["values"]["quantity"] = material_data.get("quantity")
                existing_item["values"]["rate"] = material_data.get("rate")
                if material_data.get("unit_m3") or material_data.get("unit"): 
                    existing_item["values"]["unit"] = material_data.get("unit_m3") or material_data.get("unit")

                # Resurrect if it was deleted
                if "state" not in existing_item: existing_item["state"] = {}
                existing_item["state"]["removed_by_user"] = False
               # existing_item["state"]["is_active"] = True
                
                # Update Timestamp
                existing_item["meta"]["modified_on"] = datetime.datetime.now().isoformat()
                
                target_id = existing_item["id"]

            else:
                # --- CREATE NEW ITEM ---
                new_item = self._create_item_structure(material_data, is_new=True)
                target_node["items"].append(new_item)
                target_id = new_item["id"]

            # 4. TRIGGER AUTOSAVE
            self.lifecycle.active_project_id = project_id 
            self.lifecycle.autosave(project_data)

            # 5. DATABASE SYNC
            raw_target = material_data.get("target_db")
            if raw_target:
                target_library_name = os.path.splitext(os.path.basename(raw_target))[0]
                self._save_to_user_library(material_data, sub_category, target_library_name)

            return target_id

        except Exception as e:
            print(f"❌ Data Manager Error: {e}")
            traceback.print_exc()
            return None

    def bulk_import_excel_data(self, project_id, parsed_data):
        """
        Imports Excel data.
        NOTE: Even if your UI calls add_material_item individually, this logic serves as a fallback 
        if you ever call bulk_import directly.
        """
        if not project_id: return False

        try:
            # 1. Open the existing project data
            project_data = self.lifecycle.open_project(project_id)
            
            # Ensure structure
            if "input_param" not in project_data: project_data["input_param"] = {}
            if "construction_work_data" not in project_data["input_param"]:
                project_data["input_param"]["construction_work_data"] = {}

            sheet_map = {
                "foundation": "foundation", "sub structure": "sub_structure", "sub-structure": "sub_structure",
                "substructure": "sub_structure", "super structure": "super_structure", "super-structure": "super_structure",
                "superstructure": "super_structure", "miscellaneous": "other", "auxiliary works": "other", "auxiliary": "other"
            }

            items_updated = 0
            items_added = 0

            for section in parsed_data:
                raw_sheet_name = str(section.get('sheetName', '')).lower().strip()
                target_sub_cat = next((v for k, v in sheet_map.items() if k in raw_sheet_name), None)
                
                if not target_sub_cat: continue

                if target_sub_cat not in project_data["input_param"]["construction_work_data"]:
                    project_data["input_param"]["construction_work_data"][target_sub_cat] = {"items": []}
                
                target_list = project_data["input_param"]["construction_work_data"][target_sub_cat]["items"]

                for row in section.get('data', []):
                    item_name = str(row.get("name")).strip()
                    
                    # Search for ANY item with same name (ignoring deleted status)
                    existing_item = next((item for item in target_list if item["values"]["material_name"] == item_name), None)

                    if existing_item:
                        if "state" not in existing_item: existing_item["state"] = {}
                        existing_item["state"]["removed_by_user"] = False
                        existing_item["state"]["is_active"] = True
                        existing_item["values"]["quantity"] = row.get("quantity")
                        existing_item["values"]["rate"] = row.get("rate")
                        if row.get("unit"): existing_item["values"]["unit"] = row.get("unit")
                        existing_item["meta"]["modified_on"] = datetime.datetime.now().isoformat()
                        items_updated += 1
                    else:
                        mapped_data = {
                            "type": item_name, "material_name": item_name,
                            "quantity": row.get("quantity"), "unit_m3": row.get("unit"),
                            "rate": row.get("rate"), "rate_data_source": row.get("rate_src"),
                            "carbon_emission": row.get("carbon_emission", "not_available"),
                            "carbon_source": row.get("carbon_emission_src", ""),
                            "carbon_unit": row.get("carbon_emission_units", ""),
                            "conversion_factor": row.get("conversion_factor", ""),
                            "recyclable": row.get("recycleable") == "recyclable",
                            "scrap_rate": row.get("scrap_rate", 5),
                            "recycle_percentage": row.get("recycle_percentage", 80),
                            "is_custom": True 
                        }
                        new_item = self._create_item_structure(mapped_data, is_new=True)
                        target_list.append(new_item)
                        items_added += 1

            self.lifecycle.active_project_id = project_id 
            self.lifecycle.autosave(project_data)
            print(f"✅ [Import] Added {items_added} new, Updated {items_updated} existing.")
            return True

        except Exception as e:
            print(f"❌ [Import Error] {e}")
            return False
        
    def update_material_item(self, project_id, category, sub_category, item_id, updated_values):
        if not project_id: return False
        try:
            project_data = self.lifecycle.open_project(project_id)
            try:
                items_list = project_data["input_param"][category][sub_category]["items"]
            except KeyError:
                return False
            
            for item in items_list:
                if item["id"] == item_id:
                    if "values" in item:
                        item["values"].update({k: v for k, v in updated_values.items() if k in item["values"]})
                        # Map specific keys
                        if "type" in updated_values: item["values"]["material_name"] = updated_values["type"]
                        if "unit_m3" in updated_values: item["values"]["unit"] = updated_values["unit_m3"]
                        if "rate_data_source" in updated_values: item["values"]["rate_source"] = updated_values["rate_data_source"]
                        if "recyclable" in updated_values:
                            item["values"]["is_recyclable"] = updated_values["recyclable"]
                            if "state" in item: item["state"]["included_in_recyclability"] = updated_values["recyclable"]
                        if "scrap_rate" in updated_values: item["values"]["scrap_rate"] = updated_values["scrap_rate"]
                        if "recycle_percentage" in updated_values: item["values"]["recyclability_percentage"] = updated_values["recycle_percentage"]

                    item["meta"]["modified_on"] = datetime.datetime.now().isoformat()
                    self.lifecycle.active_project_id = project_id
                    self.lifecycle.autosave(project_data)

                    raw_target = item["values"].get("target_db") or updated_values.get("target_db")
                    if raw_target:
                        target_library_name = os.path.splitext(os.path.basename(raw_target))[0]
                        full_data = item["values"].copy()
                        full_data.update(updated_values)
                        self._save_to_user_library(full_data, sub_category, target_library_name)
                    return True
            return False
        except Exception as e:
            print(f"❌ Update Error: {e}")
            return False

    def get_all_materials(self, project_id, category, sub_category):
        if not project_id: return []
        try:
            project_data = self.lifecycle.open_project(project_id)
            all_items = project_data.get("input_param", {}).get(category, {}).get(sub_category, {}).get("items", [])
            return [i for i in all_items if not i.get("state", {}).get("removed_by_user", False)]
        except Exception:
            return []
        
    def soft_delete_material_item(self, project_id, category, sub_category, item_id):
        """
        Soft Delete + Clean Sweep.
        Marks ALL items with the same name as deleted to handle any duplicates.
        """
        if not project_id: return False
        try:
            project_data = self.lifecycle.open_project(project_id)
            try:
                target_node = project_data["input_param"][category][sub_category]
                items_list = target_node.get("items", [])
            except KeyError:
                return False

            target_name = None
            for item in items_list:
                if item["id"] == item_id:
                    target_name = item.get("values", {}).get("material_name")
                    break
            
            if not target_name: return False

            deleted_count = 0
            for item in items_list:
                if item.get("values", {}).get("material_name") == target_name:
                    if "state" not in item: item["state"] = {}
                    item["state"]["removed_by_user"] = True
                    item["state"]["is_active"] = False
                    if "meta" in item: item["meta"]["modified_on"] = datetime.datetime.now().isoformat()
                    deleted_count += 1

            if deleted_count > 0:
                self.lifecycle.active_project_id = project_id 
                self.lifecycle.autosave(project_data)
                print(f"🗑️ Clean Sweep: Marked {deleted_count} items named '{target_name}' as removed.")
                return True
            return False
        except Exception as e:
            print(f"❌ Soft Delete Error: {e}")
            return False