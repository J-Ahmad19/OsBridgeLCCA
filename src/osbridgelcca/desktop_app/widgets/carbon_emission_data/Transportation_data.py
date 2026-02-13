from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFrame, QScrollArea, QGridLayout, QSizePolicy, QGroupBox, QDialog, QFormLayout, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QDoubleValidator, QIcon, QPixmap
import json
import os

# Ritik: Updated to fix database argument issue

class VehicleDetailsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vehicle Details")
        self.setFixedWidth(450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Style matches existing app dialogs/forms
        self.setStyleSheet("""
            QDialog {
                background-color: #FFF9F9; 
            }
            QLabel { 
                font-size: 14px; 
                font-weight: bold; 
                color: #3F3E5E; 
            }
            QLineEdit {
                border: 1px solid #DDDCE0; 
                border-radius: 10px; 
                padding: 6px; 
                font-size: 14px;
                background-color: white;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #3F3E5E;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F8F8F8;
                border-color: #C0C0C0;
            }
        """)

        form = QVBoxLayout()
        form.setSpacing(15)

        # Vehicle Name
        form.addWidget(QLabel("Vehicle Name"))
        self.vehicle_name = QLineEdit()
        form.addWidget(self.vehicle_name)

        # Gross Weight
        form.addWidget(QLabel("Gross  Vehicle Weight(Tonnes)"))
        self.gross_weight = QLineEdit()
        self.gross_weight.setValidator(QDoubleValidator())
        self.gross_weight.setFixedWidth(400)
        form.addWidget(self.gross_weight)

        # Cargo Capacity
        form.addWidget(QLabel("Cargo Capacity(Tonnes)"))
        self.cargo_capacity = QLineEdit()
        self.cargo_capacity.setValidator(QDoubleValidator())
        self.cargo_capacity.setFixedWidth(400)
        form.addWidget(self.cargo_capacity)

        # Emission Factor
        form.addWidget(QLabel("Emission Factor (KgCo2/tonne-km)"))
        self.emission_factor = QLineEdit()
        self.emission_factor.setValidator(QDoubleValidator())
        self.emission_factor.setFixedWidth(400)
        form.addWidget(self.emission_factor)

        layout.addLayout(form)
        layout.addStretch()

        # Save Details Button
        self.btn_save = QPushButton("Save Vehicle Details")
        self.btn_save.clicked.connect(self.accept)
        layout.addWidget(self.btn_save, alignment=Qt.AlignCenter)

    def get_data(self):
        return {
            "name": self.vehicle_name.text(),
            "gross_weight": self.gross_weight.text(),
            "cargo_capacity": self.cargo_capacity.text(),
            "emission_factor": self.emission_factor.text()
        }

class TransportationFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Transportation Data")
        self.setFixedWidth(600)
        self.init_ui()

    def get_db_path(self):
        # Calculate path to temp_file_db/temporary_construction_data.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        desktop_app_dir = os.path.dirname(os.path.dirname(current_dir))
        db_path = os.path.join(desktop_app_dir, "temp_file_db", "temporary_construction_data.json")
        return db_path

class TransportationGroupCard(QFrame):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.init_ui()

    def init_ui(self):
        self.setObjectName("GroupCard")
        self.setStyleSheet("""
            QFrame#GroupCard {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- Top Section: Vehicle Info ---
        top_layout = QHBoxLayout()
        
        # Icon placeholder
        icon_label = QLabel() 
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background-color: #E8EAF6; border-radius: 8px;")
        
        # Load SVG Icon
        current_dir = os.path.dirname(os.path.abspath(__file__))
        desktop_app_dir = os.path.dirname(os.path.dirname(current_dir))
        icon_path = os.path.join(desktop_app_dir, "resources", "vectors", "truck_icon.svg")
        
        if os.path.exists(icon_path):
            pixmap = QIcon(icon_path).pixmap(QSize(24, 24))
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText("🚛")
            icon_label.setStyleSheet("background-color: #E8EAF6; border-radius: 8px; font-size: 20px;")
        
        # Vehicle Details
        vehicle_info = QVBoxLayout()
        vehicle_info.setSpacing(2)
        lbl_v_title = QLabel("VEHICLE NAME")
        lbl_v_title.setStyleSheet("color: #757575; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        
        vehicle_name = self.data['vehicle'].get('name', 'Unknown Vehicle')
        lbl_v_name = QLabel(vehicle_name)
        lbl_v_name.setStyleSheet("color: #1A1A1A; font-size: 16px; font-weight: bold;")
        
        vehicle_info.addWidget(lbl_v_title)
        vehicle_info.addWidget(lbl_v_name)

        # Distance Details (Right Aligned)
        distance_info = QVBoxLayout()
        distance_info.setSpacing(2)
        distance_info.setAlignment(Qt.AlignRight)
        
        lbl_d_title = QLabel("DISTANCE TRAVELLED")
        lbl_d_title.setStyleSheet("color: #757575; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        lbl_d_title.setAlignment(Qt.AlignRight)
        
        distance = self.data.get('distance', '0')
        lbl_d_val = QLabel(f"{distance} km")
        lbl_d_val.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: bold;")
        lbl_d_val.setAlignment(Qt.AlignRight)
        
        distance_info.addWidget(lbl_d_title)
        distance_info.addWidget(lbl_d_val)

        top_layout.addWidget(icon_label)
        top_layout.addSpacing(15)
        top_layout.addLayout(vehicle_info)
        top_layout.addStretch()
        top_layout.addLayout(distance_info)
        
        main_layout.addLayout(top_layout)
        
        # Line separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #F0F0F0; border: none; max-height: 1px;")
        main_layout.addWidget(line)

        # --- Middle Section: Materials Table ---
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["MATERIALS", "QUANTITY"])
        
        # Header Styling
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #FFFFFF;
                color: #757575;
                font-size: 10px;
                font-weight: bold;
                border: none;
                padding: 10px 5px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background-color: transparent;
            }
        """)
        
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False) 
        table.setFocusPolicy(Qt.NoFocus)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFrameShape(QFrame.NoFrame)
        
        materials = self.data.get('materials', [])
        total_qty = 0.0
        
        table.setRowCount(len(materials))
        
        for row, item in enumerate(materials):
            try:
                qty = float(item.get('quantity', 0))
            except (ValueError, TypeError):
                qty = 0.0
            total_qty += qty
            unit = item.get('unit', '')

            # Name Cell
            name_text = str(item.get('name', 'Unknown'))
            name_item = QTableWidgetItem(name_text)
            name_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(row, 0, name_item)

            # Quantity Cell
            qty_text = f"{qty} {unit}"
            qty_item = QTableWidgetItem(qty_text)
            qty_item.setFlags(Qt.ItemIsEnabled)
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 1, qty_item)

        # Style the table cells
        table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                padding: 10px 5px;
                border-bottom: 1px solid #F0F0F0;
                color: #333333;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        
        # Resize height
        header_height = table.horizontalHeader().height() if table.horizontalHeader().height() > 0 else 30
        row_height = 40 
        total_height = header_height + (len(materials) * row_height) + 15
        table.setFixedHeight(min(total_height, 300))
        
        main_layout.addWidget(table)

        # --- Bottom Section: Summary Cards ---
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(15)

        # Calculate Totals
        try:
            cargo_capacity = float(self.data['vehicle'].get('cargo_capacity', 1) or 1)
            emission_factor = float(self.data['vehicle'].get('emission_factor', 0) or 0)
            dist_val = float(distance or 0)
        except (ValueError, TypeError):
            cargo_capacity = 1.0
            emission_factor = 0.0
            dist_val = 0.0

        import math
        trips = math.ceil(total_qty / cargo_capacity) if cargo_capacity > 0 else 0
        total_emission = total_qty * dist_val * emission_factor

        # Card 1: Total Quantity
        self.add_summary_card(summary_layout, "TOTAL QUANTITY", f"{total_qty:.2f}", "", bg_color="#FFFFFF", text_color="#1A1A1A")

        # Card 2: Total Trips
        self.add_summary_card(summary_layout, "TOTAL TRIPS", f"{trips}", "calculated", bg_color="#FFFFFF", text_color="#1A1A1A", icon_info=True)

        # Card 3: Total Carbon Emission
        self.add_summary_card(summary_layout, "TOTAL CARBON EMISSION", f"{total_emission:.2f}", "kgCO₂e", bg_color="#1E202B", text_color="#FFFFFF")

        main_layout.addLayout(summary_layout)

    def add_summary_card(self, layout, title, value, unit_or_sub, bg_color, text_color, icon_info=False):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {bg_color}; border: 1px solid #E0E0E0; border-radius: 8px;")
        
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(15, 15, 15, 15)
        fl.setSpacing(5)
        
        # Header Row
        header_row = QHBoxLayout()
        lbl_title = QLabel(title)
        
        title_color = "#757575" if bg_color == "#FFFFFF" else "#B0BEC5" 
        lbl_title.setStyleSheet(f"color: {title_color}; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; border: none;")
        
        header_row.addWidget(lbl_title)
        if icon_info:
            lbl_info = QLabel("ⓘ") 
            lbl_info.setStyleSheet(f"color: {title_color}; font-size: 12px; border: none;")
            header_row.addStretch()
            header_row.addWidget(lbl_info)
        else:
             header_row.addStretch()

        fl.addLayout(header_row)
        
        # Value Row
        val_row = QHBoxLayout()
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {text_color}; font-size: 20px; font-weight: bold; border: none;")
        
        val_row.addWidget(lbl_val)
        
        if unit_or_sub:
            lbl_unit = QLabel(unit_or_sub)
            if unit_or_sub == "calculated":
                 lbl_unit.setStyleSheet("color: #9E9E9E; font-size: 12px; margin-left: 5px; border: none;")
            else:
                 lbl_unit.setStyleSheet(f"color: {text_color}; font-size: 14px; margin-left: 2px; margin-top: 4px; border: none;")
            val_row.addWidget(lbl_unit)
            
        val_row.addStretch()
        fl.addLayout(val_row)
        
        layout.addWidget(frame)


