
"""
<Author>: Prerna Praveen Vidyarthi
<Intern>: FOSSEE Summer Fellowship 2025
<Github>: https://github.com/prerna2024-cyber
<Email>: vidyarthiprerna637@gmail.com
"""
from PySide6.QtCore import (QSize, Qt, QPropertyAnimation, QEasingCurve)
from PySide6.QtGui import (QAction, QFont, QFontDatabase, QIcon)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QTextEdit, QScrollArea, QSpacerItem, QSizePolicy,
                               QMenu, QMenuBar, QPushButton, QWidget, QLabel, QVBoxLayout, QGridLayout, 
                               QLineEdit, QComboBox, QFileDialog, QDialog, QFormLayout, QDialogButtonBox, QMessageBox)

from osbridgelcca.desktop_app.widgets.title_bar import CustomTitleBar
from osbridgelcca.desktop_app.widgets.project_details_right_widget import ProjectDetailsWidget
from osbridgelcca.desktop_app.widgets.tutorial_widget_left import TutorialWidget
from osbridgelcca.desktop_app.widgets.results_widget import ResultsWidget
from osbridgelcca.desktop_app.widgets.comparison_widget import ComparisonWidget
from osbridgelcca.desktop_app.widgets.structure_works_data.foundation_widget import Foundation
from osbridgelcca.desktop_app.widgets.structure_works_data.super_structure_widget import SuperStructure
from osbridgelcca.desktop_app.widgets.structure_works_data.sub_structure_widget import SubStructure
from osbridgelcca.desktop_app.widgets.structure_works_data.auxiliary_works_widget import AuxiliaryWorks
from osbridgelcca.desktop_app.widgets.financial_data import FinancialData
from osbridgelcca.desktop_app.widgets.carbon_emission_data.carbon_emission_data import CarbonEmissionData
from osbridgelcca.desktop_app.widgets.carbon_emission_data.carbon_emission_cost_data import CarbonEmissionCostData
from osbridgelcca.desktop_app.widgets.carbon_emission_data.carbon_machinery_widget import CarbonMachineryWidget
from osbridgelcca.desktop_app.widgets.carbon_emission_data.Transportation_data import TransportationMainWidget
from osbridgelcca.desktop_app.widgets.bridge_and_traffic_data import BridgeAndTrafficData
from osbridgelcca.desktop_app.widgets.maintenance_repair_data import MaintenanceRepairData
from osbridgelcca.desktop_app.widgets.demolition_and_recycling_data import DemolitionAndRecyclingData
from osbridgelcca.desktop_app.widgets.project_details_left_widget import ProjectDetailsLeft
from osbridgelcca.desktop_app.widgets.recyclable import RecyclableWidget
from osbridgelcca.desktop_app.widgets.tab_widget import CustomTabWidget
from osbridgelcca.desktop_app.widgets.utils.data import *
from osbridgelcca.desktop_app.widgets.utils.database import DatabaseManager
from osbridgelcca.desktop_app.resources.resources_rc import *

import pandas as pd
import json
import numpy as np
import os

# JAWWAD : Database Constants Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_DIR, "temp_file_db")
JSON_DB_PATH = os.path.join(DB_FOLDER, "temporary_construction_data.json")

# ================== RITIK : EXCEL PARSING LOGIC ==================

ALLOWED_UNITS = {'cum', 'rmt', 'm2', 'mt', 'nos', 'kg'}
FLEXIBLE_FIELD_CONFIG = ['carbon_emission', 'conversion_factor']
ALLOWED_FLEXIBLE_VALUES = {'not_available'}
ALLOWED_RECYCLE_VALUES = {'recycleable', 'recyclable', 'non-recyclable'}

def clean_header(header_val):
    if not isinstance(header_val, str):
        return str(header_val)
    # Converts 'CID#Item' -> 'item'
    return header_val.replace('CID#', '').lower().strip()

def is_valid_number(val):
    if val is None or val == "":
        return False
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False

def get_row_identifier(sheet, type_name, row_idx, item_code=None):
    # Pandas index 0 = Excel Row 1
    base_id = f"Sheet: '{sheet}', Component: '{type_name}', Row: {row_idx + 1}"
    if item_code:
        return f"{base_id} [Item: {item_code}]"
    return base_id

def normalize_unit_string(val):
    """
    RITIK: Helper to normalize known unit strings, especially handling typos like KgC02e (zero) vs kgCO2e.
    """
    if not isinstance(val, str):
        return val
    
    val_clean = val.strip()
    
    # Specific replacements
    # Case: "KgC02e/kg" (Capital K, C, Zero instead of O) -> "kgCO₂e/kg"
    # Case: "KgCO2e/kg" (Capital K, C, Letter O) -> "kgCO₂e/kg"
    # Case: "kgCO2e/kg" (lowercase k, Letter O) -> "kgCO₂e/kg"
    if val_clean in ["KgC02e/kg", "KgCO2e/kg", "kgCO2e/kg", "kgC02e/kg"]:
        return "kgCO\u2082e/kg"
        
    return val

