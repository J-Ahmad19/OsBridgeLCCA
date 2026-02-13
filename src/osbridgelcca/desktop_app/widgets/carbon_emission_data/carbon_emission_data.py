from PySide6.QtWidgets import (QApplication, QMainWindow, QScrollArea, QVBoxLayout, QWidget, QLabel, 
                               QGridLayout, QLineEdit, QComboBox, QPushButton, QFrame, QHBoxLayout, 
                               QSpacerItem, QSizePolicy, QDialog, QFormLayout, QDialogButtonBox, QToolTip)
from PySide6.QtGui import QDoubleValidator, QCursor, QIcon
from PySide6.QtCore import Qt, Signal, QEvent, QObject, QSize
import sys
import json
import os
import glob
import pprint
from osbridgelcca.desktop_app.widgets.utils.data import *
from osbridgelcca.desktop_app.resources.resources_rc import *

# CONSTANTS - Column Widths
COL_WIDTH_TYPE = 200
COL_WIDTH_QTY = 80
COL_WIDTH_UNIT = 120
COL_WIDTH_VALUE = 80
COL_WIDTH_EMISSION = 120
COL_WIDTH_SOURCE = 110
COL_WIDTH_ACTION = 160 
COL_WIDTH_TOTAL = 100
COL_WIDTH_SPACER = 40
INPUT_HEIGHT = 32

# Keys for the Collected Data (Output)
KEY_TYPE = "type"
KEY_QUANTITY = "quantity"
KEY_EMISSION_FACTOR = "carbon_emission"
KEY_UNIT = "carbon_emission_units"
KEY_CONVERSION = "conversion_factor"
KEY_SOURCE = "carbon_emission_src"
KEY_SECTION = "section"

from PySide6.QtCore import QTimer

class DelayedTooltipFilter(QObject):
    def __init__(self, delay=500, parent=None):
        super().__init__(parent)
        self.delay = delay
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.show_tooltip)
        self.widget = None
        self.pos = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.widget = obj
            self.pos = QCursor.pos()
            self.timer.start(self.delay)
        elif event.type() == QEvent.Leave:
            self.timer.stop()
            self.widget = None
        elif event.type() == QEvent.MouseButtonPress:
            self.timer.stop()
            # Optional: Hide tooltip on click if it's showing?
            QToolTip.hideText()
        return super().eventFilter(obj, event)

    def show_tooltip(self):
        if self.widget and self.widget.underMouse():
            QToolTip.showText(QCursor.pos(), self.widget.toolTip(), self.widget)

class InstantTooltipFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            QToolTip.showText(QCursor.pos(), obj.toolTip(), obj)
        return super().eventFilter(obj, event)

class EditMaterialDialog(QDialog):
    """
    A popup window for editing material details.
    """
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Material Details")
        self.setModal(True)
        self.setFixedWidth(400) # Set a reasonable width for the popup
        self.data = data
        self.inputs = {}
        self.tooltip_filter = InstantTooltipFilter(self)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form Layout for neat Label -> Input pairing
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Map display labels to data keys
        fields = [
            ("Type of Material", "name"),
            ("Quantity", "quantity"),
            ("Carbon Emission Factor", "carbon_emission"),
            ("Carbon Units", "carbon_emission_units"),
            ("Conversion Factor", "conversion_factor"),
            ("Carbon Emission Source", "carbon_emission_src")
        ]

        # 1. Validator for Quantity & Carbon Emission (Allows any float >= 0)
        general_validator = QDoubleValidator()
        general_validator.setBottom(0.0) 
        general_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        # 2. Validator for Conversion Factor (Must be > 0, so we set a small epsilon)
        #    Note: QDoubleValidator.setBottom(0.0) includes 0, so to enforce >0 strictly via validator is tricky.
        #    Usually we just set bottom 0.000001 or check on save. 
        #    The user specifically asked "greater than zero".
        conv_validator = QDoubleValidator()
        conv_validator.setBottom(0.000001)
        conv_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        for label, key in fields:
            le = QLineEdit(str(self.data.get(key, "")))
            le.setPlaceholderText(f"Enter {label}")
            le.setToolTip(str(self.data.get(key, ""))) # Tooltip showing current value
            le.installEventFilter(self.tooltip_filter)
            
            # Apply Validators
            if key in ["quantity", "carbon_emission"]:
                le.setValidator(general_validator)
            elif key == "conversion_factor":
                le.setValidator(conv_validator)
                
            form_layout.addRow(QLabel(f"{label}:"), le)
            self.inputs[key] = le

        layout.addLayout(form_layout)

        # Apply ToolTip Style to Dialog as well
        self.setStyleSheet("""
            QToolTip {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
        """)

        # Save and Cancel Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept) # Closes dialog with ResultCode.Accepted
        button_box.rejected.connect(self.reject) # Closes dialog with ResultCode.Rejected
        
        layout.addWidget(button_box)

    def get_data(self):
        """Retrieve the modified data from inputs."""
        return {key: le.text() for key, le in self.inputs.items()}


