from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, 
    QSizePolicy, QLineEdit, QGridLayout, QFrame, QDialog, QFormLayout, 
    QDialogButtonBox, QToolTip
)
from PySide6.QtGui import QIntValidator, QDoubleValidator, QCursor, QIcon
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QSize, QTimer
import os
import glob
import json
from osbridgelcca.desktop_app.widgets.utils.data import KEY_RECYCLABLE

INPUT_HEIGHT = 32

class DelayedTooltipFilter(QObject):
    def __init__(self, delay=1200, parent=None):
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

class EditRecyclableDialog(QDialog):
    """
    A popup window for editing recyclable material details.
    """
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Recyclable Details")
        self.setModal(True)
        self.setFixedWidth(400)
        self.data = data
        self.inputs = {}
        self.tooltip_filter = InstantTooltipFilter(self)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form Layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Fields mapping
        fields = [
            ("Type of Material", "name"),
            ("Quantity", "quantity"),
            ("% Recyclability", "recyclability_percentage"),
            ("Scrap Rate", "scrap_rate")
        ]

        # Validators
        qty_validator = QIntValidator()
        qty_validator.setBottom(1)

        percent_validator = QDoubleValidator()
        percent_validator.setBottom(0.0)
        percent_validator.setTop(100.0)
        percent_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        rate_validator = QDoubleValidator()
        rate_validator.setBottom(0.0)
        rate_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        for label, key in fields:
            val_str = str(self.data.get(key, ""))
            le = QLineEdit(val_str)
            le.setPlaceholderText(f"Enter {label}")
            le.setToolTip(val_str)
            le.installEventFilter(self.tooltip_filter)
            
            if key == "quantity":
                le.setValidator(qty_validator)
            elif key == "recyclability_percentage":
                le.setValidator(percent_validator)
            elif key == "scrap_rate":
                le.setValidator(rate_validator)
                
            form_layout.addRow(QLabel(f"{label}:"), le)
            self.inputs[key] = le

        layout.addLayout(form_layout)

        # Tooltip Style
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

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)

    def get_data(self):
        return {key: le.text() for key, le in self.inputs.items()}