class TransportationFormDialog(QDialog):
    def __init__(self, used_materials=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Transportation Data")
        self.setFixedWidth(600)
        self.vehicle_data = {} 
        self.material_checkboxes = {} 
        self.used_materials = used_materials if used_materials else set()
        self.init_ui()

    def get_db_path(self):
        # Calculate path to temp_file_db/temporary_construction_data.json
        # Current file: .../widgets/carbon_emission_data/Transportation_data.py
        # DB: .../desktop_app/temp_file_db/temporary_construction_data.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up 2 levels: widgets -> desktop_app
        desktop_app_dir = os.path.dirname(os.path.dirname(current_dir))
        db_path = os.path.join(desktop_app_dir, "temp_file_db", "temporary_construction_data.json")
        return db_path

    def open_vehicle_details(self):
        dialog = VehicleDetailsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.vehicle_data = dialog.get_data()
            self.btn_veh_details.setText(f"Vehicle: {self.vehicle_data.get('name', 'Selected')}")
            self.btn_veh_details.setStyleSheet("background-color: #E8F5E9; border: 1px solid #285A23; color: #285A23;")

    def populate_materials(self):
        db_path = self.get_db_path()
        print(f"[DEBUG] DB Path: {db_path}")
        
        if not os.path.exists(db_path):
            no_data_label = QLabel("No materials found. Please upload data via Excel.")
            no_data_label.setStyleSheet("color: #808080 ")
            self.materials_grid.addWidget(no_data_label, 0, 0)
            return

        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract materials with full data
            self.loaded_materials = {} # Name -> Item Dict
            for section in data:
                items = section.get('data', [])
                for item in items:
                    name = item.get('name')
                    if name:
                        self.loaded_materials[name] = item
            
            sorted_names = sorted(list(self.loaded_materials.keys()))

            # Clear existing
            while self.materials_grid.count():
                item = self.materials_grid.takeAt(0)
                widget = item.widget()
                if widget: widget.deleteLater()

            if not sorted_names:
                no_data_label = QLabel("No materials found in the uploaded file.")
                no_data_label.setStyleSheet("color: #808080; font-style: italic;")
                self.materials_grid.addWidget(no_data_label, 0, 0)
                return

            row = 0
            col = 0
            max_cols = 1
            
            for name in sorted_names:
                checkbox = QCheckBox(name)
                
                # Check if material is already used
                is_locked = name in self.used_materials
                
                if is_locked:
                    checkbox.setChecked(True)
                    checkbox.setEnabled(False)
                    checkbox.setToolTip("This material has already been added to a group.")
                    # Locked Style: Grey text, standard disabled checkbox
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            font-size: 14px;
                            color: #A0A0A0; 
                            padding: 5px;
                        }
                    """)
                else:
                    # Normal Style: Standard checkbox
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            font-size: 14px;
                            color: #3F3E5E;
                            padding: 5px;
                        }
                    """)
                
                self.materials_grid.addWidget(checkbox, row, col)
                self.material_checkboxes[name] = checkbox # Store reference
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        except Exception as e:
            print(f"Error loading materials: {e}")
            error_label = QLabel(f"Error loading materials: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.materials_grid.addWidget(error_label, 0, 0)
    
    def get_data(self):
        # Collect selected materials
        selected_materials = []
        for name, checkbox in self.material_checkboxes.items():
            if checkbox.isChecked():
                # Get the full item data
                item_data = self.loaded_materials.get(name, {})
                selected_materials.append(item_data)
        
        return {
            "source": self.source_input.text(),
            "destination": self.dest_input.text(),
            "distance": self.dist_travelled.text(),
            "vehicle": self.vehicle_data,
            "materials": selected_materials
        }

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        self.setStyleSheet("""
            QDialog { background-color: #FFF9F9; }
            QLabel { font-size: 14px; color: #3F3E5E; font-weight: bold; }
            QLineEdit { border: 1px solid #DDDCE0; border-radius: 10px; padding: 6px; background-color: white; }
            QPushButton { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; font-weight: bold; }
        """)
        
        title = QLabel("Add Transportation Data")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("font-size: 18px; text-decoration: underline; margin-bottom: 20px; color: #3F3E5E;")
        layout.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea { background-color: transparent; }
            QScrollBar:vertical { border: none; background: #FFFFFF; width: 10px; margin: 0px; border-radius: 0px; }
            QScrollBar::handle:vertical { background-color: #E0E0E0; min-height: 20px; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        # Src/Dest Row
        src_dest_row=QHBoxLayout()
        self.source_input = QLineEdit()
        self.dest_input = QLineEdit()
        src_container=QWidget(); src_layout=QVBoxLayout(src_container); src_layout.setContentsMargins(0,0,0,0); src_layout.setSpacing(5)
        src_layout.addWidget(QLabel("Src")); src_layout.addWidget(self.source_input)
        
        dest_container=QWidget(); dest_layout=QVBoxLayout(dest_container); dest_layout.setContentsMargins(0,0,0,0); dest_layout.setSpacing(5)
        dest_layout.addWidget(QLabel("Dest")); dest_layout.addWidget(self.dest_input)

        src_dest_row.addWidget(src_container); src_dest_row.addWidget(dest_container)
        content_layout.addLayout(src_dest_row)

        # Vehicle Button
        self.btn_veh_details = QPushButton("+ Add Vehicle Details")
        self.btn_veh_details.setCursor(Qt.PointingHandCursor)
        self.btn_veh_details.setFixedWidth(170)
        self.btn_veh_details.clicked.connect(self.open_vehicle_details)
        content_layout.addWidget(self.btn_veh_details)

        # Distance
        content_layout.addWidget(QLabel("Dist Travelled(km)"))
        self.dist_travelled = QLineEdit()
        self.dist_travelled.setValidator(QDoubleValidator())
        self.dist_travelled.setFixedWidth(200)
        content_layout.addWidget(self.dist_travelled)
        
        # Materials Header
        content_layout.addWidget(QLabel("Materials"))
        
        # Materials Grid Container
        self.materials_list_widget = QWidget()
        self.materials_list_widget.setStyleSheet("background-color: transparent;")
        self.materials_grid = QGridLayout(self.materials_list_widget)
        self.materials_grid.setContentsMargins(0, 0, 0, 0)
        self.materials_grid.setSpacing(15)
        content_layout.addWidget(self.materials_list_widget)
        
        self.populate_materials()

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Group")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)


class TransportationMainWidget(QWidget):
    def __init__(self, database=None, parent=None):
        qt_parent = parent if isinstance(parent, QWidget) else None
        super().__init__(qt_parent)
        self.database = database
        self.parent_controller = parent
        print("[DEBUG] TransportationMainWidget initializing...")
        try:
            self.init_ui()
            print("[DEBUG] TransportationMainWidget initialized successfully.")
        except Exception as e:
            print(f"[ERROR] TransportationMainWidget init_ui failed: {e}")
            import traceback
            traceback.print_exc()

    def init_ui(self):
        # Main Layout (Fixed Page)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main Container (Fixed Page Background)
        self.container = QFrame()
        self.container.setObjectName("MainPanel")
        self.container.setStyleSheet("""
            QFrame#MainPanel {
                background-color: #FFF9F9;
                border: 1px solid #000000;
                border-radius: 0px;
            }
             QLabel {
                font-size: 14px;
                color: #3F3E5E;
                font-weight: bold;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(15)
        container_layout.setContentsMargins(40, 30, 40, 40)

        # 1. FIXED TITLE
        title = QLabel("Transportation Carbon Emission Data")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; text-decoration: none; margin-bottom: 20px; color: #3F3E5E;")
        container_layout.addWidget(title)
        
        # 2. SCROLLABLE CONTENT AREA
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #FFFFFF;
                width: 10px;
                margin: 0px;
                border-radius: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #E0E0E0;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        
        # Layout for the scrollable content (where cards go)
        self.data_rows_layout = QVBoxLayout(self.scroll_content)
        self.data_rows_layout.setContentsMargins(0, 0, 0, 0) # Tight margins inside scroll
        self.data_rows_layout.setSpacing(15)
        self.data_rows_layout.addStretch() # Push items up

        self.scroll_area.setWidget(self.scroll_content)
        container_layout.addWidget(self.scroll_area)

        # 3. FIXED BUTTON AT BOTTOM
        self.btn_add_group = QPushButton("Add emission Group")
        self.btn_add_group.setCursor(Qt.PointingHandCursor)
        self.btn_add_group.setFixedWidth(150)
        self.btn_add_group.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #3F3E5E;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F8F8F8;
                border-color: #C0C0C0;
            }
        """)
        self.btn_add_group.clicked.connect(self.open_add_emission_group_dialog)
        container_layout.addWidget(self.btn_add_group, alignment=Qt.AlignCenter)
        
        main_layout.addWidget(self.container)

        self.used_materials_set = set() # Track used materials

    def open_add_emission_group_dialog(self):
        # Pass the set of already used materials
        dialog = TransportationFormDialog(used_materials=self.used_materials_set, parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.add_group_card(data)

    def add_group_card(self, data):
        # Add new materials to the set
        if 'materials' in data:
            for item in data['materials']:
                name = item.get('name')
                if name:
                    self.used_materials_set.add(name)

        card = TransportationGroupCard(data)
        # Insert before the stretch (last item)
        count = self.data_rows_layout.count()
        if count > 0:
             self.data_rows_layout.insertWidget(count - 1, card)
        else:
             self.data_rows_layout.addWidget(card)