class MaterialSectionWidget(QWidget):
    """
    Represents ONE section (Included OR Excluded).
    """
    item_moved = Signal(dict)

    def __init__(self, title, data=None, section_type="included", parent=None):
        super().__init__(parent)
        self.section_title = title
        self.section_type = section_type.lower() 
        self.data = data if data else []
        
        self.widgets = [] 
        self.current_material_row_idx = 1
        self.tooltip_filter = InstantTooltipFilter(self)
        self.delayed_tooltip_filter = DelayedTooltipFilter(delay=1200, parent=self)
        
        self.init_ui()

    def style_input(self, widget, width):
        widget.setFixedWidth(width)
        widget.setFixedHeight(INPUT_HEIGHT)
        widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 10, 0, 20)
        self.layout.setSpacing(10)

        # 1. Title
        title_label = QLabel(self.section_title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #3F3E5E; margin-bottom: 5px;")
        self.layout.addWidget(title_label)

        # 2. Grid Layout
        self.material_grid_layout = QGridLayout()
        self.material_grid_layout.setHorizontalSpacing(10)
        self.material_grid_layout.setVerticalSpacing(12)
        self.material_grid_layout.setContentsMargins(0, 0, 0, 0)

        # Headers
        headers = [
            "Type of Material", 
            "Quantity", 
            "Carbon Emission Factor", 
            "Carbon Units", 
            "Conv Factor", 
            "Carbon Emission Source",
            "Total",
            "",
            "Actions"
        ]
        
        for col, header_text in enumerate(headers):
            label = QLabel(header_text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #555; font-size: 12px;") 
            self.material_grid_layout.addWidget(label, 0, col, alignment=Qt.AlignCenter)

        self.layout.addLayout(self.material_grid_layout)

        # 3. Existing Data Loading
        if self.data:
            for item in self.data:
                self.add_material_row(item)
        
        # 4. Add Button - Removed per user request
        # self.add_material_button.clicked.connect(lambda: self.add_material_row(None))
        # self.layout.addSpacing(5)
        # self.layout.addWidget(self.add_material_button, alignment=Qt.AlignCenter)

    def add_material_row(self, item=None):
        row_idx = self.current_material_row_idx
        row_widgets = []

        # Helper to create styled inputs - ALWAYS READ ONLY in the grid
        def create_input(text, width, align=Qt.AlignLeft):
            le = QLineEdit()
            le.setText(str(text))
            le.setToolTip(str(text))
            le.installEventFilter(self.tooltip_filter)
            le.setReadOnly(True) # Enforce ReadOnly so users must use the Edit button
            le.setStyleSheet("color: #333; background-color: #F9F9F9;") 
            le.setAlignment(align)
            le.setCursorPosition(0) # Ensure start is visible for long text
            self.style_input(le, width)
            return le

        # Extract data safely
        name_val = item.get("name", "") if item else ""
        qty_val = item.get("quantity", "") if item else ""
        ce_val = item.get("carbon_emission", "") if item else ""
        unit_val = item.get("carbon_emission_units", "") if item else ""
        conv_val = item.get("conversion_factor", "") if item else ""
        src_val = item.get("carbon_emission_src", "") if item else ""
        
        # --- Columns 1-6 ---
        w_type = create_input(name_val, COL_WIDTH_TYPE, Qt.AlignLeft)
        self.material_grid_layout.addWidget(w_type, row_idx, 0)
        row_widgets.append(w_type)

        w_qty = create_input(qty_val, COL_WIDTH_QTY, Qt.AlignRight)
        self.material_grid_layout.addWidget(w_qty, row_idx, 1)
        row_widgets.append(w_qty)

        w_emit = create_input(ce_val, COL_WIDTH_EMISSION, Qt.AlignRight)
        self.material_grid_layout.addWidget(w_emit, row_idx, 2)
        row_widgets.append(w_emit)

        w_unit = create_input(unit_val, COL_WIDTH_UNIT, Qt.AlignLeft)
        self.material_grid_layout.addWidget(w_unit, row_idx, 3)
        row_widgets.append(w_unit)

        w_conv = create_input(conv_val, COL_WIDTH_VALUE, Qt.AlignRight)
        self.material_grid_layout.addWidget(w_conv, row_idx, 4)
        row_widgets.append(w_conv)

        w_src = create_input(src_val, COL_WIDTH_SOURCE, Qt.AlignLeft)
        self.material_grid_layout.addWidget(w_src, row_idx, 5)
        row_widgets.append(w_src)

        # --- Column 6: TOTAL (Calculated) ---
        try:
            val_qty = float(qty_val) if qty_val else 0.0
            val_ce = float(ce_val) if ce_val else 0.0
            val_conv = float(conv_val) if conv_val else 0.0
            total_val = val_qty * val_ce * val_conv
            # Format to 2 decimal places? Or just string? Let's do string for now, maybe 2 decimals is better but user didn't specify.
            # Usually strict float behavior is better.
            total_str = f"{total_val:.2f}"
        except ValueError:
            total_str = "0.00"

        w_total = create_input(total_str, COL_WIDTH_TOTAL, Qt.AlignRight)
        # It's read-only by default from create_input, which is good.
        self.material_grid_layout.addWidget(w_total, row_idx, 6)
        row_widgets.append(w_total)

        # --- Column 7: SPACER ---
        spacer = QWidget()
        spacer.setFixedWidth(COL_WIDTH_SPACER)
        self.material_grid_layout.addWidget(spacer, row_idx, 7)
        row_widgets.append(spacer)

        # --- Column 8: ACTIONS ---
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)

        # EDIT Button (Blue)
        
        current_dir = os.path.dirname(__file__)
        widgets_dir = os.path.dirname(current_dir)
        desktop_app_dir = os.path.dirname(widgets_dir)
        icon_path = os.path.join(desktop_app_dir, 'resources', 'images', 'e1.png')

        btn_edit = QPushButton()
        if os.path.exists(icon_path):
            btn_edit.setIcon(QIcon(icon_path))
        else:
            # Fallback or debug print if needed, but for now just try to load
             btn_edit.setIcon(QIcon(":/images/e1.png"))

        btn_edit.setIconSize(QSize(24, 24))
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.setFixedWidth(40)
        btn_edit.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: transparent; }
        """)
        # Change connection to open popup
        # Note: We must pass row_widgets carefully. row_widgets[0] to [5] are inputs. [6] is spacer.
        # open_edit_dialog expects row_widgets to match indices 0-5. 
        # Current implementation of open_edit_dialog uses indices 0-5. 
        # We should check open_edit_dialog implementation.
        btn_edit.clicked.connect(lambda: self.open_edit_dialog(row_widgets))
        
        # Tooltip for Edit
        btn_edit.setToolTip("Edit")
        btn_edit.installEventFilter(self.delayed_tooltip_filter)
        
        action_layout.addWidget(btn_edit)

        # MOVE Button (Include/Exclude)
        btn_move = QPushButton()
        if self.section_type == "included":
            # "Exclude" button -> Down Icon
            icon_file = "down2.png"
            tooltip_text = "Exclude"
        else:
            # "Include" button -> Up Icon
            icon_file = "up.png"
            tooltip_text = "Include"

        move_icon_path = os.path.join(desktop_app_dir, 'resources', 'images', icon_file)
        if os.path.exists(move_icon_path):
            btn_move.setIcon(QIcon(move_icon_path))
        else:
            print(f"Icon not found: {move_icon_path}")

        btn_move.setToolTip(tooltip_text)
        btn_move.installEventFilter(self.delayed_tooltip_filter)

        btn_move.setIconSize(QSize(24, 24))
        btn_move.setCursor(Qt.PointingHandCursor)
        btn_move.setFixedWidth(30) # Match edit button width or similar
        btn_move.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: transparent; }
        """)
        
        btn_move.clicked.connect(lambda: self.handle_move_click(row_widgets))
        action_layout.addWidget(btn_move)
        
        self.material_grid_layout.addWidget(action_widget, row_idx, 8, alignment=Qt.AlignCenter)
        row_widgets.append(action_widget) 

        self.widgets.append(row_widgets)
        self.current_material_row_idx += 1

    def is_valid_row(self, data):
        """Checks if the numeric fields contain valid numbers."""
        try:
            float(data.get("quantity", 0))
            float(data.get("carbon_emission", 0))
            float(data.get("conversion_factor", 0))
            return True
        except ValueError:
            return False

    def open_edit_dialog(self, row_widgets):
        """
        Opens a popup dialog to edit the row's data.
        """
        # 1. Scrape current data from the row
        current_data = {
            "name": row_widgets[0].text(),
            "quantity": row_widgets[1].text(),
            "carbon_emission": row_widgets[2].text(),
            "carbon_emission_units": row_widgets[3].text(),
            "conversion_factor": row_widgets[4].text(),
            "carbon_emission_src": row_widgets[5].text(),
        }

        # 2. Create and Open Dialog
        dialog = EditMaterialDialog(current_data, self)
        
        # 3. Check if user clicked Save (Accepted)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            
            # 4. Update the Row Widgets with new data
            row_widgets[0].setText(new_data["name"])
            row_widgets[1].setText(new_data["quantity"])
            row_widgets[2].setText(new_data["carbon_emission"])
            row_widgets[3].setText(new_data["carbon_emission_units"])
            row_widgets[4].setText(new_data["conversion_factor"])
            row_widgets[5].setText(new_data["carbon_emission_src"])
            
            # Update Total
            try:
                q = float(new_data["quantity"]) if new_data["quantity"] else 0.0
                c = float(new_data["carbon_emission"]) if new_data["carbon_emission"] else 0.0
                cf = float(new_data["conversion_factor"]) if new_data["conversion_factor"] else 0.0
                tot = q * c * cf
                row_widgets[6].setText(f"{tot:.2f}")
            except ValueError:
                row_widgets[6].setText("0.00")

            # 5. VALIDATION CHECK
            # If we are in "Included" section and data is invalid (non-numeric), move to Excluded.
            if self.section_type == "included":
                if not self.is_valid_row(new_data):
                    print(f"Validation failed for {new_data['name']}. Moving to Excluded.")
                    self.handle_move_click(row_widgets)

    def handle_move_click(self, row_widgets):
        """
        Removes the row from THIS section and emits a signal.
        """
        data = {
            "name": row_widgets[0].text(),
            "quantity": row_widgets[1].text(),
            "carbon_emission": row_widgets[2].text(),
            "carbon_emission_units": row_widgets[3].text(),
            "conversion_factor": row_widgets[4].text(),
            "carbon_emission_src": row_widgets[5].text(),
        }

        for w in row_widgets:
            self.material_grid_layout.removeWidget(w)
            w.deleteLater() 
        
        if row_widgets in self.widgets:
            self.widgets.remove(row_widgets)

        self.item_moved.emit(data)

    def collect_data(self):
        p = []
        for row in self.widgets:
            data = {
                KEY_TYPE: row[0].text(),
                KEY_QUANTITY: row[1].text(),
                KEY_EMISSION_FACTOR: row[2].text(),
                KEY_UNIT: row[3].text(),
                KEY_CONVERSION: row[4].text(),
                KEY_SOURCE: row[5].text(),
                KEY_SECTION: self.section_title 
            }
            p.append(data)
        return p