class RecyclableSectionWidget(QWidget):
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
        self.current_row_idx = 1
        self.tooltip_filter = InstantTooltipFilter(self)
        self.delayed_tooltip_filter = DelayedTooltipFilter(delay=1200, parent=self)
        
        self.init_ui()

    def style_input(self, widget, width=None):
        # Removed fixed width to allow expansion
        widget.setFixedHeight(INPUT_HEIGHT)
        # widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) # Allow horizontal expansion


    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 10, 0, 20)
        self.layout.setSpacing(10)

        # Title
        title_label = QLabel(self.section_title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #3F3E5E; margin-bottom: 5px;")
        self.layout.addWidget(title_label)

        # Grid
        self.grid_layout = QGridLayout()
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(12)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Headers
        headers = [
            "Type of Material", 
            "Quantity", 
            "% Recyclability", 
            "Scrap Rate",
            "Actions"
        ]
        
        for col, header_text in enumerate(headers):
            label = QLabel(header_text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #555; font-size: 12px;") 
            self.grid_layout.addWidget(label, 0, col, alignment=Qt.AlignCenter)
            self.grid_layout.setColumnStretch(col, 1) # Make all columns stretch equally

        self.layout.addLayout(self.grid_layout)

        # Load Data
        if self.data:
            for item in self.data:
                self.add_row(item)

    def add_row(self, item=None):
        row_idx = self.current_row_idx
        row_widgets = []

        def create_input(text, width=None, align=Qt.AlignLeft):
            le = QLineEdit()
            text_str = str(text) if text is not None else ""
            le.setText(text_str)
            le.setToolTip(text_str)
            # le.installEventFilter(self.tooltip_filter) # Use delayed or keep instant for fields? User request said "same delay for tooltip", likely for buttons
            # But let's apply delayed to fields too if inconsistent? 
            # Request says "for respective button", implied fields might not change? 
            # I will keep FIELDS as is (using self.tooltip_filter which is InstantTooltipFilter initiated in __init__ - wait, I need to check __init__ if I removed it)
            # Checked above: I only added delayed_tooltip_filter, didn't remove existing tooltip_filter.
            # Wait, in the ReplacementContent for __init__, I replaced the WHOLE __init__.
            # The original code had `self.tooltip_filter = InstantTooltipFilter(self)`.
            # I should keep it for inputs if not requested to change, or change inputs to delayed too?
            # "implement tooltips for all input fields... ensure they appear instantly" was a previous request (Conversation 28a0f8ed).
            # Current request: "in place of button... use same icons... and for respective button and same delay for tool tip".
            # This implies BUTTONS strictly.
            # So I will re-add `self.tooltip_filter = InstantTooltipFilter(self)` in __init__ in the replacement block to be safe.
            le.installEventFilter(self.tooltip_filter) 
            le.setReadOnly(True) 
            le.setStyleSheet("color: #333; background-color: #F9F9F9;") 
            le.setAlignment(align)
            le.setCursorPosition(0) 
            self.style_input(le) 
            return le

        # Data extraction
        name_val = item.get("name", "") if item else ""
        qty_val = item.get("quantity", "") if item else ""
        perc_val = item.get("recyclability_percentage", "") if item else ""
        rate_val = item.get("scrap_rate", "") if item else ""

        # Columns
        # 1. Type (Left)
        w_name = create_input(name_val, align=Qt.AlignLeft)
        self.grid_layout.addWidget(w_name, row_idx, 0)
        row_widgets.append(w_name)

        # 2. Quantity (Right)
        w_qty = create_input(qty_val, align=Qt.AlignRight)
        self.grid_layout.addWidget(w_qty, row_idx, 1)
        row_widgets.append(w_qty)

        # 3. % Recyclability (Right)
        w_perc = create_input(perc_val, align=Qt.AlignRight)
        self.grid_layout.addWidget(w_perc, row_idx, 2)
        row_widgets.append(w_perc)

        # 4. Scrap Rate (Right)
        w_rate = create_input(rate_val, align=Qt.AlignRight)
        self.grid_layout.addWidget(w_rate, row_idx, 3)
        row_widgets.append(w_rate)

        # 5. Actions (Skipping spacer)
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)

        # Path Logic
        current_dir = os.path.dirname(os.path.abspath(__file__)) # .../widgets
        desktop_app_dir = os.path.dirname(current_dir) # .../desktop_app
        
        # EDIT Button (e1.png)
        btn_edit = QPushButton()
        edit_icon_path = os.path.join(desktop_app_dir, 'resources', 'images', 'e1.png')
        
        if os.path.exists(edit_icon_path):
            btn_edit.setIcon(QIcon(edit_icon_path))
        else:
             # Fallback if needed, but path should be correct
             btn_edit.setIcon(QIcon(":/images/edit_button.png")) # Original fallback

        btn_edit.setIconSize(QSize(24, 24))
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.setFixedWidth(30)
        btn_edit.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: transparent; }
        """)
        btn_edit.clicked.connect(lambda: self.open_edit_dialog(row_widgets))
        
        btn_edit.setToolTip("Edit")
        btn_edit.installEventFilter(self.delayed_tooltip_filter)
        
        action_layout.addWidget(btn_edit)

        # MOVE Button (Include/Exclude)
        btn_move = QPushButton()
        
        if self.section_type == "included":
            # "Exclude" button -> Down Icon (down2.png)
            icon_file = "down2.png"
            tooltip_text = "Exclude"
        else:
            # "Include" button -> Up Icon (up.png)
            icon_file = "up.png"
            tooltip_text = "Include"

        move_icon_path = os.path.join(desktop_app_dir, 'resources', 'images', icon_file)
        if os.path.exists(move_icon_path):
            btn_move.setIcon(QIcon(move_icon_path))
        else:
            print(f"Icon not found: {move_icon_path}")
            btn_move.setText(tooltip_text) # Fallback text

        btn_move.setToolTip(tooltip_text)
        btn_move.installEventFilter(self.delayed_tooltip_filter)

        btn_move.setIconSize(QSize(24, 24))
        btn_move.setCursor(Qt.PointingHandCursor)
        btn_move.setFixedWidth(40)
        btn_move.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: transparent; }
        """)
        
        btn_move.clicked.connect(lambda: self.handle_move_click(row_widgets))
        action_layout.addWidget(btn_move)
        
        self.grid_layout.addWidget(action_widget, row_idx, 4, alignment=Qt.AlignCenter)
        row_widgets.append(action_widget) 

        self.widgets.append(row_widgets)
        self.current_row_idx += 1

    def is_valid_row(self, data):
        """Checks if the required fields contain valid numbers."""
        try:
            # Check Quantity (Int > 0)
            q = int(data.get("quantity", 0))
            if q <= 0: return False
            
            # Check % (0 <= x <= 100)
            p_str = str(data.get("recyclability_percentage", "")).strip()
            if not p_str or p_str.lower() in ["none", "n/a", ""]: return False
            p = float(p_str)
            if p < 0 or p > 100: return False

            # Check Rate (>= 0)
            r_str = str(data.get("scrap_rate", "")).strip()
            if not r_str or r_str.lower() in ["none", "n/a", ""]: return False
            r = float(r_str)
            if r < 0: return False

            return True
        except ValueError:
            return False

    def open_edit_dialog(self, row_widgets):
        current_data = {
            "name": row_widgets[0].text(),
            "quantity": row_widgets[1].text(),
            "recyclability_percentage": row_widgets[2].text(),
            "scrap_rate": row_widgets[3].text(),
        }

        dialog = EditRecyclableDialog(current_data, self)
        
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            
            row_widgets[0].setText(new_data["name"])
            row_widgets[1].setText(new_data["quantity"])
            row_widgets[2].setText(new_data["recyclability_percentage"])
            row_widgets[3].setText(new_data["scrap_rate"])
            
            # Update tooltips
            row_widgets[0].setToolTip(new_data["name"])
            row_widgets[1].setToolTip(new_data["quantity"])
            row_widgets[2].setToolTip(new_data["recyclability_percentage"])
            row_widgets[3].setToolTip(new_data["scrap_rate"])
            
            # Auto-move if invalid in included
            if self.section_type == "included":
                if not self.is_valid_row(new_data):
                    self.handle_move_click(row_widgets)

    def handle_move_click(self, row_widgets):
        data = {
            "name": row_widgets[0].text(),
            "quantity": row_widgets[1].text(),
            "recyclability_percentage": row_widgets[2].text(),
            "scrap_rate": row_widgets[3].text(),
        }

        for w in row_widgets:
            self.grid_layout.removeWidget(w)
            w.deleteLater() 
        
        if row_widgets in self.widgets:
            self.widgets.remove(row_widgets)

        self.item_moved.emit(data)

    def collect_data(self):
        p = []
        for row in self.widgets:
            data = {
                "name": row[0].text(),
                "quantity": row[1].text(),
                "recyclability_percentage": row[2].text(),
                "scrap_rate": row[3].text(),
                "section": self.section_title 
            }
            p.append(data)
        return p


