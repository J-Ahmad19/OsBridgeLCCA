from PySide6.QtWidgets import (QApplication, QMainWindow, QDialog, QFormLayout, QCheckBox, QGroupBox,
                               QHBoxLayout, QPushButton, QLineEdit, QComboBox, QGridLayout, QWidget, 
                               QLabel, QVBoxLayout, QScrollArea, QSpacerItem, QSizePolicy, QFrame, 
                               QMessageBox, QCompleter, QListWidget, QAbstractItemView, QToolTip, QInputDialog)
from PySide6.QtCore import (QCoreApplication, Qt, QSize, Signal, QStringListModel, QPoint, QEvent, 
                            QObject, QTimer, QRect, Slot) 
from PySide6.QtGui import QIcon, QDoubleValidator, QIntValidator, QCursor
import sys

# --- CONSTANTS ---
DROPDOWN_UNITS = ["cum", "MT", "Rmt", "RMT", "m2", "number"]

# --- IMPORTS ---
from osbridgelcca.desktop_app.widgets.utils.data import *

try:
    # UPDATED IMPORT: Import manager instance for Search
    from osbridgelcca.desktop_app.widgets.utils.sor_backend import sor_manager
except ImportError:
    print("Warning: sor_backend.py not found. Search features will be limited.")
    sor_manager = None

# JAWWAD: Import ProjectDataManager for real-time saving functionality
try:
    from osbridgelcca.desktop_app.core.data_manager import ProjectDataManager
except ImportError:
    print("Warning: ProjectDataManager not found. Real-time saving disabled.")
    ProjectDataManager = None

# JAWWAD: Import MaterialDatabaseManager for User Library features
try:
    from osbridgelcca.desktop_app.core.material_db_manager import MaterialDatabaseManager
except ImportError:
    print("Warning: MaterialDatabaseManager not found. DB saving features will be limited.")
    MaterialDatabaseManager = None

# --- NEW: Event Filter for Locking Logic (Fixed Flickering) ---
class LockEventFilter(QObject):
    def __init__(self, main_widget):
        # JAWWAD: Pass parent to avoid Garbage Collection issues
        super().__init__(main_widget)
        self.main_widget = main_widget

    def eventFilter(self, obj, event):
        # Safety check for main_widget existence
        if not hasattr(self, 'main_widget') or self.main_widget is None:
            return super().eventFilter(obj, event)

        # Only intercept interaction events if the widget is locked
        if getattr(self.main_widget, 'is_locked', False):
            # Check for Mouse Clicks, Key Presses, or Wheel scrolls
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonDblClick, 
                                QEvent.KeyPress, QEvent.KeyRelease, QEvent.Wheel]:
                
                # Call the debounce method in main_widget to avoid flickering
                self.main_widget.trigger_lock_warning()
                
                # Return True to consume/block the event (prevent editing)
                return True
        
        return super().eventFilter(obj, event)