class ComponentWidget(QWidget):
    def __init__(self, included_data, excluded_data, parent=None):
        super().__init__(parent)
        self.included_data = included_data
        self.excluded_data = excluded_data
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.included_section = MaterialSectionWidget("Included", data=self.included_data, section_type="included")
        self.main_layout.addWidget(self.included_section)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0;")
        self.main_layout.addWidget(line)

        self.excluded_section = MaterialSectionWidget("Excluded", data=self.excluded_data, section_type="excluded")
        self.main_layout.addWidget(self.excluded_section)
        
        self.included_section.item_moved.connect(self.excluded_section.add_material_row)
        self.excluded_section.item_moved.connect(self.included_section.add_material_row)

    def collect_data(self):
        return self.included_section.collect_data() + self.excluded_section.collect_data()


class CarbonEmissionData(QWidget):
    closed = Signal()
    next = Signal(str)
    back = Signal(str)
    
    def __init__(self, database, parent=None):
        super().__init__()
        self.database_manager = database
        self.component_widgets = []
        
        self.included_data, self.excluded_data = self.load_temp_data()

        self.setStyleSheet("""
            #scroll_wrapper { background-color: #F8F8F8; }
            #content_card {
                background-color: #FFF9F9;
                border: 1px solid #000000;
                border-radius: 0px;
            }
            QScrollArea { background-color: transparent; border: none; }
            QLineEdit, QComboBox {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
                background-color: white;
            }
            QPushButton#add_material_button {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #3F3E5E;
                padding: 6px 15px;
            }
            QPushButton#add_material_button:hover { background-color: #F8F8F8; border-color: #C0C0C0; }
            QPushButton#nav_button {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #3F3E5E;
                padding: 6px 15px;
                min-width: 80px;
            }
            QPushButton#nav_button:hover {
                background-color: #F8F8F8;
                border-color: #C0C0C0;
            }
            QToolTip {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
        """)

        self.init_ui()

    def load_temp_data(self):
        included = []
        excluded = []
        
        current_dir = os.path.dirname(__file__) 
        parent_dir = os.path.dirname(current_dir) 
        parent_dir = os.path.dirname(parent_dir) 
        folder_name = os.path.join(parent_dir, 'temp_file_db')
        
        raw_data = []

        if os.path.exists(folder_name):
            list_of_files = glob.glob(os.path.join(folder_name, '*.json'))
            if list_of_files:
                latest_file = max(list_of_files, key=os.path.getctime)
                try:
                    with open(latest_file, 'r') as f:
                        raw_data = json.load(f)
                    print(f"Loaded data from: {latest_file}")
                except Exception as e:
                    print(f"Error reading file: {e}")
            else:
                print(f"No JSON files found in {folder_name}")
        else:
            print(f"Folder '{folder_name}' not found.")

        if isinstance(raw_data, list):
            for group_obj in raw_data:
                items_list = group_obj.get("data", [])
                
                for item in items_list:
                    c_emit = str(item.get("carbon_emission", "")).lower()
                    c_units = str(item.get("carbon_emission_units", "")).lower()
                    c_conv = str(item.get("conversion_factor", "")).lower()
                    c_src = str(item.get("carbon_emission_src", "")).lower()
                    
                    invalid_values = ["not_available", "n/a", "none", ""]
                    
                    is_excluded = (c_emit in invalid_values) or \
                                  (c_units in invalid_values) or \
                                  (c_conv in invalid_values) or \
                                  (c_src in invalid_values)
                    
                    if is_excluded:
                        excluded.append(item)
                    else:
                        included.append(item)
                        
        return included, excluded

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)

        self.scroll_wrapper = QWidget()
        self.scroll_wrapper.setObjectName("scroll_wrapper")
        self.scroll_area.setWidget(self.scroll_wrapper)
        
        self.wrapper_layout = QVBoxLayout(self.scroll_wrapper)
        self.wrapper_layout.setContentsMargins(20, 20, 20, 20)
        self.wrapper_layout.setSpacing(20)

        self.content_card = QWidget()
        self.content_card.setObjectName("content_card")
        self.content_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum) 
        
        self.card_layout = QVBoxLayout(self.content_card)
        self.card_layout.setContentsMargins(15, 15, 15, 15)
        self.card_layout.setSpacing(15)

        self.add_component_layout()

        self.button_h_layout = QHBoxLayout()
        self.button_h_layout.setSpacing(10)
        self.button_h_layout.addStretch()

        back_button = QPushButton("Back")
        back_button.setObjectName("nav_button")
        back_button.clicked.connect(lambda: self.back.emit(KEY_CARBON_EMISSION))
        self.button_h_layout.addWidget(back_button)

        next_button = QPushButton("Next")
        next_button.setObjectName("nav_button")
        next_button.clicked.connect(self.collect_data)
        self.button_h_layout.addWidget(next_button)

        self.card_layout.addLayout(self.button_h_layout)
        self.wrapper_layout.addWidget(self.content_card)
        self.wrapper_layout.addStretch()

    def add_component_layout(self):
        new_component = ComponentWidget(
            included_data=self.included_data, 
            excluded_data=self.excluded_data, 
            parent=self
        )
        self.component_widgets.append(new_component)
        self.card_layout.insertWidget(0, new_component)

    def collect_data(self):
        data = self.component_widgets[0].collect_data()
        print("\nCollected Data:")
        pprint.pprint(data)