def parse_and_validate_excel(file_path):
    try:
        all_sheets = pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        return {"fatal_error": f"Failed to read file: {str(e)}"}

    parsed_sections = []
    global_errors = []
    global_warnings = []

    for sheet_name, df in all_sheets.items():
        
        current_section = None
        current_keys = None 
        section_seen_data = {} 

        for idx, row in df.iterrows():
            if row.isnull().all():
                continue

            # Safely get first two string values for detection
            def get_val(r, i):
                if i < len(r) and pd.notna(r[i]):
                    return str(r[i]).strip()
                return ""

            first_val = get_val(row, 0)
            second_val = get_val(row, 1)

            # --- 1. Identify Header (CID#) ---
            # We check col 0 OR col 1 to support the 'Excavation' sheet structure
            is_header_row = first_val.startswith('CID#') or second_val.startswith('CID#')
            
            if is_header_row:
                current_keys = []
                for i, val in enumerate(row):
                    v_str = get_val(row, i)
                    if v_str != "":
                        current_keys.append((i, clean_header(v_str)))
                
                # SPECIAL HANDLING: Excavation Sheet
                # If header starts at index 1 (Name) but index 0 is empty,
                # we explicitly map index 0 to 'item' so we capture the item code.
                has_idx_0 = any(k[0] == 0 for k in current_keys)
                has_name_at_1 = any(k[0] == 1 and k[1] == 'name' for k in current_keys)
                
                if not has_idx_0 and has_name_at_1:
                    current_keys.insert(0, (0, 'item'))
                    
                continue
            
            # --- Skip Visual Headers ---
            if first_val in ['Material', 'SOR Item No.']:
                continue

            # --- 2. Identify Section ---
            col2 = row[2] if len(row) > 2 else np.nan
            col3 = row[3] if len(row) > 3 else np.nan
            
            if pd.notna(row[0]) and pd.isna(col2) and pd.isna(col3):
                if current_section:
                    parsed_sections.append(current_section)
                
                current_section = {
                    "sheetName": sheet_name,
                    "type": first_val, 
                    "data": []
                }
                section_seen_data = {} 
                continue

            # --- 3. Process Data Row ---
            if current_section and current_keys:
                raw_row_data = {}
                for col_idx, key in current_keys:
                    val = row[col_idx] if col_idx < len(row) else None
                    if pd.isna(val) or str(val).strip() == "":
                        raw_row_data[key] = None
                    else:
                        if key == 'carbon_emission_units':
                            val = normalize_unit_string(val)
                        raw_row_data[key] = val

                # === VALIDATION ===
                qty_val = raw_row_data.get('quantity')
                if qty_val is None:
                    continue

                final_row_data = raw_row_data.copy()
                row_has_critical_error = False
                is_duplicate = False
                
                # Context for logging
                item_code = final_row_data.get('item') 
                row_context = get_row_identifier(sheet_name, current_section['type'], idx, item_code)

                # Validate Quantity
                if not is_valid_number(qty_val):
                    global_errors.append(f"{row_context} - Error: Quantity '{qty_val}' is not a valid number.")
                    row_has_critical_error = True

                # Validate Rate
                rate_val = final_row_data.get('rate')
                if rate_val is None:
                    global_errors.append(f"{row_context} - Error: Quantity is present but 'rate' is missing.")
                    row_has_critical_error = True
                elif not is_valid_number(rate_val):
                    global_errors.append(f"{row_context} - Error: Rate '{rate_val}' is not a valid number.")
                    row_has_critical_error = True

                # Validate Sources
                if final_row_data.get('rate_src') is None:
                    global_warnings.append(f"{row_context} - Warning: 'rate_src' is missing.")
                if final_row_data.get('carbon_emission_src') is None:
                    global_warnings.append(f"{row_context} - Warning: 'carbon_emission_src' is missing.")

                # Validate Flexible Numbers
                for field in FLEXIBLE_FIELD_CONFIG:
                    val = final_row_data.get(field)
                    if val is not None:
                        val_str = str(val).strip().lower()
                        if not is_valid_number(val) and val_str not in ALLOWED_FLEXIBLE_VALUES:
                            global_errors.append(f"{row_context} - Error: Field '{field}' value '{val}' is invalid. Must be number or {ALLOWED_FLEXIBLE_VALUES}.")
                            row_has_critical_error = True

                # Validate Units
                unit_val = final_row_data.get('unit')
                if unit_val:
                    if str(unit_val).strip().lower() not in ALLOWED_UNITS:
                        global_errors.append(f"{row_context} - Error: Unit '{unit_val}' is not valid. Allowed: {ALLOWED_UNITS}")
                        row_has_critical_error = True
                else:
                    global_errors.append(f"{row_context} - Error: Unit is missing.")
                    row_has_critical_error = True

                # Validate Recyclability
                perc_val = final_row_data.get('recyclability_percentage')
                if perc_val is None or str(perc_val).strip() == "":
                     global_warnings.append(f"{row_context} - Warning: 'recyclability_percentage' is missing.")
                else:
                    if not is_valid_number(perc_val):
                         global_errors.append(f"{row_context} - Error: 'recyclability_percentage' '{perc_val}' is not a valid number.")
                         row_has_critical_error = True
                    else:
                        if float(perc_val) > 100:
                            global_errors.append(f"{row_context} - Error: 'recyclability_percentage' ({perc_val}) cannot be greater than 100.")
                            row_has_critical_error = True
                        elif float(perc_val) < 0:
                            global_errors.append(f"{row_context} - Error: 'recyclability_percentage' ({perc_val}) cannot be negative.")
                            row_has_critical_error = True

                # Validate Scrap Rate
                scrap_val = final_row_data.get('scrap_rate')
                if scrap_val is None or str(scrap_val).strip() == "":
                    global_warnings.append(f"{row_context} - Warning: 'scrap_rate' is missing.")
                else:
                    if not is_valid_number(scrap_val):
                         global_errors.append(f"{row_context} - Error: 'scrap_rate' '{scrap_val}' is not a valid number.")
                         row_has_critical_error = True

                # === DUPLICATE CHECK ===
                name_val = final_row_data.get('name')
                if name_val:
                    if name_val in section_seen_data:
                        original_entry = section_seen_data[name_val]
                        original_data = original_entry['data']
                        original_loc = original_entry['row_id']

                        if final_row_data == original_data:
                            global_warnings.append(f"{row_context} - Warning: Duplicate material '{name_val}' found with identical values. Rows have been merged.")
                            is_duplicate = True
                        else:
                            global_errors.append(f"{row_context} - Error: Duplicate material '{name_val}' found with conflicting values compared to {original_loc}. User selection required.")
                            is_duplicate = True
                    else:
                        section_seen_data[name_val] = {
                            'data': final_row_data,
                            'row_id': row_context
                        }

                if not row_has_critical_error and not is_duplicate:
                    current_section['data'].append(final_row_data)

        if current_section:
            parsed_sections.append(current_section)

    return {
        "validation_report": {
            "errors": global_errors,
            "warnings": global_warnings
        },
        "parsed_data": parsed_sections
    }