# --- UPDATED: MATERIAL INPUT POPUP ---
class MaterialInputPopup(QDialog):
    # JAWWAD: Signal to send data without closing the popup
    data_submitted = Signal(dict)

    def __init__(self, material_data_source, component_name, current_region, current_sor, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Material Details")
        
        # --- WINDOW SIZE OPTIMIZATION ---
        self.setMinimumWidth(600)
        self.resize(650, 700) # Default size
        self.setMaximumHeight(900) 
        
        self.material_data_source = material_data_source
        self.component_name = component_name
        # Store context
        self.current_region = current_region
        self.current_sor = current_sor
        
        if MaterialDatabaseManager:
            self.db_manager = MaterialDatabaseManager()
        else:
            self.db_manager = None

        self.result_data = None
        
        self.init_ui()
        
        # JAWWAD: Install event filter on the dialog itself to detect clicks outside the suggestion box
        self.installEventFilter(self)
        
    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { font-size: 12px; color: #333; font-family: 'Segoe UI', sans-serif; }
            QLineEdit, QComboBox {
                border: 1px solid #cccccc; border-radius: 8px; padding: 5px 8px;
                background-color: #fcfcfc; font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #007BFF; background-color: #ffffff; }
            QListWidget { border: 1px solid #cccccc; border-radius: 8px; background-color: #ffffff; outline: none; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background-color: #e6f3ff; color: #000; }
            QListWidget::item:hover { background-color: #f5f5f5; }
            QPushButton { border-radius: 6px; padding: 8px 16px; font-weight: bold; }
            QScrollArea { border: none; background-color: transparent; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # --- DYNAMIC HEADER ---
        header_text_val = f"Region: {self.current_region}, Selected SOR: {self.current_sor}\nAdding in Super-Structure > {self.component_name} Component"
        
        header_text = QLabel(header_text_val)
        header_text.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px; margin-bottom: 5px;")
        layout.addWidget(header_text)
        
        # 2. SCROLL AREA (Contains the form)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Container Widget inside Scroll Area
        self.scroll_content_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content_widget)
        self.scroll_layout.setContentsMargins(5, 0, 10, 0) # Right margin for scrollbar
        self.scroll_layout.setSpacing(10)

        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(10)
        self.form_layout.setLabelAlignment(Qt.AlignLeft)
        
        # --- Form Fields ---
        self.search_source_combo = QComboBox()
        self.search_source_combo.addItems(["All Sources", "Standard Database (SOR)", "User Personal Libraries"])
        self.search_source_combo.setToolTip("Choose which database to search in")
        self.search_source_combo.currentTextChanged.connect(self.on_search_source_changed)
        self.form_layout.addRow("Search Source:", self.search_source_combo)

        self.specific_lib_combo = QComboBox()
        self.specific_lib_combo.setVisible(False)
        self.specific_lib_combo.currentTextChanged.connect(lambda: self.update_search_results(self.material_input.text()))
        self.form_layout.addRow("Select Library:", self.specific_lib_combo)

        self.material_input = QLineEdit()
        self.material_input.setPlaceholderText(f"Search {self.component_name}...")
        self.material_input.textEdited.connect(self.update_search_results)
        self.material_input.textChanged.connect(self.on_material_text_changed)
        self.form_layout.addRow("Material Name", self.material_input)
        
        # Suggestion List (Floating - added to self, not scroll area, to float correctly)
        self.suggestion_list = QListWidget(self)
        self.suggestion_list.setWindowFlags(Qt.SubWindow)
        self.suggestion_list.setFocusPolicy(Qt.NoFocus)
        self.suggestion_list.setFixedHeight(150) 
        self.suggestion_list.setUniformItemSizes(True)
        self.suggestion_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.suggestion_list.hide() 
        self.suggestion_list.itemClicked.connect(self.on_suggestion_clicked)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; margin-left: 2px;")
        self.form_layout.addRow("", self.status_label)

        self.quantity_edit = QLineEdit()
        self.quantity_edit.setValidator(QDoubleValidator(0.001, 9999999.99, 3))
        self.form_layout.addRow("Quantity (Unit_A) *", self.quantity_edit)
        
        self.unit_combo = QComboBox()
        self.unit_combo.setEditable(False)
        self.unit_combo.setMinimumWidth(120)
        self.unit_combo.addItems(DROPDOWN_UNITS)
        self.form_layout.addRow("Unit_A *", self.unit_combo)
        
        self.rate_edit = QLineEdit()
        self.rate_edit.setValidator(QDoubleValidator(0.0, 9999999.99, 2))
        self.form_layout.addRow("Rupees/Unit_A *", self.rate_edit)
        
        self.rate_source_edit = QLineEdit()
        self.form_layout.addRow("Rate source *", self.rate_source_edit)
        
        self.carbon_edit = QLineEdit()
        self.carbon_edit.setPlaceholderText("Optional (or NA)")
        self.form_layout.addRow("Carbon emission (kgCO₂e/Unit_B)", self.carbon_edit)
        
        self.carbon_unit_edit = QLineEdit()
        self.form_layout.addRow("Carbon emission units", self.carbon_unit_edit)
        
        self.conv_factor_edit = QLineEdit()
        self.conv_factor_edit.setValidator(QDoubleValidator(0.001, 9999999.99, 4))
        self.form_layout.addRow("Conversion factor (Unit_A → Unit_B) *", self.conv_factor_edit)
        
        self.carbon_source_edit = QLineEdit()
        self.form_layout.addRow("Carbon factor source", self.carbon_source_edit)
        
        self.scroll_layout.addLayout(self.form_layout)
        
        # --- RECYCLABLE SECTION ---
        self.recyclable_check = QCheckBox("Recyclable")
        # JAWWAD: Connect toggled signal to show/hide extra fields
        self.recyclable_check.toggled.connect(self.on_recyclable_toggled)
        self.scroll_layout.addWidget(self.recyclable_check)

        # JAWWAD: Container for extra fields when Recyclable is checked
        self.recyclable_fields_widget = QWidget()
        self.recyclable_fields_layout = QFormLayout(self.recyclable_fields_widget)
        self.recyclable_fields_layout.setContentsMargins(20, 0, 0, 0)
        self.recyclable_fields_layout.setSpacing(10)
        self.recyclable_fields_layout.setLabelAlignment(Qt.AlignLeft)

        # JAWWAD: 1. Scrap Rate Input
        self.scrap_rate_edit = QLineEdit()
        self.scrap_rate_edit.setValidator(QDoubleValidator(0.0, 9999999.99, 2))
        self.scrap_rate_edit.setPlaceholderText("0.00")
        self.recyclable_fields_layout.addRow("Scrap Rate *", self.scrap_rate_edit)

        # JAWWAD: 2. Percentage of Quantities Input
        self.percentage_qty_edit = QLineEdit()
        self.percentage_qty_edit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.percentage_qty_edit.setPlaceholderText("0-100%")
        self.recyclable_fields_layout.addRow("Percentage of Quantities (%) *", self.percentage_qty_edit)

        # JAWWAD: Initially hidden
        self.recyclable_fields_widget.setVisible(False)
        self.scroll_layout.addWidget(self.recyclable_fields_widget)
        # --- END RECYCLABLE SECTION ---
        
        self.edit_check = QCheckBox("Edit")
        self.edit_check.toggled.connect(self.on_edit_toggled)
        self.edit_check.setVisible(False) 
        self.scroll_layout.addWidget(self.edit_check)
        
        self.db_selection_widget = QWidget()
        self.db_selection_layout = QHBoxLayout(self.db_selection_widget)
        self.db_selection_layout.setContentsMargins(0, 5, 0, 5)
        self.db_selection_layout.setSpacing(10)

        self.save_db_label = QLabel("Save to Database:")
        self.db_selection_layout.addWidget(self.save_db_label)

        self.save_db_combo = QComboBox()
        self.save_db_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.populate_db_combo() 
        self.db_selection_layout.addWidget(self.save_db_combo)

        self.new_db_btn = QPushButton("+ New DB")
        self.new_db_btn.setFixedWidth(80)
        self.new_db_btn.setStyleSheet("background-color: #28a745; color: white; padding: 5px;")
        self.new_db_btn.setCursor(Qt.PointingHandCursor)
        self.new_db_btn.clicked.connect(self.create_new_database)
        self.db_selection_layout.addWidget(self.new_db_btn)

        self.db_selection_widget.setVisible(False) 
        self.scroll_layout.addWidget(self.db_selection_widget)
        
        # Add Spacer at bottom of scroll content to push things up
        self.scroll_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Set Widget to Scroll Area
        self.scroll_area.setWidget(self.scroll_content_widget)
        layout.addWidget(self.scroll_area)
        
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #dc3545; font-weight: 600; font-size: 11px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.add_btn = QPushButton("+ Add Material")
        self.add_btn.setStyleSheet("background-color: #007BFF; color: white; border: none;")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.validate_and_accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #f0f0f0; color: #333; border: 1px solid #ccc;")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setStyleSheet("background-color: #DC3545; color: white; border: none;")
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.exit_btn)
        
        layout.addLayout(btn_layout)
        
        self.on_material_text_changed(self.material_input.text())

    # JAWWAD: Event Filter to handle clicking outside the suggestion box
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self.suggestion_list.isVisible():
                list_rect = self.suggestion_list.rect()
                list_global_pos = self.suggestion_list.mapToGlobal(QPoint(0, 0))
                list_global_rect = QRect(list_global_pos, list_rect.size())

                input_rect = self.material_input.rect()
                input_global_pos = self.material_input.mapToGlobal(QPoint(0, 0))
                input_global_rect = QRect(input_global_pos, input_rect.size())
                
                mouse_pos = event.globalPosition().toPoint()

                if not list_global_rect.contains(mouse_pos) and not input_global_rect.contains(mouse_pos):
                    self.suggestion_list.hide()
        
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.suggestion_list.isVisible():
            self.adjust_list_position()

    def adjust_list_position(self):
        if not self.material_input: return
        pos = self.material_input.mapTo(self, QPoint(0, self.material_input.height()))
        available_width = self.width() - pos.x() - 25 
        self.suggestion_list.move(pos)
        self.suggestion_list.setFixedWidth(available_width)
        self.suggestion_list.raise_()

    # JAWWAD: New method to handle visibility toggling of recyclable fields
    def on_recyclable_toggled(self, checked):
        """Shows or hides the extra recyclable fields based on checkbox state."""
        self.recyclable_fields_widget.setVisible(checked)
        if not checked:
            self.scrap_rate_edit.clear()
            self.percentage_qty_edit.clear()

    # --- Handler for Source Change ---
    def on_search_source_changed(self, text):
        if text == "User Personal Libraries":
            self.populate_specific_libs()
            self.specific_lib_combo.setVisible(True)
        else:
            self.specific_lib_combo.setVisible(False)
        
        # Trigger update
        self.update_search_results(self.material_input.text())

    def populate_specific_libs(self):
        self.specific_lib_combo.blockSignals(True)
        self.specific_lib_combo.clear()
        self.specific_lib_combo.addItem("All User Libraries")
        if self.db_manager:
            try:
                dbs = self.db_manager.get_available_databases()
                for db in dbs:
                    self.specific_lib_combo.addItem(db['name'])
            except Exception as e:
                print(f"Error populating specific libs: {e}")
        self.specific_lib_combo.blockSignals(False)

    def update_search_results(self, text):
        if not text.strip():
            self.suggestion_list.hide()
            return

        all_items = []
        source_selection = self.search_source_combo.currentText()

        # 1. Search Standard SOR (Backend)
        if source_selection in ["All Sources", "Standard Database (SOR)"]:
            if sor_manager and sor_manager.searcher:
                backend_results = sor_manager.searcher.performSearch([self.component_name.lower()], text)
                all_items.extend([item['name'] for item in backend_results])

        # 2. Search User Databases
        if source_selection in ["All Sources", "User Personal Libraries"]:
            if self.db_manager:
                # Get ALL matching items first
                user_results = self.db_manager.search_all_databases(text)
                
                # Apply Sub-Library Filter if applicable
                if source_selection == "User Personal Libraries":
                    specific_lib = self.specific_lib_combo.currentText()
                    if specific_lib and specific_lib != "All User Libraries":
                        # Filter the results based on 'db_name'
                        user_results = [r for r in user_results if r.get('db_name') == specific_lib]

                all_items.extend([item['name'] for item in user_results])

        unique_items = sorted(list(set(all_items)))
        
        self.suggestion_list.clear()
        
        if unique_items:
            self.suggestion_list.addItems(unique_items)
            self.adjust_list_position() 
            self.suggestion_list.show()
        else:
            self.suggestion_list.hide()

    def populate_db_combo(self):
        self.save_db_combo.clear()
        self.save_db_combo.addItem("Do not save", None)
        if self.db_manager:
            try:
                dbs = self.db_manager.get_available_databases()
                for db in dbs:
                    # Uses db['name'] for both text and data for Master DB tagging
                    self.save_db_combo.addItem(db['name'], db['name'])
            except Exception as e:
                print(f"Error loading databases: {e}")

    def create_new_database(self):
        if not self.db_manager:
            QMessageBox.critical(self, "Error", "Database Manager not loaded.")
            return
        name, ok = QInputDialog.getText(self, "New Database", "Enter Database Name:")
        if ok and name.strip():
            try:
                new_path = self.db_manager.create_new_database(name.strip())
                self.populate_db_combo()
                
                # Search by text (Name) to select the new library
                index = self.save_db_combo.findText(name.strip())
                if index >= 0:
                    self.save_db_combo.setCurrentIndex(index)
                
                # Refresh filter list too if visible
                if self.specific_lib_combo.isVisible():
                    self.populate_specific_libs()
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")

    def on_suggestion_clicked(self, item):
        self.material_input.setText(item.text())
        self.suggestion_list.hide()

    def on_material_text_changed(self, text):
        self.error_label.setText("") 
        found_data = None
        source_type = None 
        
        source_selection = self.search_source_combo.currentText()
        check_standard = source_selection in ["All Sources", "Standard Database (SOR)"]
        check_user = source_selection in ["All Sources", "User Personal Libraries"]

        if check_standard and sor_manager and sor_manager.searcher:
            found_data = sor_manager.searcher.getDetailByName(text)
            if found_data: source_type = "standard"

        if not found_data and check_user and self.db_manager:
            found_data = self.db_manager.get_material_details(text)
            if found_data: source_type = "user"
        
        if found_data:
            unit = found_data.get("unit", "")
            if not unit and source_type == "user": unit = found_data.get("unit", "")

            index = self.unit_combo.findText(unit)
            if index != -1:
                self.unit_combo.setCurrentIndex(index)
            else:
                self.unit_combo.addItem(unit)
                self.unit_combo.setCurrentText(unit)
            
            self.rate_edit.setText(str(found_data.get("rate", "")))
            self.rate_source_edit.setText(found_data.get("rate_src") or found_data.get("rate_source", ""))
            self.carbon_edit.setText(str(found_data.get("carbon_emission", "")))
            self.carbon_unit_edit.setText(found_data.get("carbon_emission_units") or found_data.get("carbon_unit", ""))
            self.conv_factor_edit.setText(str(found_data.get("conversion_factor", "")))
            self.carbon_source_edit.setText(found_data.get("carbon_emission_src") or found_data.get("carbon_source", ""))
            
            is_recyclable = False
            if source_type == "standard":
                self.status_label.setText(f"✅ Found standard material: {found_data.get('name')}")
                self.status_label.setStyleSheet("color: green; font-size: 11px; margin-left: 2px;")
                is_recyclable = str(found_data.get("recycleable", "")).lower() == "recyclable"
            
            elif source_type == "user":
                db_name = found_data.get("origin_db_name", "User DB")
                self.status_label.setText(f"📂 Found in User Database: {db_name}")
                self.status_label.setStyleSheet("color: #007BFF; font-weight: bold; font-size: 11px; margin-left: 2px;")
                is_recyclable = False 

            self.recyclable_check.setChecked(is_recyclable)
            self.edit_check.setVisible(True)
            self.edit_check.setChecked(False)
            self.set_fields_readonly(True)
            self.db_selection_widget.setVisible(False)
        else:
            self.status_label.setText("") 
            self.edit_check.setVisible(False)
            self.db_selection_widget.setVisible(True)
            self.set_fields_readonly(False)

    def on_edit_toggled(self, checked):
        if checked:
            self.set_fields_readonly(False)
            self.rate_source_edit.clear()
            self.carbon_source_edit.clear()
            self.db_selection_widget.setVisible(True)
            self.save_db_combo.setCurrentIndex(0) 
            self.edit_check.setVisible(False) 
        else:
            self.set_fields_readonly(True)
            self.db_selection_widget.setVisible(False)

    def set_fields_readonly(self, readonly):
        self.unit_combo.setEnabled(not readonly)
        self.rate_edit.setReadOnly(readonly)
        self.rate_source_edit.setReadOnly(readonly)
        self.carbon_edit.setReadOnly(readonly)
        self.carbon_unit_edit.setReadOnly(readonly)
        self.conv_factor_edit.setReadOnly(readonly)
        self.carbon_source_edit.setReadOnly(readonly)
        self.recyclable_check.setEnabled(not readonly)
        
        # JAWWAD: New recyclable fields logic
        self.scrap_rate_edit.setReadOnly(readonly)
        self.percentage_qty_edit.setReadOnly(readonly)
        
        base_style = "border: 1px solid #ccc; border-radius: 8px; padding: 6px 10px;"
        style = base_style + ("background-color: #E0E0E0;" if readonly else "background-color: #fcfcfc;")
            
        for widget in [self.rate_edit, self.rate_source_edit, self.carbon_edit, 
                       self.carbon_unit_edit, self.conv_factor_edit, self.carbon_source_edit,
                       self.scrap_rate_edit, self.percentage_qty_edit]:
            widget.setStyleSheet(style)
        self.unit_combo.setStyleSheet(style)

    def validate_and_accept(self):
        self.error_label.setText("")
        name = self.material_input.text().strip()
        if not name:
            self.error_label.setText("Error: Material name is required.")
            return

        errors = []
        try:
            qty = float(self.quantity_edit.text())
            if qty <= 0: errors.append("Quantity must be > 0.")
        except ValueError:
            errors.append("Quantity must be a valid number.")

        if not self.unit_combo.currentText().strip():
            errors.append("Unit cannot be empty.")

        try:
            price = float(self.rate_edit.text())
            if price < 0: errors.append("Price must be a valid number.")
        except ValueError:
            errors.append("Price must be a valid number.")

        if not self.rate_source_edit.text().strip():
            errors.append("Rate Source is required.")
        
        conv_text = self.conv_factor_edit.text().strip()
        if conv_text.lower() not in ["na", "not_available", "not available"]:
            try:
                conv = float(conv_text)
                if conv <= 0: errors.append("Conversion Factor must be > 0.")
            except ValueError:
                errors.append("Conversion Factor must be a valid number.")

        c_text = self.carbon_edit.text().strip()
        if c_text and c_text.lower() not in ["na", "not_available", "not available"]:
            try:
                c_val = float(c_text)
                if c_val < 0: errors.append("Carbon Emission must be ≥ 0.")
            except ValueError:
                errors.append("Carbon Emission must be a number or 'NA'.")

        # JAWWAD: Validate Recyclable Fields
        if self.recyclable_check.isChecked():
            scrap_text = self.scrap_rate_edit.text().strip()
            if not scrap_text:
                errors.append("Scrap Rate is required when Recyclable is checked.")
            else:
                try:
                    s_val = float(scrap_text)
                    if s_val < 0: errors.append("Scrap Rate must be ≥ 0.")
                except ValueError:
                    errors.append("Scrap Rate must be a valid number.")

            perc_text = self.percentage_qty_edit.text().strip()
            if not perc_text:
                errors.append("Percentage of Quantities is required when Recyclable is checked.")
            else:
                try:
                    p_val = float(perc_text)
                    if p_val < 0 or p_val > 100: errors.append("Percentage must be between 0 and 100.")
                except ValueError:
                    errors.append("Percentage must be a valid number.")

        # This will now contain the NAME of the database (e.g., "MyProjectLib")
        selected_db_path = self.save_db_combo.currentData()
        
        if errors:
            self.error_label.setText("\n".join(errors))
            return

        is_custom = True
        if sor_manager and sor_manager.searcher and sor_manager.searcher.getDetailByName(name):
            is_custom = False
        
        self.result_data = {
            KEY_TYPE: name,
            KEY_GRADE: "Standard",
            KEY_QUANTITY: self.quantity_edit.text(),
            KEY_UNIT_M3: self.unit_combo.currentText(),
            KEY_RATE: self.rate_edit.text(),
            KEY_RATE_DATA_SOURCE: self.rate_source_edit.text(),
            "carbon_emission": self.carbon_edit.text(),
            "carbon_unit": self.carbon_unit_edit.text(),
            "conversion_factor": self.conv_factor_edit.text(),
            "carbon_source": self.carbon_source_edit.text(),
            "recyclable": self.recyclable_check.isChecked(),
            # JAWWAD: Add new keys to result data
            "scrap_rate": self.scrap_rate_edit.text() if self.recyclable_check.isChecked() else "",
            "recycle_percentage": self.percentage_qty_edit.text() if self.recyclable_check.isChecked() else "",
            "target_db": selected_db_path,
            "save_to_db": True if selected_db_path else False,
            "is_custom": is_custom
        }
        
        # JAWWAD: Emit signal with data instead of closing
        self.data_submitted.emit(self.result_data)
        
        self.clear_inputs()
        self.status_label.setText("✅ Material Added Successfully! You can add another.")
        self.status_label.setStyleSheet("color: blue; font-weight: bold; font-size: 11px; margin-left: 2px;")

    def clear_inputs(self):
        """Resets the input fields to allow adding another material quickly."""
        self.material_input.clear()
        self.quantity_edit.clear()
        self.rate_edit.clear()
        self.rate_source_edit.clear()
        self.carbon_edit.clear()
        self.carbon_unit_edit.clear()
        self.conv_factor_edit.clear()
        self.carbon_source_edit.clear()
        # JAWWAD: Clear recyclability check which also hides and clears extra fields
        self.recyclable_check.setChecked(False) 
        self.save_db_combo.setCurrentIndex(0)
        self.db_selection_widget.setVisible(False)
        self.edit_check.setChecked(False)
        self.edit_check.setVisible(False)
        self.unit_combo.setCurrentIndex(0)
        self.material_input.setFocus() 

    def get_data(self):
        return self.result_data

# --- COMPONENT WIDGET ---
class ComponentWidget(QWidget):
    def __init__(self, parent_widget, event_filter):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.lock_event_filter = event_filter 
        self._initializing = True
        self.is_locked = False 
        self.data = construction_materials.get(KEY_SUPERSTRUCTURE) # Using SuperStructure key
        self.material_rows = []
        self.current_material_row_idx = 1

        self.init_ui()
        self._initializing = False

    def init_ui(self):
        self.component_first_scroll_content_layout = QVBoxLayout(self)
        self.component_first_scroll_content_layout.setContentsMargins(10, 10, 10, 10)
        self.component_first_scroll_content_layout.setSpacing(10)

        component_header_layout = QHBoxLayout()
        component_label = QLabel("Component:")
        component_label.setContentsMargins(0, 5, 0, 5)
        component_header_layout.addWidget(component_label)

        self.component_combobox = QComboBox()
        self.component_combobox.currentTextChanged.connect(self.update_comp_material)
        self.component_combobox.installEventFilter(self.lock_event_filter) 
        
        comp_items = list(self.data.keys())
        self.component_combobox.addItems(comp_items)

        self.component_combobox.currentTextChanged.connect(self._on_value_changed)
        self.component_combobox.setContentsMargins(0, 5, 0, 5)
        component_header_layout.addWidget(self.component_combobox)

        self.remove_component_button = QPushButton("x")
        self.remove_component_button.setFixedSize(24, 24)
        self.remove_component_button.installEventFilter(self.lock_event_filter) 
        self.remove_component_button.setStyleSheet("""
            QPushButton {
                background-color: #FFCCCC;
                border: 1px solid #FF9999;
                border-radius: 12px;
                font-weight: bold;
                line-height:12px;
                padding: 0px;
                color: #CC0000;
            }
            QPushButton:hover { background-color: #FF9999; color: white; }
            QPushButton:pressed { background-color: #FF6666; }
            QPushButton[locked_state="true"] {
                background-color: #F8F8F8;
                border: 1px solid #E0E0E0;
                color: #CCCCCC;
            }
        """)
        component_header_layout.addWidget(self.remove_component_button)
        component_header_layout.addStretch(1)

        self.component_first_scroll_content_layout.addLayout(component_header_layout)

        self.material_grid_layout = QGridLayout()
        self.material_grid_layout.setHorizontalSpacing(10)
        self.material_grid_layout.setVerticalSpacing(5)

        self.material_grid_layout.setColumnStretch(0, 2) 
        self.material_grid_layout.setColumnStretch(1, 2) 
        self.material_grid_layout.setColumnStretch(2, 3) 
        self.material_grid_layout.setColumnStretch(3, 3) 
        self.material_grid_layout.setColumnStretch(4, 3) 
        self.material_grid_layout.setColumnStretch(5, 3) 
        self.material_grid_layout.setColumnStretch(6, 0) 

        # No Grade in headers
        headers = ["Type of Material", "Quantity", "Unit", "Rate", "Rate Data Source"]
        for col, header_text in enumerate(headers):
            label = QLabel(header_text)
            label.setAlignment(Qt.AlignCenter)
            label.setObjectName("MaterialGridLabel")
            
            if col == 0:
                self.material_grid_layout.addWidget(label, 0, 0, 1, 2)
            else:
                grid_col = col + 1 
                self.material_grid_layout.addWidget(label, 0, grid_col)

        self.component_first_scroll_content_layout.addLayout(self.material_grid_layout)

        self.update_comp_material(self.component_combobox.currentText())

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.add_material_button = QPushButton("+ Add Material")
        self.add_material_button.setObjectName("add_material_button")
        self.add_material_button.installEventFilter(self.lock_event_filter) 
        self.add_material_button.clicked.connect(self.open_add_material_popup)
        buttons_layout.addWidget(self.add_material_button)
        
        buttons_layout.addStretch()
        
        self.component_first_scroll_content_layout.addLayout(buttons_layout)
        
    def set_locked(self, locked):
        self.is_locked = locked
        
        def set_widget_locked(widget):
            widget.setProperty("locked_state", str(locked).lower())
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        set_widget_locked(self.component_combobox)
        set_widget_locked(self.add_material_button)
        set_widget_locked(self.remove_component_button)
        
        for row in self.material_rows:
            set_widget_locked(row[KEY_TYPE])
            set_widget_locked(row[KEY_QUANTITY])
            set_widget_locked(row[KEY_UNIT_M3])
            set_widget_locked(row[KEY_RATE])
            set_widget_locked(row[KEY_RATE_DATA_SOURCE])
            set_widget_locked(row['remove_button'])
   
    def collect_data(self):
        rows_data = []
        for row in self.material_rows:
            component = self.component_combobox.currentText()
            
            widget_type = row[KEY_TYPE]
            if isinstance(widget_type, QComboBox):
                material_type = widget_type.currentText()
            else:
                material_type = widget_type.text()

            material_grade = "Standard"

            widget_unit = row[KEY_UNIT_M3]
            if isinstance(widget_unit, QComboBox):
                unit_m3 = widget_unit.currentText()
            else:
                unit_m3 = widget_unit.text()

            quantity = row[KEY_QUANTITY].text()
            rate = row[KEY_RATE].text()
            rate_data_source = row[KEY_RATE_DATA_SOURCE].text()
            
            row_dict = { KEY_COMPONENT: component,
                         KEY_TYPE: material_type,
                         KEY_GRADE: material_grade,
                         KEY_QUANTITY: quantity if quantity.strip() else "0",
                         KEY_UNIT_M3: unit_m3,
                         KEY_RATE: rate if rate.strip() else "0.00",
                         KEY_RATE_DATA_SOURCE: rate_data_source,
                         "carbon_emission": row.get("carbon_emission", ""),
                         "carbon_unit": row.get("carbon_unit", ""),
                         "conversion_factor": row.get("conversion_factor", ""),
                         "carbon_source": row.get("carbon_source", ""),
                         "recyclable": row.get("recyclable", False),
                         # JAWWAD: Capture new fields in collected data
                         "scrap_rate": row.get("scrap_rate", ""),
                         "recycle_percentage": row.get("recycle_percentage", ""),
                         "save_to_db": row.get("save_to_db", False),
                         "target_db": row.get("target_db", None)
                        }
            rows_data.append(row_dict)
        return rows_data

    def _on_value_changed(self, *_args):
        if getattr(self, "_initializing", False):
            return
        if self.parent_widget and hasattr(self.parent_widget, "mark_state_changed"):
            self.parent_widget.mark_state_changed()

    def _on_type_material_changed(self, text, unit_widget):
        self.update_comp_units(text, unit_widget)
        self._on_value_changed()

    def update_comp_material(self, selected_component):
        comp_data = self.data.get(selected_component, {})
        materials = comp_data.keys()

        for i in range(len(self.material_rows)):
            material_widget = self.material_rows[i][KEY_TYPE]
            unit_combo = self.material_rows[i][KEY_UNIT_M3]
            
            if isinstance(material_widget, QComboBox):
                material_widget.clear()
                material_widget.addItems(materials)
                current_text = material_widget.currentText()
                if current_text:
                    self.update_comp_units(current_text, unit_combo)
            
            elif isinstance(material_widget, QLineEdit):
                current_text = material_widget.text()
                if current_text:
                    self.update_comp_units(current_text, unit_combo)

        self._on_value_changed()
   
    def update_comp_units(self, selected_material, widget):
        widget.clear()
        widget.addItems(DROPDOWN_UNITS)

    def open_add_material_popup(self):
        selected_component = self.component_combobox.currentText()
        materials_data = self.data.get(selected_component, {})
        
        current_region = "Unknown"
        current_sor = "Unknown"
        if self.parent_widget:
            current_region = self.parent_widget.region_combo.currentText()
            current_sor = self.parent_widget.sor_combo.currentText()
            
        popup = MaterialInputPopup(materials_data, selected_component, current_region, current_sor, self)
        # JAWWAD: Connect to data_submitted signal
        popup.data_submitted.connect(self.add_row_from_popup_data)
        popup.exec()

    def add_row_from_popup_data(self, data):
        # JAWWAD: START Real-time Save Implementation
        saved_item_id = None
        
        # USE THE PARENT WIDGET'S MANAGER to ensure we write to the active project context
        if self.parent_widget and getattr(self.parent_widget, 'data_manager', None) and self.parent_widget.project_id:
            try:
                # Determine sub-category from combobox
                sub_cat = "super_structure"
                
                # Call the manager
                # NOTE: We assume everything in SuperStructure widget goes under "construction_work_data"
                saved_item_id = self.parent_widget.data_manager.add_material_item(
                    project_id=self.parent_widget.project_id,
                    category="construction_work_data",
                    sub_category=sub_cat,
                    material_data=data
                )
                print(f"✅ Real-time save successful for {sub_cat}. ID: {saved_item_id}")
            except Exception as e:
                print(f"❌ Real-time save failed: {e}")
        else:
            # JAWWAD: DEBUGGING
            print("CRITICAL ERROR: Save skipped!")
            if not self.parent_widget: print(" - Parent widget is None")
            elif not getattr(self.parent_widget, 'data_manager', None): print(" - Data Manager is None")
            elif not getattr(self.parent_widget, 'project_id', None): print(" - Project ID is None")
        # JAWWAD: END Real-time Save Implementation

        # JAWWAD: Pass the saved ID to the row creator so we can delete it later
        if data.get('is_custom', False):
            self.add_custom_material_row(data, item_id=saved_item_id)
        else:
            self.add_material_row(data, item_id=saved_item_id)

    # JAWWAD: New method to handle Auto-Delete
    def handle_auto_delete(self, row_widgets):
        """
        Handles removing the row from UI AND deleting from Autosave JSON.
        """
        # 1. Get the ID we stored during creation
        item_id = row_widgets.get('db_id')

        # 2. If we have an ID and a Data Manager, call the delete API
        if item_id and self.parent_widget and getattr(self.parent_widget, 'data_manager', None):
            try:
                sub_cat ="super_structure"
                
                # We assume delete_material_item exists in data_manager
                self.parent_widget.data_manager.soft_delete_material_item(
                    project_id=self.parent_widget.project_id,
                    category="construction_work_data",
                    sub_category=sub_cat,
                    item_id=item_id
                )
                print(f"🗑️ Triggered auto-delete for ID: {item_id}")
            except Exception as e:
                print(f"❌ Auto-delete failed: {e}")

        # 3. Remove from UI (Visual)
        self.remove_material_row_by_widgets(row_widgets)

    def add_custom_material_row(self, data=None, item_id=None):
        validator = QDoubleValidator()
        validator.setRange(0.0, 9999999.999, 3)
        validator.setBottom(0.0)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
   
        row_widgets = {}
        # JAWWAD: Store the Database ID
        row_widgets['db_id'] = item_id

        row_idx = self.current_material_row_idx
        
        type_material_input = QLineEdit()
        type_material_input.setPlaceholderText("Enter custom material")
        type_material_input.setObjectName("MaterialGridInput")
        type_material_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        type_material_input.installEventFilter(self.lock_event_filter)
        type_material_input.setReadOnly(True)
        type_material_input.setStyleSheet("background-color: #FFFFFF; color: #000000;")
        
        self.material_grid_layout.addWidget(type_material_input, row_idx, 0, 1, 2)
        row_widgets[KEY_TYPE] = type_material_input
        type_material_input.textChanged.connect(self._on_value_changed)

        quantity_edit = QLineEdit()
        quantity_edit.setValidator(validator)
        quantity_edit.setPlaceholderText("0")
        quantity_edit.setObjectName("MaterialGridInput")
        quantity_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        quantity_edit.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(quantity_edit, row_idx, 2)
        row_widgets[KEY_QUANTITY] = quantity_edit
        quantity_edit.textChanged.connect(self._on_value_changed)

        unit_combo_m3 = QComboBox()
        unit_combo_m3.setEditable(False)
        unit_combo_m3.setMinimumWidth(120) 
        unit_combo_m3.addItems(DROPDOWN_UNITS)
        unit_combo_m3.setObjectName("MaterialGridInput")
        unit_combo_m3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        unit_combo_m3.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(unit_combo_m3, row_idx, 3)
        row_widgets[KEY_UNIT_M3] = unit_combo_m3
        unit_combo_m3.currentTextChanged.connect(self._on_value_changed)

        rate_edit = QLineEdit()
        rate_edit.setValidator(validator)
        rate_edit.setPlaceholderText("0.00")
        rate_edit.setObjectName("MaterialGridInput")
        rate_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rate_edit.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(rate_edit, row_idx, 4)
        row_widgets[KEY_RATE] = rate_edit
        rate_edit.textChanged.connect(self._on_value_changed)

        rate_data_source_edit = QLineEdit()
        rate_data_source_edit.setObjectName("MaterialGridInput")
        rate_data_source_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rate_data_source_edit.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(rate_data_source_edit, row_idx, 5)
        row_widgets[KEY_RATE_DATA_SOURCE] = rate_data_source_edit
        rate_data_source_edit.textChanged.connect(self._on_value_changed)

        remove_button = QPushButton("x")
        remove_button.setFixedSize(24, 24)
        remove_button.installEventFilter(self.lock_event_filter) 
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #FFCCCC;
                border: 1px solid #FF9999;
                border-radius: 12px;
                font-weight: bold;
                line-height:12px;
                padding: 0px;
                color: #CC0000;
            }
            QPushButton:hover { background-color: #FF9999; color: white; }
            QPushButton:pressed { background-color: #FF6666; }
            QPushButton[locked_state="true"] {
                background-color: #F8F8F8;
                border: 1px solid #E0E0E0;
                color: #CCCCCC;
            }
        """)
        # JAWWAD: Connect to auto-delete handler
        remove_button.clicked.connect(lambda: self.handle_auto_delete(row_widgets))
        
        self.material_grid_layout.addWidget(remove_button, row_idx, 6, alignment=Qt.AlignCenter)
        
        row_widgets['remove_button'] = remove_button
        
        type_material_input.textChanged.connect(
            lambda text, unit_widget=unit_combo_m3: self._on_type_material_changed(text, unit_widget)
        )

        self.material_rows.append(row_widgets)
        self.current_material_row_idx += 1
        
        if data:
            type_material_input.setText(data.get(KEY_TYPE, ""))
            self.update_comp_units(type_material_input.text(), unit_combo_m3)
            
            target_unit = data.get(KEY_UNIT_M3, "")
            if target_unit:
                if unit_combo_m3.findText(target_unit) == -1:
                    unit_combo_m3.addItem(target_unit)
                unit_combo_m3.setCurrentText(target_unit)
            
            quantity_edit.setText(data.get(KEY_QUANTITY, ""))
            rate_edit.setText(data.get(KEY_RATE, ""))
            rate_data_source_edit.setText(data.get(KEY_RATE_DATA_SOURCE, ""))
            
            row_widgets["carbon_emission"] = data.get("carbon_emission")
            row_widgets["carbon_unit"] = data.get("carbon_unit")
            row_widgets["conversion_factor"] = data.get("conversion_factor")
            row_widgets["carbon_source"] = data.get("carbon_source")
            row_widgets["recyclable"] = data.get("recyclable")
            # JAWWAD: Save new recyclable data fields to row widgets
            row_widgets["scrap_rate"] = data.get("scrap_rate")
            row_widgets["recycle_percentage"] = data.get("recycle_percentage")
            # JAWWAD: End Saving
            row_widgets["save_to_db"] = data.get("save_to_db")
            row_widgets["target_db"] = data.get("target_db")

        self.updateGeometry()
        self.adjustSize()
        self._on_value_changed()

    def add_material_row(self, data=None, item_id=None):
        validator = QDoubleValidator()
        validator.setRange(0.0, 9999999.999, 3)
        validator.setBottom(0.0)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
   
        row_widgets = {}
        # JAWWAD: Store the Database ID
        row_widgets['db_id'] = item_id

        row_idx = self.current_material_row_idx

        type_material_input = QLineEdit()
        type_material_input.setObjectName("MaterialGridInput")
        type_material_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        type_material_input.installEventFilter(self.lock_event_filter)
        type_material_input.setReadOnly(True)
        type_material_input.setStyleSheet("background-color: #FFFFFF; color: #000000;")
        
        self.material_grid_layout.addWidget(type_material_input, row_idx, 0, 1, 2)
        row_widgets[KEY_TYPE] = type_material_input
        type_material_input.textChanged.connect(self._on_value_changed)

        quantity_edit = QLineEdit()
        quantity_edit.setValidator(validator)
        quantity_edit.setPlaceholderText("0")
        quantity_edit.setObjectName("MaterialGridInput")
        quantity_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        quantity_edit.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(quantity_edit, row_idx, 2)
        row_widgets[KEY_QUANTITY] = quantity_edit
        quantity_edit.textChanged.connect(self._on_value_changed)

        unit_combo_m3 = QComboBox()
        unit_combo_m3.setEditable(False)
        unit_combo_m3.setMinimumWidth(120) 
        unit_combo_m3.addItems(DROPDOWN_UNITS)
        unit_combo_m3.setObjectName("MaterialGridInput")
        unit_combo_m3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        unit_combo_m3.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(unit_combo_m3, row_idx, 3)
        row_widgets[KEY_UNIT_M3] = unit_combo_m3
        unit_combo_m3.currentTextChanged.connect(self._on_value_changed)

        rate_edit = QLineEdit()
        rate_edit.setValidator(validator)
        rate_edit.setPlaceholderText("0.00")
        rate_edit.setObjectName("MaterialGridInput")
        rate_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rate_edit.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(rate_edit, row_idx, 4)
        row_widgets[KEY_RATE] = rate_edit
        rate_edit.textChanged.connect(self._on_value_changed)

        rate_data_source_edit = QLineEdit()
        rate_data_source_edit.setObjectName("MaterialGridInput")
        rate_data_source_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rate_data_source_edit.installEventFilter(self.lock_event_filter) 
        self.material_grid_layout.addWidget(rate_data_source_edit, row_idx, 5)
        row_widgets[KEY_RATE_DATA_SOURCE] = rate_data_source_edit
        rate_data_source_edit.textChanged.connect(self._on_value_changed)

        remove_button = QPushButton("x")
        remove_button.setFixedSize(24, 24)
        remove_button.installEventFilter(self.lock_event_filter) 
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #FFCCCC;
                border: 1px solid #FF9999;
                border-radius: 12px;
                font-weight: bold;
                line-height:12px;
                padding: 0px;
                color: #CC0000;
            }
            QPushButton:hover { background-color: #FF9999; color: white; }
            QPushButton:pressed { background-color: #FF6666; }
            QPushButton[locked_state="true"] {
                background-color: #F8F8F8;
                border: 1px solid #E0E0E0;
                color: #CCCCCC;
            }
        """)
        # JAWWAD: Connect to auto-delete handler
        remove_button.clicked.connect(lambda: self.handle_auto_delete(row_widgets))
        
        self.material_grid_layout.addWidget(remove_button, row_idx, 6, alignment=Qt.AlignCenter)
        
        row_widgets['remove_button'] = remove_button
        
        type_material_input.textChanged.connect(
            lambda text, unit_widget=unit_combo_m3: self._on_type_material_changed(text, unit_widget)
        )

        self.material_rows.append(row_widgets)
        self.current_material_row_idx += 1
        
        if data:
            type_material_input.setText(data.get(KEY_TYPE, ""))
            self.update_comp_units(type_material_input.text(), unit_combo_m3)
            
            target_unit = data.get(KEY_UNIT_M3, "")
            if target_unit:
                if unit_combo_m3.findText(target_unit) == -1:
                    unit_combo_m3.addItem(target_unit)
                unit_combo_m3.setCurrentText(target_unit)
            
            quantity_edit.setText(data.get(KEY_QUANTITY, ""))
            rate_edit.setText(data.get(KEY_RATE, ""))
            rate_data_source_edit.setText(data.get(KEY_RATE_DATA_SOURCE, ""))
            
            row_widgets["carbon_emission"] = data.get("carbon_emission")
            row_widgets["carbon_unit"] = data.get("carbon_unit")
            row_widgets["conversion_factor"] = data.get("conversion_factor")
            row_widgets["carbon_source"] = data.get("carbon_source")
            row_widgets["recyclable"] = data.get("recyclable")
            # JAWWAD: Save new recyclable data fields to row widgets
            row_widgets["scrap_rate"] = data.get("scrap_rate")
            row_widgets["recycle_percentage"] = data.get("recycle_percentage")
            # JAWWAD: End Saving
            row_widgets["save_to_db"] = data.get("save_to_db")
            row_widgets["target_db"] = data.get("target_db")

        self.updateGeometry()
        self.adjustSize()
        self._on_value_changed()

    def remove_material_row_by_widgets(self, row_widgets_to_remove):
        if row_widgets_to_remove not in self.material_rows:
            return

        row_idx_in_grid = -1
        for i, row_dict in enumerate(self.material_rows):
            if row_dict == row_widgets_to_remove:
                row_idx_in_grid = i + 1
                break

        if row_idx_in_grid == -1:
            return

        for col in range(self.material_grid_layout.columnCount()):
            item = self.material_grid_layout.itemAtPosition(row_idx_in_grid, col)
            if item:
                if item.widget():
                    widget = item.widget()
                    self.material_grid_layout.removeWidget(widget)
                    widget.deleteLater()
                elif item.layout():
                    layout = item.layout()
                    while layout.count():
                        sub_item = layout.takeAt(0)
                        if sub_item.widget():
                            sub_item.widget().deleteLater()
                    self.material_grid_layout.removeItem(layout)

        self.material_rows.remove(row_widgets_to_remove)
        self.current_material_row_idx -= 1

        for r_idx in range(row_idx_in_grid, self.current_material_row_idx):
            c_idx = 0
            while c_idx < self.material_grid_layout.columnCount():
                item = self.material_grid_layout.itemAtPosition(r_idx + 1, c_idx)
                if item:
                    try:
                        row_span = item.rowSpan()
                        col_span = item.columnSpan()
                    except AttributeError:
                        row_span = 1
                        col_span = 1
                    
                    alignment = Qt.Alignment()
                    if c_idx == 6:
                        alignment = Qt.AlignCenter
                    
                    if item.widget():
                        widget = item.widget()
                        self.material_grid_layout.removeWidget(widget)
                        self.material_grid_layout.addWidget(widget, r_idx, c_idx, row_span, col_span, alignment)
                    elif item.layout():
                        layout = item.layout()
                        self.material_grid_layout.removeItem(layout)
                        self.material_grid_layout.addLayout(layout, r_idx, c_idx, row_span, col_span)
                    
                    c_idx += col_span
                else:
                    old_item = self.material_grid_layout.itemAtPosition(r_idx, c_idx)
                    if old_item:
                        if old_item.widget():
                            old_item.widget().deleteLater()
                        self.material_grid_layout.removeItem(old_item)
                    c_idx += 1

        self.updateGeometry()
        self.update()
        self.material_grid_layout.invalidate()
        self.adjustSize()
        self._on_value_changed()

class SuperStructure(QWidget):
    closed = Signal()
    next = Signal(str)
    back = Signal(str)
    def __init__(self, database, parent=None):
        super().__init__()
        self.database_manager = database
        
        # JAWWAD: Project ID initialization for real-time saves
        self.project_id = None 
        # JAWWAD: Initialize ProjectDataManager if available
        if ProjectDataManager:
            self.data_manager = ProjectDataManager() 
        else:
            self.data_manager = None

        self.data_id = []
        self.setObjectName("central_panel_widget")
        self.component_widgets = []
        self._initializing = True
        self.state_changed = True
        self.is_first_visit = True
        self.is_locked = False
        
        self.warning_cooldown = False
        
        self.lock_filter = LockEventFilter(self)

        self.setStyleSheet("""
            #central_panel_widget {
                background-color: #F8F8F8;
                border-radius: 8px;
            }
            #central_panel_widget QLabel {
                color: #333333;
                font-size: 12px;
            }
            #central_panel_widget QLabel#page_number_label {
                font-size: 14px;
                font-weight: bold;
                color: #555555;
            }

            QScrollArea {
                background-color: transparent;
                outline: none;
            }
            #scroll_content_widget {
                background-color: #FFF9F9;
                border: 1px solid #000000;
                padding-bottom: 20px;
            }

            QScrollBar:vertical {
                border: 1px solid #E0E0E0;
                background: #F0F0F0;
                width: 12px;
                margin: 18px 0px 18px 0px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #C0C0C0;
                border: 1px solid #A0A0A0;
                min-height: 20px;
                border-radius: 5px;
            }

            QScrollBar::add-line:vertical {
                border: 1px solid #E0E0E0;
                background: #E8E8E8;
                height: 18px;
                subcontrol-origin: bottom;
                subcontrol-position: bottom;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }

            QScrollBar::sub-line:vertical {
                border: 1px solid #E0E0E0;
                background: #E8E8E8;
                height: 18px;
                subcontrol-origin: top;
                subcontrol-position: top;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }

            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 10px;
                height: 10px;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar::up-arrow:vertical {
                image: url(:/images/arrow_up.png);
            }
            QScrollBar::down-arrow:vertical {
                image: url(:/images/arrow_down.png);
            }

            QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
                background: #D0D0D0;
            }

            QPushButton#top_button_left_panel {
                background-color: #FDEFEF;
                border-top: 1px solid #000000;
                border-left: 1px solid #000000;
                border-right: 1px solid #000000;
                text-align: left;
                padding: 4px 10px;
                color: #000000;
            }
            QPushButton#top_button_left_panel:hover {
                background-color: #F0E6E6;
                border-color: #808080;
            }
            QPushButton#top_button_left_panel:pressed {
                background-color: #FFF3F3;
                border-color: #606060;
            }

            #component_first_widget {
                background-color: transparent;
                margin-top: 10px;
            }

            #component_first_scroll_content_widget {
                background-color: #FFFFFF;
                padding: 10px;
                border-radius: 8px;
            }

            QPushButton#nav_button {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #3F3E5E;
                padding: 6px 15px;
                text-align: center;
                min-width: 80px;
            }
            QPushButton#nav_button:hover {
                background-color: #F8F8F8;
                border-color: #C0C0C0;
            }
            QPushButton#nav_button:pressed {
                background-color: #E8E8E8;
                border-color: #A0A0A0;
            }
            
            QPushButton#lock_button {
                background-color: #FFF8DC; 
                border: 2px solid #DAA520; 
                border-radius: 12px;
                color: #3F3E5E;
                padding: 2px 2px;
                text-align: center;
                font-weight: bold;
            }
            QPushButton#lock_button:hover {
                background-color: #FFE4B5;
                border-color: #C0C0C0;
            }
            QPushButton#lock_button[locked="true"] {
                background-color: #FFEEEE;
                border-color: #FF9999;
                color: #CC0000;
            }
            QPushButton#lock_button[locked="false"] {
                background-color: #E8F5E9;
                border-color: #45913E;
                color: #00AA00;
            }
            
            QLineEdit {
                text-align: center;
            }
            QComboBox {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
                text-align: center;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 5px;
            }
            QComboBox::down-arrow {
                image: url(:/images/country_arrow.png);
                width: 30px;
                height: 30px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #DDDCE0;
                border-radius: 5px;
                background-color: #FFFFFF;
                outline: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #FDEFEF;
                color: #000000;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #FDEFEF;
            }

            #MaterialGridLabel {
                font-weight: bold;
                color: #3F3E5E;
                padding: 5px;
                text-align: center;
            }
            #MaterialGridInput {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
                background-color: #FFFFFF;
            }
            #MaterialGridInput:focus {
                border: 1px solid #DDDCE0;
                background-color: #FFFFFF;
            }
            #MaterialGridInput:disabled {
                background-color: #F0F0F0;
                color: #888888;
            }
            
            QPushButton#add_material_button, QPushButton#add_component_button {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #3F3E5E;
                padding: 6px 15px;
                text-align: center;
            }
            QPushButton#add_material_button:hover, QPushButton#add_component_button:hover {
                background-color: #F8F8F8;
                border-color: #C0C0C0;
            }
            QPushButton#add_material_button:pressed, QPushButton#add_component_button:pressed {
                background-color: #E8E8E8;
                border-color: #A0A0A0;
            }
            QPushButton#add_material_button:disabled, QPushButton#add_component_button:disabled {
                background-color: #F0F0F0;
                color: #AAAAAA;
                border-color: #D0D0D0;
            }
            
            QPushButton#add_material_button[locked_state="true"], 
            QPushButton#add_component_button[locked_state="true"] {
                background-color: #F0F0F0;
                color: #AAAAAA;
                border-color: #D0D0D0;
            }
            #MaterialGridInput[locked_state="true"] {
                background-color: #E0E0E0;
                color: #888888;
                border: 1px solid #D0D0D0;
            }
        """)
        
        self.left_panel_vlayout = QVBoxLayout(self)
        self.left_panel_vlayout.setContentsMargins(0,0,0,0)
        self.left_panel_vlayout.setSpacing(0)

        header_container = QWidget()
        header_container.setStyleSheet("background-color: #FFF9F9; border-bottom: 1px solid #ccc;")
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        header_layout.addWidget(QLabel("Region:"))
        self.region_combo = QComboBox()
        self.region_combo.setFixedWidth(150)
        
        if sor_manager:
            self.region_combo.addItems(sor_manager.get_regions())
            sor_manager.registry_updated.connect(self.refresh_ui_options)
        else:
            self.region_combo.addItems(["India", "USA"])
            
        self.region_combo.currentTextChanged.connect(self.on_region_changed)
        header_layout.addWidget(self.region_combo)
        
        header_layout.addSpacing(20)
        
        header_layout.addWidget(QLabel("Select SOR:"))
        self.sor_combo = QComboBox()
        self.sor_combo.setFixedWidth(200)
        self.on_region_changed(self.region_combo.currentText()) 
        self.sor_combo.currentTextChanged.connect(self.on_sor_changed)
        header_layout.addWidget(self.sor_combo)
        
        header_layout.addStretch()
        
        self.left_panel_vlayout.addWidget(header_container)

        lock_hlayout = QHBoxLayout()
        lock_hlayout.setContentsMargins(0,2,2,0)
        lock_hlayout.setSpacing(0)
        lock_hlayout.addStretch()

        self.lock_button = QPushButton("🔓") 
        self.lock_button.setObjectName("lock_button")
        self.lock_button.setFixedSize(30, 30) 
        self.lock_button.setCursor(Qt.PointingHandCursor)
        self.lock_button.setProperty("locked", "false")
        self.lock_button.clicked.connect(self.toggle_lock)
        self.lock_button.setToolTip("Click to Lock Editing") 
        lock_hlayout.addWidget(self.lock_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        scroll_content_widget = QWidget()
        scroll_content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        scroll_content_widget.setObjectName("scroll_content_widget")
        self.scroll_area.setWidget(scroll_content_widget)

        self.scroll_content_layout = QVBoxLayout(scroll_content_widget)
        self.scroll_content_layout.setContentsMargins(0,0,0,0)
        self.scroll_content_layout.setSpacing(0)

        self.scroll_content_layout.addLayout(lock_hlayout)

        self.add_component_button = QPushButton("+ Add Component")
        self.add_component_button.setObjectName("add_component_button")
        self.add_component_button.installEventFilter(self.lock_filter) 
        self.add_component_button.clicked.connect(self.add_component_layout)

        self.button_h_layout = QHBoxLayout()
        self.button_h_layout.setSpacing(10)
        self.button_h_layout.setContentsMargins(10,10,10,10)

        self.button_h_layout.addStretch(6)

        back_button = QPushButton("Back")
        back_button.setObjectName("nav_button")
        back_button.clicked.connect(lambda: self.back.emit(KEY_SUPERSTRUCTURE))
        self.button_h_layout.addWidget(back_button)

        next_button = QPushButton("Next")
        next_button.setObjectName("nav_button")
        next_button.clicked.connect(self.on_next_clicked)
        self.button_h_layout.addWidget(next_button)

        self.add_component_layout()

        self.scroll_content_layout.addLayout(self.button_h_layout)
        self.left_panel_vlayout.addWidget(self.scroll_area)
        self._initializing = False

    # JAWWAD: Method to allow Main Window to set the Project ID context
    def set_project_id(self, pid):
        self.project_id = pid
        print(f"SuperStructure Widget: Project ID set to {pid}")

    def showEvent(self, event):
        super().showEvent(event)
        if not self.is_first_visit:
            self.set_form_locked(True)
        else:
            self.is_first_visit = False

    @Slot()
    def refresh_ui_options(self):
        print("UI: Refreshing Region/SOR dropdowns...")
        current_region = self.region_combo.currentText()
        current_sor = self.sor_combo.currentText()
        
        self.region_combo.blockSignals(True)
        self.region_combo.clear()
        if sor_manager:
            self.region_combo.addItems(sor_manager.get_regions())
        else:
            self.region_combo.addItems(["India", "USA"])
        self.region_combo.blockSignals(False)
        
        idx = self.region_combo.findText(current_region)
        if idx != -1:
            self.region_combo.setCurrentIndex(idx)
        elif self.region_combo.count() > 0:
            self.region_combo.setCurrentIndex(0)
            
        self.on_region_changed(self.region_combo.currentText())
        
        idx_sor = self.sor_combo.findText(current_sor)
        if idx_sor != -1:
            self.sor_combo.setCurrentIndex(idx_sor)

    def on_region_changed(self, new_region):
        if not sor_manager: return
        sors = sor_manager.get_sors_for_region(new_region)
        self.sor_combo.blockSignals(True)
        self.sor_combo.clear()
        self.sor_combo.addItems(sors)
        self.sor_combo.blockSignals(False)
        if sors:
            self.sor_combo.setCurrentIndex(0)
            self.on_sor_changed(sors[0])

    def on_sor_changed(self, new_sor):
        if not sor_manager or not new_sor: return
        region = self.region_combo.currentText()
        success, msg = sor_manager.set_active_sor(region, new_sor)
        if success:
            print(f"UI: Successfully loaded {new_sor}")
        else:
            print(f"UI: Failed to load {new_sor}: {msg}")

    def toggle_lock(self):
        self.set_form_locked(not self.is_locked)
       
    def set_form_locked(self, locked):
        self.is_locked = locked
        
        if locked:
            self.lock_button.setText("🔒")
            self.lock_button.setProperty("locked", "true")
            self.lock_button.setToolTip("Click to Unlock to Edit")
        else:
            self.lock_button.setText("🔓")
            self.lock_button.setProperty("locked", "false")
            self.lock_button.setToolTip("Click to Lock Editing")
        
        self.lock_button.style().unpolish(self.lock_button)
        self.lock_button.style().polish(self.lock_button)
        
        for component_widget in self.component_widgets:
            component_widget.set_locked(locked)
        
        self.add_component_button.setProperty("locked_state", str(locked).lower())
        self.add_component_button.style().unpolish(self.add_component_button)
        self.add_component_button.style().polish(self.add_component_button)
        
        self.region_combo.setEnabled(not locked)
        self.sor_combo.setEnabled(not locked)

    def trigger_lock_warning(self):
        if self.warning_cooldown:
            return
            
        self.warning_cooldown = True
        
        if self.lock_button:
            global_pos = self.lock_button.mapToGlobal(QPoint(-80, self.lock_button.height() + 5))
            QToolTip.showText(global_pos, "Unlock to Edit", self.lock_button, self.lock_button.rect(), 2000)
            
        QTimer.singleShot(2000, self._reset_warning_cooldown)

    def _reset_warning_cooldown(self):
        self.warning_cooldown = False

    def add_component_layout(self):
        new_component = ComponentWidget(self, self.lock_filter)
        self.component_widgets.append(new_component)
        new_component.remove_component_button.clicked.connect(lambda: self.remove_component_layout(new_component))

        if self.scroll_content_layout.indexOf(self.add_component_button) != -1:
            self.scroll_content_layout.removeWidget(self.add_component_button)
        if self.scroll_content_layout.indexOf(self.button_h_layout) != -1:
            self.scroll_content_layout.removeItem(self.button_h_layout)

        self.scroll_content_layout.addWidget(new_component)
        self.scroll_content_layout.addWidget(self.add_component_button, alignment=Qt.AlignCenter)
        self.scroll_content_layout.addLayout(self.button_h_layout)

        if self.is_locked:
            new_component.set_locked(True)

        self.scroll_area.widget().updateGeometry()
        self.scroll_area.widget().adjustSize()
        self.mark_state_changed()

    def remove_component_layout(self, component_to_remove):
        if component_to_remove in self.component_widgets:
            self.scroll_content_layout.removeWidget(component_to_remove)
            self.component_widgets.remove(component_to_remove)
            component_to_remove.deleteLater()
            self.scroll_area.widget().updateGeometry()
            self.scroll_area.widget().adjustSize()
            self.mark_state_changed()

    def collect_data(self):
        all_data = []
        for component_widget in self.component_widgets:
            component_data = component_widget.collect_data()
            all_data.append(component_data)
        return all_data
      
    def mark_state_changed(self):
        if self._initializing:
            return
        self.state_changed = True
      
    def save_data(self):
        from pprint import pprint
        data = self.collect_data()
        print("\nCollected Data from Super-Structure UI:")
        print(f"Context -> Region: {self.region_combo.currentText()}, SOR: {self.sor_combo.currentText()}")
        pprint(data)
            
        if self.data_id:
            self.database_manager.replace_structure_work_rows(KEY_SUPERSTRUCTURE, data, self.data_id)
        else:
            self.data_id = self.database_manager.input_data_row(KEY_SUPERSTRUCTURE, data)
        self.state_changed = False
      
    def on_next_clicked(self):
        if not self.state_changed:
            self.next.emit(KEY_SUPERSTRUCTURE)
            return
        if self.data_id:
            message = "Do you want to replace previous data?"
        else:
            message = "Do you want to save data?"
        reply = QMessageBox.question(self, "Confirm", message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.save_data()
        self.next.emit(KEY_SUPERSTRUCTURE)

    def expand_scroll_area(self):
        # self.central_widget.layout().invalidate()
        pass

    def close_widget(self):
        self.closed.emit()
        self.setParent(None)
      
    #Ritik - START: Improved Excel Data Mapping for SuperStructure Widget
    def load_from_excel_sections(self, sections_data):
        """
        Load parsed Excel data sections into the SuperStructure widget.
        Data is grouped by component type - all materials for the same component
        are displayed under one component widget.
        """
        print(f"\n[EXCEL IMPORT] Loading {len(sections_data)} section(s) into SuperStructure widget")

        # Ritik - START: Remove any existing default components so imported data replaces them
        # Remove any existing default components so imported data replaces them
        if getattr(self, 'component_widgets', None):
            print(f"  [INFO] Clearing {len(self.component_widgets)} existing component(s) before import")
            while self.component_widgets:
                self.remove_component_layout(self.component_widgets[-1])
        # Ritik - END: Removed default components prior to Excel import
        
        # ritik: GROUP DATA BY COMPONENT TYPE
        component_data_map = {}
        total_materials = 0
        
        for section_idx, section in enumerate(sections_data):
            component_name = section.get('type', '')
            rows = section.get('data', [])
            sheet_name = section.get('sheetName', 'Unknown')
            
            if not component_name:
                print(f"  [SKIP] Section {section_idx}: No component name found")
                continue
            
            print(f"  [SECTION {section_idx}] Sheet: {sheet_name}, Component: {component_name}, Rows: {len(rows)}")
            
            if component_name not in component_data_map:
                component_data_map[component_name] = []
                print(f"    ✓ Grouped component: {component_name}")
            
            component_data_map[component_name].extend(rows)
            total_materials += len(rows)
        
        print(f"\n  [GROUPING] Total materials: {total_materials}, Total components: {len(component_data_map)}")
        
        # ritik: CREATE COMPONENT WIDGETS AND POPULATE WITH GROUPED DATA
        for component_idx, (component_name, all_rows) in enumerate(component_data_map.items()):
            print(f"\n  [COMPONENT {component_idx}] {component_name} ({len(all_rows)} materials)")
            
            self.add_component_layout()
            new_comp_widget = self.component_widgets[-1]
            
            index = new_comp_widget.component_combobox.findText(component_name, Qt.MatchFixedString)
            if index >= 0:
                new_comp_widget.component_combobox.setCurrentIndex(index)
                print(f"    ✓ Set component dropdown to: {component_name}")
            else:
                new_comp_widget.component_combobox.addItem(component_name)
                new_comp_widget.component_combobox.setCurrentText(component_name)
                print(f"    ✓ Added new component: {component_name}")

            # Ritik - COMMENT OUT: clear_rows() has issues with rowSpan, just add materials instead
            # new_comp_widget.clear_rows()
            
            for row_idx, row_data in enumerate(all_rows):
                try:
                    material_name = str(row_data.get('name', '')).strip()
                    if not material_name:
                        print(f"      [WARN] Material {row_idx}: Missing material name, skipping")
                        continue
                    
                    quantity_val = row_data.get('quantity', '1')
                    try:
                        quantity_str = str(float(quantity_val))
                    except (ValueError, TypeError):
                        quantity_str = '1'
                        print(f"      [INFO] Material {row_idx}: Invalid quantity '{quantity_val}', using default '1'")
                    
                    unit_val = str(row_data.get('unit', '')).lower().strip()
                    if not unit_val or unit_val == 'none':
                        unit_val = 'cum'
                        print(f"      [INFO] Material {row_idx}: No unit specified, using default 'cum'")
                    
                    rate_val = row_data.get('rate', '0')
                    try:
                        rate_str = str(float(rate_val))
                    except (ValueError, TypeError):
                        rate_str = '0'
                        print(f"      [INFO] Material {row_idx}: Invalid rate '{rate_val}', using default '0'")
                    
                    rate_source = str(row_data.get('rate_src', 'Excel Import')).strip()
                    if not rate_source:
                        rate_source = 'Excel Import'
                    
                    carbon_emission_val = row_data.get('carbon_emission', 'not_available')
                    if carbon_emission_val is None:
                        carbon_emission_str = 'not_available'
                    else:
                        carbon_emission_str = str(carbon_emission_val).strip()
                        if not carbon_emission_str or carbon_emission_str.lower() in ['na', 'not available', 'not_available', 'none']:
                            carbon_emission_str = 'not_available'
                    
                    carbon_units = str(row_data.get('carbon_emission_units', 'kgCO2e')).strip()
                    if not carbon_units:
                        carbon_units = 'kgCO2e'
                    
                    conversion_factor_val = row_data.get('conversion_factor', 'not_available')
                    if conversion_factor_val is None:
                        conversion_factor_str = 'not_available'
                    else:
                        conversion_factor_str = str(conversion_factor_val).strip()
                        if not conversion_factor_str or conversion_factor_str.lower() in ['na', 'not available', 'not_available', 'none']:
                            conversion_factor_str = 'not_available'
                    
                    carbon_source = str(row_data.get('carbon_emission_src', '')).strip()
                    
                    recycleable_val = row_data.get('recycleable', 'Non-recyclable')
                    recycleable_str = str(recycleable_val).strip() if recycleable_val else 'Non-recyclable'
                    is_recyclable = recycleable_str.lower() in ['recyclable', 'recycleable', 'yes', 'true']
                    
                    mapped_data = {
                        KEY_TYPE: material_name,
                        KEY_QUANTITY: quantity_str,
                        KEY_UNIT_M3: unit_val,
                        KEY_RATE: rate_str,
                        KEY_RATE_DATA_SOURCE: rate_source,
                        "carbon_emission": carbon_emission_str,
                        "carbon_unit": carbon_units,
                        "conversion_factor": conversion_factor_str,
                        "carbon_source": carbon_source,
                        "recyclable": is_recyclable,
                        "save_to_db": False,
                        "is_custom": True
                    }
                    
                    # --- CRITICAL FIX START: Register ID with Backend immediately ---
                    saved_id = None
                    if self.data_manager and self.project_id:
                        try:
                            # Save to autosave.json to generate a UUID so soft-delete works later
                            saved_id = self.data_manager.add_material_item(
                                project_id=self.project_id,
                                category="construction_work_data",
                                sub_category="super_structure",
                                material_data=mapped_data
                            )
                            print(f"      [DB] Registered Item ID: {saved_id}")
                        except Exception as e:
                            print(f"      [ERROR] Could not save to backend: {e}")
                    # --- CRITICAL FIX END ---

                    if hasattr(new_comp_widget, 'add_custom_material_row'):
                        new_comp_widget.add_custom_material_row(mapped_data, item_id=saved_id)
                        print(f"      ✓ Material {row_idx}: {material_name} | {quantity_str} {unit_val} @ {rate_source}")
                    else:
                        new_comp_widget.add_material_row(mapped_data, item_id=saved_id)
                        print(f"      ✓ Material {row_idx}: {material_name} | {quantity_str} {unit_val}")
                        
                except Exception as e:
                    print(f"      [ERROR] Material {row_idx}: Failed to process - {str(e)}")
                    continue
        
        self.mark_state_changed()
        print(f"\n[EXCEL IMPORT] ✓ Complete. All data grouped by components and loaded.\n")

    #Ritik - END: Improved Excel Data Mapping for SuperStructure Widget