class RecyclableWidget(QWidget):
    closed = Signal()
    next = Signal(str)
    back = Signal(str)

    def __init__(self, database, parent=None):
        super().__init__()
        self.database_manager = database
        
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

        self.included_data, self.excluded_data = self.load_temp_data()
        self.init_ui()

    def load_temp_data(self):
        """Loads data from the latest JSON in temp_file_db and splits it."""
        included = []
        excluded = []
        
        current_dir = os.path.dirname(os.path.abspath(__file__)) 
        parent_dir = os.path.dirname(current_dir) # desktop_app
        folder_name = os.path.join(parent_dir, 'temp_file_db')
        
        raw_data = []

        if os.path.exists(folder_name):
            list_of_files = glob.glob(os.path.join(folder_name, '*.json'))
            if list_of_files:
                latest_file = max(list_of_files, key=os.path.getctime)
                try:
                    with open(latest_file, 'r') as f:
                        raw_data = json.load(f)
                    print(f"RecyclableWidget: Loaded data from {latest_file}")
                except Exception as e:
                    print(f"RecyclableWidget: Error reading file: {e}")
            else:
                print(f"RecyclableWidget: No JSON files found in {folder_name}")
        else:
            print(f"RecyclableWidget: Folder '{folder_name}' not found.")

        if isinstance(raw_data, list):
            for group_obj in raw_data:
                items_list = group_obj.get("data", [])
                for item in items_list:
                    # Filter logic
                    p = str(item.get("recyclability_percentage", "")).strip().lower()
                    r = str(item.get("scrap_rate", "")).strip().lower()
                    
                    invalid_values = ["not_available", "n/a", "none", "", "null"]
                    
                    is_excluded = False
                    if p in invalid_values or r in invalid_values:
                        is_excluded = True
                    else:
                        # Also check if they are valid numbers?
                        try:
                            float(p)
                            float(r)
                        except ValueError:
                            is_excluded = True

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

        # Included Section
        self.included_section = RecyclableSectionWidget("Included", data=self.included_data, section_type="included")
        self.card_layout.addWidget(self.included_section)

        # Line Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0;")
        self.card_layout.addWidget(line)

        # Excluded Section
        self.excluded_section = RecyclableSectionWidget("Excluded", data=self.excluded_data, section_type="excluded")
        self.card_layout.addWidget(self.excluded_section)
        
        # Connect Move Signals
        self.included_section.item_moved.connect(self.excluded_section.add_row)
        self.excluded_section.item_moved.connect(self.included_section.add_row)

        self.button_h_layout = QHBoxLayout()
        self.button_h_layout.setSpacing(10)
        self.button_h_layout.addStretch()

        back_button = QPushButton("Back")
        back_button.setObjectName("nav_button")
        back_button.clicked.connect(lambda: self.back.emit(KEY_RECYCLABLE))
        self.button_h_layout.addWidget(back_button)

        next_button = QPushButton("Next")
        next_button.setObjectName("nav_button")
        next_button.clicked.connect(self.collect_and_proceed)
        self.button_h_layout.addWidget(next_button)

        self.card_layout.addLayout(self.button_h_layout)
        self.wrapper_layout.addWidget(self.content_card)
        self.wrapper_layout.addStretch()

    def collect_and_proceed(self):
        data = self.included_section.collect_data() + self.excluded_section.collect_data()
        print("\nCollected Recyclable Data:")
        # pprint.pprint(data) # Import pprint if needed, or just print
        print(data)
        self.next.emit(KEY_RECYCLABLE)