def show_error_message(error_list, parent=None):
    error_text = "❌ ERRORS FOUND - Import Stopped\n\n" + "═" * 60 + "\n"
    for idx, error in enumerate(error_list, 1):
        error_text += f"{idx}. {error}\n"
    error_text += "═" * 60
    QMessageBox.critical(parent, "Excel Import - Errors", error_text)
    return False

def show_warning_message(warning_list, parent=None):
    warning_text = "⚠️ WARNINGS\n\n" + "═" * 60 + "\n"
    for idx, warning in enumerate(warning_list, 1):
        warning_text += f"{idx}. {warning}\n"
    warning_text += "═" * 60 + "\n\nData will be imported with warnings."
    QMessageBox.warning(parent, "Excel Import - Warnings", warning_text)
    return True

# RITIK: End of Excel Parsing Logic
def map_parsed_data_to_widgets(parsed_data, ui_instance):
    # This logic is integrated into distribute_imported_data
    pass

def map_section_to_widget(widget, component_type, data_items):
    # This logic is integrated into distribute_imported_data
    pass

class UiMainWindow(object):
    # --- Ritik: Excel Functionality ---
    def open_excel_dialog(self):
        print("[UI] Upload Excel clicked")
        file_path, _ = QFileDialog.getOpenFileName(None, "Select Excel File", "", "Excel Files (*.xlsx *.xls)")
        if not file_path:
            return

        print(f"[UI] Excel selected: {file_path}")
        result = parse_and_validate_excel(file_path)
        print("\n========== PARSER OUTPUT ==========\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        validation_report = result.get('validation_report', {})
        errors = validation_report.get('errors', [])
        warnings = validation_report.get('warnings', [])
        parsed_data = result.get('parsed_data', [])
        
        if errors:
            show_error_message(errors, parent=self.windows)
            return

        # JAWWAD : Save to JSON immediately after parsing
        self.save_temp_data(parsed_data)
        
        # JAWWAD: Reset lock flag on new upload to allow re-calculation
        self.construction_locked = False 
        print("[LOCK] Construction lock reset due to new data upload.")
        
        if warnings:
            show_warning_message(warnings, parent=self.windows)
        
        print(f"\n[MAPPING] Starting mapping of {len(parsed_data)} section(s)...")
        self.distribute_imported_data(parsed_data)

    # JAWWAD : New method to save parsed data to JSON file
    def save_temp_data(self, parsed_data):
        """Saves the parsed Excel data to a local JSON file."""
        try:
            # Create db directory if it doesn't exist
            if not os.path.exists(DB_FOLDER):
                os.makedirs(DB_FOLDER)
                print(f"[DB] Created database folder at: {DB_FOLDER}")

            # Write data to JSON
            with open(JSON_DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=4, ensure_ascii=False)
            
            print(f"[DB] ✓ Data successfully saved to: {JSON_DB_PATH}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error saving data: {str(e)}")
            return False

    # JAWWAD : New method to calculate cost directly from JSON DB
    def calculate_cost_from_json(self):
        """Reads the JSON DB, calculates costs, and prints a neat dictionary to terminal."""
        if not os.path.exists(JSON_DB_PATH):
            print("[CALC] ❌ No data file found. Please upload Excel first.")
            return None

        print("\n" + "="*60)
        print(" 🏗️  FINAL CONSTRUCTION COST CALCULATION (FROM JSON DB)")
        print("="*60)

        try:
            with open(JSON_DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[CALC] Error reading JSON: {e}")
            return None

        # Initialize Cost Structure
        cost_summary = {
            "FOUNDATION": 0.0,
            "SUB-STRUCTURE": 0.0,
            "SUPER-STRUCTURE": 0.0,
            "MISCELLANEOUS": 0.0
        }

        # Mapping variations in Excel sheet names to our standard Keys
        key_map = {
            'foundation': 'FOUNDATION',
            'sub-structure': 'SUB-STRUCTURE', 'sub structure': 'SUB-STRUCTURE',
            'super-structure': 'SUPER-STRUCTURE', 'super structure': 'SUPER-STRUCTURE',
            'miscellaneous': 'MISCELLANEOUS', 'auxiliary works': 'MISCELLANEOUS'
        }

        # Calculation Loop
        for section in data:
            raw_sheet_name = str(section.get('sheetName', '')).lower().strip()
            category = key_map.get(raw_sheet_name, 'MISCELLANEOUS')
            
            # Print Section Header
            print(f"\n--- Processing: {section.get('type', 'Unknown Component')} ({category}) ---")
            print(f"{'Material':<50} | {'Qty':<10} | {'Rate':<10} | {'Total':<15}")
            print("-" * 90)

            for material in section.get('data', []):
                try:
                    name = material.get('name', 'Unknown')
                    qty = float(material.get('quantity', 0))
                    rate = float(material.get('rate', 0))
                    total = qty * rate

                    # Add to category total
                    cost_summary[category] += total

                    # Print Row
                    print(f"{name:<50} | {qty:<10.2f} | {rate:<10.2f} | {total:<15.2f}")
                except (ValueError, TypeError):
                    continue
        
        # Calculate Grand Total
        grand_total = sum(cost_summary.values())

        # Final Dictionary Output
        print("\n" + "="*60)
        print(" 💰 FINAL COST DICTIONARY")
        print("="*60)
        
        final_output = {
            "breakdown": cost_summary,
            "grand_total": grand_total,
            "currency": "INR"
        }
        
        # Pretty print the dictionary
        print(json.dumps(final_output, indent=4, ensure_ascii=False))
        print("="*60 + "\n")

        return grand_total

    def distribute_imported_data(self, parsed_data):
        print(f"\n[DISTRIBUTE] Started distribution of {len(parsed_data)} section(s)")
        
        sheet_map = {
            "foundation": KEY_FOUNDATION, "sub structure": KEY_SUBSTRUCTURE, "sub-structure": KEY_SUBSTRUCTURE,
            "substructure": KEY_SUBSTRUCTURE, "super structure": KEY_SUPERSTRUCTURE, "super-structure": KEY_SUPERSTRUCTURE,
            "superstructure": KEY_SUPERSTRUCTURE, "miscellaneous": KEY_AUXILIARY, "auxiliary works": KEY_AUXILIARY,
            "auxiliary": KEY_AUXILIARY
        }

        grouped_data = {}
        for section in parsed_data:
            sheet_name_clean = str(section.get('sheetName', '')).lower().strip()
            target_key = None
            for key_alias, key_const in sheet_map.items():
                if key_alias in sheet_name_clean:
                    target_key = key_const
                    break
            if target_key:
                if target_key not in grouped_data: grouped_data[target_key] = []
                grouped_data[target_key].append(section)

        for widget_key, sections in grouped_data.items():
            if self.tabs_active and widget_key in self.active_tab_widgets:
                tab_idx = self.active_tab_widgets[widget_key]
                if hasattr(self.current_right_widget, 'widget'):
                    # JAWWAD: If widgets are cached, accessing via active tab might get the new UI instance
                    # but logic below ensures we load data into it.
                    widget_instance = self.current_right_widget.widget(tab_idx)
                    if hasattr(widget_instance, 'load_from_excel_sections'):
                        widget_instance.load_from_excel_sections(sections)
            else:
                if not self.tabs_active:
                    self.tabs_active = True
                    self.active_tab_widgets = {}
                    self.current_right_widget = CustomTabWidget(parent=self)
                    self.right_panel_placeholder.layout().addWidget(self.current_right_widget)
                
                # JAWWAD: Simplified this block to use the standard add_new_tab_widget method
                # which now handles caching (retrieving existing widget with data).
                if widget_key not in self.active_tab_widgets:
                    self.add_new_tab_widget(widget_key)
                
                if widget_key in self.active_tab_widgets:
                    tab_idx = self.active_tab_widgets[widget_key]
                    widget_instance = self.current_right_widget.widget(tab_idx)
                    if hasattr(widget_instance, 'load_from_excel_sections'):
                        widget_instance.load_from_excel_sections(sections)

    # JAWWAD: New cleanup method added here
    def cleanup_temp_db(self):
        """Removes the temporary JSON database file at application startup."""
        try:
            if os.path.exists(JSON_DB_PATH):
                try:
                    os.remove(JSON_DB_PATH)
                    print(f"[CLEANUP] Existing temporary database deleted: {JSON_DB_PATH}")
                except PermissionError:
                    print(f"[CLEANUP] WARNING: Could not delete {JSON_DB_PATH} (locked). Skipping cleanup.")
                except Exception as e:
                    print(f"[CLEANUP] WARNING: Error deleting {JSON_DB_PATH}: {e}")
            else:
                print("[CLEANUP] No existing temporary database found. Starting fresh.")
                
            # Ensure the directory itself still exists for future uploads
            if not os.path.exists(DB_FOLDER):
                os.makedirs(DB_FOLDER)
        except Exception as e:
            print(f"[CLEANUP] ❌ Error during startup cleanup: {str(e)}")

    def setupUi(self, MainWindow):
        # JAWWAD: Call the cleanup method immediately on startup
        self.cleanup_temp_db()

        self.database_manager = DatabaseManager()
        self.tabs_active = False
        self.active_tab_widgets = {}
        
        # JAWWAD: Cache to store construction widgets to persist data when navigating away
        self.cached_construction_widgets = {}

        # --- NEW: Flag to track if construction data is locked ---
        self.construction_locked = False
        # ---------------------------------------------------------
        
        # JAWWAD: Variable to store the active project UUID globally
        self.current_project_id = None

        self.widget_map = {
            KEY_STRUCTURE_WORKS_DATA: Foundation, KEY_FOUNDATION: Foundation,
            KEY_SUPERSTRUCTURE: SuperStructure, KEY_SUBSTRUCTURE: SubStructure,
            KEY_AUXILIARY: AuxiliaryWorks, KEY_FINANCIAL: FinancialData,
            KEY_CARBON_EMISSION: CarbonEmissionData, KEY_CARBON_EMISSION_COST: CarbonEmissionCostData,
            "Carbon Emission Machinery Data": CarbonMachineryWidget,
            "Carbon Emission Machinery Data": CarbonMachineryWidget,
            KEY_BRIDGE_TRAFFIC: BridgeAndTrafficData, KEY_MAINTAINANCE_REPAIR: MaintenanceRepairData,
            KEY_RECYCLABLE: RecyclableWidget,
            KEY_DEMOLITION_RECYCLE: DemolitionAndRecyclingData,
            KEY_TRANSPORTATION_DATA: TransportationMainWidget
        }

        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")

        font_id = QFontDatabase.addApplicationFont(":/font/AlataRegular.ttf")
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            QApplication.setFont(QFont(font_family, 10))

        MainWindow.setWindowTitle("3psLCCA")
        screen = QApplication.primaryScreen().geometry()
        MainWindow.setGeometry(screen.width()//8, screen.height()//8, screen.width()*3//4, screen.height()*3//4)

        MainWindow.setStyleSheet("""
            QMainWindow { border: none; }
            QMenuBar { background-color: #E8F5E9; border-bottom: 1px solid #d0d0d0; border-left: 1px solid #285A23; border-right: 1px solid #285A23; }
            QMenuBar::item { padding: 4px 10px; background-color: transparent; border-bottom: 2px solid #FAFAFA; margin: 2px; }
            QMenuBar::item:selected { border-bottom: 2px solid #806C6C; }
            QMenu { background-color: #f0f0f0; border: 1px solid #d0d0d0; }
            QMenu::item { padding: 4px 4px 4px 12px; text-align: left; color: #514E4E; }
            QMenu::item:selected { background-color: #e0e0e0; }
            QMenu::separator { height: 1px; background-color: #d0d0d0; margin: 4px 0px; }
            QMenu::icon { padding-left: 5px; width: 16px; height: 16px; }
            QMenu::indicator { width: 16px; height: 16px; }
            QMenu::right-arrow { margin-right: 5px; }
        """)

        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("border: none;")
        self.central_widget.setObjectName("central_widget")
        MainWindow.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.menubar = QMenuBar()
        self.menubar.setObjectName(u"menubar")
        main_layout.addWidget(self.menubar)

        self.menuFile = QMenu("&File", self.menubar)
        self.menuHome = QMenu("&Home", self.menubar)
        self.menuReport = QMenu("&Report", self.menubar)
        self.menuHelp = QMenu("&Help", self.menubar)
        self.menubar.addMenu(self.menuFile)
        self.menubar.addMenu(self.menuHome)
        self.menubar.addMenu(self.menuReport)
        self.menubar.addMenu(self.menuHelp)

        self.actionNew = QAction(QIcon(":/vectors/new.svg"), "New", MainWindow)
        self.actionOpen = QAction(QIcon(":/vectors/open.svg"), "Open", MainWindow)
        self.actionSave = QAction(QIcon(":/vectors/save.svg"), "Save", MainWindow)
        self.actionSaveAs = QAction(QIcon(":/vectors/save_as.svg"), "Save As...", MainWindow)
        self.actionCreateCopy = QAction(QIcon(":/vectors/create_copy.svg"), "Create a Copy", MainWindow)
        self.actionPrint = QAction(QIcon(":/vectors/print.svg"), "Print", MainWindow)
        self.actionRename = QAction(QIcon(":/vectors/rename.svg"), "Rename", MainWindow)
        self.actionExport = QAction(QIcon(":/vectors/export.svg"), "Export", MainWindow)
        self.actionVersionHistory = QAction(QIcon(":/vectors/version_history.svg"), "Version History", MainWindow)
        self.actionInfo = QAction(QIcon(":/vectors/info.svg"), "Info", MainWindow)

        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionSaveAs)
        self.menuFile.addAction(self.actionCreateCopy)
        self.menuFile.addAction(self.actionPrint)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionRename)
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addAction(self.actionVersionHistory)
        self.menuFile.addAction(self.actionInfo)

        self.actionDocumentation = QAction(QIcon(":/vectors/contact.svg"), "Contact us", MainWindow)
        self.actionFeedback = QAction(QIcon(":/vectors/feedback.svg"), "Feedback", MainWindow)
        self.actionVideoTutorial = QAction(QIcon(":/vectors/video_tutorial.svg"), "Video Tutorials", MainWindow)
        self.actionJoinCommunity = QAction(QIcon(":/vectors/join_community.svg"), "Join our Community", MainWindow)

        self.menuHelp.addAction(self.actionDocumentation)
        self.menuHelp.addAction(self.actionFeedback)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionVideoTutorial)
        self.menuHelp.addAction(self.actionJoinCommunity)

        self.main_content_area = QWidget()
        main_layout.addWidget(self.main_content_area, 1)
        self.main_content_area.setObjectName("main_content_area")
        self.main_content_area.setStyleSheet("""
            #main_content_area { background-color: #FAFAFA; border: 1px solid #285A23; border-top: 1px solid #BBBBBB; }
            QLabel { color: #9F8888; font-size: 14px; border: none; padding: 5px; }
            QPushButton { background-color: #EDEDED; border: 1px solid #d0d0d0; padding: 6px 16px; color: #514E4E; }
            QPushButton:hover { background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #BBBBBB, stop: 0.26 #E8E8E8, stop: 1 #EDEDED); border-color: #806C6C; }
            QPushButton:pressed { background-color: #d0d0d0; }
        """)

        content_layout = QVBoxLayout(self.main_content_area)
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.setSpacing(0)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(0)
        button_layout.setContentsMargins(5, 5, 5, 5)

        self.edit_button = QPushButton()
        self.edit_button.setObjectName(u"edit_button")
        self.edit_button.setIcon(QIcon(":/images/edit_button.png"))
        self.edit_button.setFixedSize(60, 30)
        self.edit_button.setIconSize(QSize(25, 25))
        self.edit_button.setStyleSheet("""
            QPushButton { border-radius: 5px; background-color: #EDEDED; border: 1px solid #BBBBBB; margin-right: 20px; margin-left: 10px; }
            QPushButton:hover { background-color: #FAFAFA; border: 1px solid #888888; }
        """)
        button_layout.addWidget(self.edit_button)

        self.file_button= QPushButton()
        self.file_button.setObjectName(u"file_button")
        self.file_button.setFixedSize(50, 30)
        self.file_button.setIcon(QIcon(":/images/file_button.png"))
        self.file_button.setIconSize(QSize(30, 30))
        self.file_button.setStyleSheet("""
            QPushButton { border-radius: 5px; background-color: #EDEDED; border: 1px solid #BBBBBB; margin-right: 20px; }
            QPushButton:hover { border: 1px solid #888888; background-color: #FAFAFA; }
        """)
        button_layout.addWidget(self.file_button)

        self.save_button = QPushButton()
        self.save_button.setObjectName(u"save_button")
        self.save_button.setFixedSize(40, 30)
        self.save_button.setIcon(QIcon(":/images/save_button.png"))
        self.save_button.setIconSize(QSize(25, 25))
        self.save_button.setStyleSheet("""
            QPushButton { border-radius: 5px; background-color: #EDEDED; border: 1px solid #BBBBBB; }
            QPushButton:hover { background-color: #FAFAFA; border: 1px solid #888888; }
            QPushButton::menu-indicator { image: url(:/images/arrow_down.png); width: 8px; height: 30px; subcontrol-position: right center; subcontrol-origin: padding; margin-right: 2px; margin-left: 2px; border-left: 1px solid #BBBBBB; }
        """)

        self.save_menu = QMenu(self.save_button)
        self.save_menu.setStyleSheet("""
            QMenu { background-color: #EDEDED; border: 1px solid #BBBBBB; padding: 2px; color: #9F8888; }
            QMenu::item { padding: 2px 2px; margin: 0px; border: none; min-height: 18px; font-size: 11px; }
            QMenu::item:selected { background-color: #FAFAFA; }
            QMenu::icon { width: 0px; }
        """)
        self.save_action = QAction("Save", self.save_menu)
        self.save_as_action = QAction("Save As", self.save_menu)
        self.save_menu.addAction(self.save_action)
        self.save_menu.addAction(self.save_as_action)
        self.save_button.setMenu(self.save_menu)
        button_layout.addWidget(self.save_button)

        self.upload_excel_button = QPushButton("Upload excel")
        self.upload_excel_button.setObjectName("upload_excel_button")
        self.upload_excel_button.clicked.connect(self.open_excel_dialog)
        self.upload_excel_button.setFixedSize(100, 30)
        self.upload_excel_button.setStyleSheet("""
            QPushButton { border-radius: 5px; background-color: #217346; border: 1px solid #1a5c38; color: white; font-weight: bold; font-size: 10px; padding-left: 5px; padding-right: 5px; margin-left: 20px; }
            QPushButton:hover { background-color: #2b945a; border: 1px solid #217346; }
            QPushButton:pressed { background-color: #1a5c38; }
        """)
        self.upload_excel_button.setToolTip("Upload Excel")
        button_layout.addWidget(self.upload_excel_button)

        button_layout.addStretch()
        self.windows = QLabel("Windows:")
        button_layout.addWidget(self.windows)

        self.tutorial_tab = QPushButton("Tutorials")
        self.project_details_tab = QPushButton("Project Details")
        self.results_tab = QPushButton("Results")
        self.compare = QPushButton("Compare")

        button_layout.addWidget(self.project_details_tab)
        button_layout.addWidget(self.results_tab)
        button_layout.addWidget(self.compare)
        button_layout.addWidget(self.tutorial_tab)
        button_layout.addStretch()

        content_layout.addLayout(button_layout)

        body_widget = QWidget()
        body_widget.setObjectName("body_widget")
        body_widget.setStyleSheet("#body_widget { border-top: 1px solid #d0d0d0; }")
        body_layout = QHBoxLayout(body_widget)
        body_layout.setSpacing(20)

        self.left_panel_placeholder = QWidget()
        self.left_panel_placeholder.setLayout(QVBoxLayout())
        self.right_panel_placeholder = QWidget()
        self.right_panel_placeholder.setLayout(QVBoxLayout())
        body_layout.addWidget(self.left_panel_placeholder, 1)
        body_layout.addWidget(self.right_panel_placeholder, 4)
        content_layout.addWidget(body_widget)

        self.current_left_widget = None
        self.current_right_widget = None

        # --- Updated Signal Connections to use Class Methods ---
        self.results_tab.clicked.connect(self.show_results_widget)
        self.compare.clicked.connect(self.show_comparison_widget)
        self.tutorial_tab.clicked.connect(self.show_tutorial_widget)
        self.project_details_tab.clicked.connect(lambda: self.show_project_detail_widgets())

    # --- NEW: Calculation & Locking Logic ---
    def calculate_and_lock_construction_data(self):
        """Calculates total costs, prints to terminal, shows alert, and locks data."""
        
        # JAWWAD : Use the new JSON calculation method instead of UI scraping
        grand_total = self.calculate_cost_from_json()
        
        # Fallback if calculation returns None (e.g., file error)
        if grand_total is None:
            grand_total = 0.0

        # Show the Alert Message
        msg = QMessageBox(self.central_widget)
        msg.setWindowTitle("Stage Locked")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Construction work data has been locked and saved.")
        msg.setInformativeText(f"Total Construction Cost calculated from Database:\nRs. {grand_total:,.2f}\n\nClick 'OK' to continue.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

        self.construction_locked = True

    # --- JAWWAD: New method to handle project ID signal from ProjectDetailsWidget ---
    def handle_project_creation(self, project_id):
        """Captures the project ID created by the details widget and stores it globally."""
        print(f"Main Window received Project ID: {project_id}")
        self.current_project_id = project_id

    # --- Refactored Navigation Logic (Fixes Recursion & Implements Locking) ---
    def show_project_detail_widgets(self, widget_name=None):
        """Handles widget switching and the 'Gatekeeper' logic for construction data."""
        print(f"[DEBUG] show_project_detail_widgets called with: {widget_name}")
        
        # 1. Normalize the widget name
        if widget_name == KEY_STRUCTURE_WORKS_DATA or widget_name == "Construction work data":
            widget_name = KEY_FOUNDATION

        # 2. Gatekeeper Logic: Check if leaving Construction -> Analysis
        construction_keys = [KEY_FOUNDATION, KEY_SUBSTRUCTURE, KEY_SUPERSTRUCTURE, KEY_AUXILIARY]
        
        is_moving_away = widget_name and (widget_name not in construction_keys)
        # Check if we are currently looking at construction tabs
        current_is_construction = self.tabs_active and any(k in self.active_tab_widgets for k in construction_keys)
        
        # Trigger lock if: Moving Away + Currently in Construction + Not yet locked
        if is_moving_away and current_is_construction and not self.construction_locked:
            self.calculate_and_lock_construction_data()

        # 3. Widget Switching Logic
        if widget_name and widget_name in self.widget_map:
            
            # Case A: The target is a Construction Tab (Foundation, Super, etc.)
            if widget_name in construction_keys:
                if self.tabs_active:
                    # Tabs are already open, just switch or add
                    if self.active_tab_widgets.get(widget_name) is not None:
                        index = self.active_tab_widgets[widget_name]
                        self.current_right_widget.activate_tab(index)
                    else:
                        self.add_new_tab_widget(widget_name)
                else:
                    # Initialize Tab View (First time opening construction)
                    self.setup_tabbed_view(widget_name)

            # Case B: The target is a Single Page (Financial, Carbon, etc.)
            # JAWWAD: Handle Navigation away from tabs
            else:
                # If we are currently in tab mode, we need to remove the tab widget
                self.remove_right_widget()
                self.tabs_active = False
                self.active_tab_widgets = {}

                # Create and show the new single widget (Financial, etc.)
                target_class = self.widget_map.get(widget_name)
                if target_class:
                    print(f"[DEBUG] Instantiating widget: {target_class}")
                    self.current_right_widget = target_class(database=self.database_manager, parent=self)
                    
                    # JAWWAD : Pass the project ID if available
                    if self.current_project_id and hasattr(self.current_right_widget, 'set_project_id'):
                        self.current_right_widget.set_project_id(self.current_project_id)

                    # Connect signals safely
                    if hasattr(self.current_right_widget, 'next'):
                        self.current_right_widget.next.connect(self.next_widget)
                    if hasattr(self.current_right_widget, 'back'):
                        self.current_right_widget.back.connect(self.prev_widget)
                        
                    self.right_panel_placeholder.layout().addWidget(self.current_right_widget)
                    print(f"[DEBUG] Widget added to layout.")

        else:
            # -- Default / Project Details Landing Page --
            self.remove_right_widget()
            self.tabs_active = False
            self.active_tab_widgets = {}
            self.current_right_widget = ProjectDetailsWidget()
            
            # JAWWAD : CONNECT SIGNAL HERE - This fixes the "Project ID is None" error
            self.current_right_widget.projectCreated.connect(self.handle_project_creation)
            
            self.right_panel_placeholder.layout().addWidget(self.current_right_widget)
            self.current_right_widget.closed.connect(self.remove_right_widget)

            # Prevent recursion: Connect signals cleanly
            if hasattr(self.current_right_widget, 'param_buttons'):
                for btn in self.current_right_widget.param_buttons:
                    try: btn.clicked.disconnect() 
                    except: pass
                    btn.clicked.connect(lambda checked, b=btn: self.show_project_detail_widgets(b.text().strip()))

    def setup_tabbed_view(self, start_widget_name):
        """Helper to initialize the tabbed construction view"""
        self.remove_right_widget()
        self.active_tab_widgets = {}
        self.tabs_active = True
        self.current_right_widget = CustomTabWidget(parent=self)
        self.right_panel_placeholder.layout().addWidget(self.current_right_widget)

        self.remove_left_widget()
        self.current_left_widget = ProjectDetailsLeft(self.widget_map, parent=self)
        self.left_panel_placeholder.layout().addWidget(self.current_left_widget)
        self.current_left_widget.closed.connect(self.remove_left_widget)
        self.current_left_widget.handle_button_selection(button_name=start_widget_name)

        self.add_new_tab_widget(start_widget_name)

    def add_new_tab_widget(self, widget_name):
        """Helper to create or retrieve a widget tab."""
        # JAWWAD: CACHING LOGIC
        # 1. Check if the widget already exists in our cache
        if widget_name in self.cached_construction_widgets:
            print(f"[CACHE] Retrieving existing widget for: {widget_name}")
            widget = self.cached_construction_widgets[widget_name]
        else:
            # 2. If not, create a new one and cache it
            print(f"[CACHE] Creating new widget for: {widget_name}")
            widget = self.widget_map[widget_name](database=self.database_manager, parent=self)
            
            # JAWWAD : Inject Project ID into new widget
            if self.current_project_id and hasattr(widget, 'set_project_id'):
                widget.set_project_id(self.current_project_id)
                
            widget.next.connect(self.next_widget)
            widget.back.connect(self.prev_widget)
            self.cached_construction_widgets[widget_name] = widget
            
        # 3. Add the widget (either retrieved or new) to the tab view
        index = self.current_right_widget.add_new_tab(widget, widget_name)
        self.active_tab_widgets[widget_name] = index

    # --- Standard Widget Toggle Functions ---
    def show_tutorial_widget(self):
        if self.current_left_widget:
            self.left_panel_placeholder.layout().removeWidget(self.current_left_widget)
            self.current_left_widget.setParent(None)
        self.current_left_widget = TutorialWidget()
        self.left_panel_placeholder.layout().addWidget(self.current_left_widget)
        self.current_left_widget.closed.connect(self.remove_left_widget)

    def show_results_widget(self):
        if self.current_right_widget:
            self.right_panel_placeholder.layout().removeWidget(self.current_right_widget)
            self.current_right_widget.setParent(None)
        self.current_right_widget = ResultsWidget()
        self.right_panel_placeholder.layout().addWidget(self.current_right_widget)
        self.current_right_widget.closed.connect(self.remove_right_widget)

    def show_comparison_widget(self):
        if self.current_right_widget:
            self.right_panel_placeholder.layout().removeWidget(self.current_right_widget)
            self.current_right_widget.setParent(None)
        self.current_right_widget = ComparisonWidget()
        self.right_panel_placeholder.layout().addWidget(self.current_right_widget)
        self.current_right_widget.closed.connect(self.remove_right_widget)

    def remove_right_widget(self):
        # JAWWAD: Before destroying the current widget, if it's the Tab container,
        # rescue the cached children so they persist!
        if self.tabs_active and self.cached_construction_widgets:
             print("[CACHE] Detaching widgets to prevent deletion...")
             for w in self.cached_construction_widgets.values():
                 try: 
                     w.setParent(None)
                 except: 
                     pass

        if self.current_right_widget:
            self.right_panel_placeholder.layout().removeWidget(self.current_right_widget)
            self.current_right_widget.setParent(None)
            self.current_right_widget = None

    def remove_left_widget(self):
        if self.current_left_widget:
            self.left_panel_placeholder.layout().removeWidget(self.current_left_widget)
            self.current_left_widget.setParent(None)
            self.current_left_widget = None

    def next_widget(self, widget_name):
        keys = list(self.widget_map.keys())
        current_idx = keys.index(widget_name)
        if current_idx + 1 < len(keys):
            next_name = keys[current_idx + 1]
            if self.current_left_widget and hasattr(self.current_left_widget, 'all_param_buttons'):
                if next_name in self.current_left_widget.all_param_buttons:
                    self.current_left_widget.all_param_buttons[next_name].click()
            self.show_project_detail_widgets(next_name)

    def prev_widget(self, widget_name):
        keys = list(self.widget_map.keys())
        current_idx = keys.index(widget_name)
        if current_idx - 1 >= 0:
            prev_name = keys[current_idx - 1]
            if self.current_left_widget and hasattr(self.current_left_widget, 'all_param_buttons'):
                if prev_name in self.current_left_widget.all_param_buttons:
                    self.current_left_widget.all_param_buttons[prev_name].click()
            self.show_project_detail_widgets(prev_name)
