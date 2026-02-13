import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QSizePolicy, QGroupBox, QRadioButton, QStackedWidget, QFormLayout, QGridLayout,
    QToolTip
)
from PySide6.QtGui import QDoubleValidator, QIntValidator, QCursor, QIcon
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QEvent, QObject, QSize

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




DEFAULT_MACHINERY_DATA = [
    {"name": "Backhoe loader (JCB)", "source": "Diesel", "rate": "5", "ef": "2.69"},
    {"name": "Bar bending machine", "source": "Electricity (Grid)", "rate": "3", "ef": "0.71"},
    {"name": "Bar cutting machine", "source": "Electricity (Grid)", "rate": "4", "ef": "0.71"},
    {"name": "Bitumen boiler", "source": "Diesel", "rate": "1", "ef": "2.69"},
    {"name": "Bitumen sprayer", "source": "Diesel", "rate": "5", "ef": "2.69"},
    {"name": "Concrete pump", "source": "Diesel", "rate": "12", "ef": "2.69"},
    {"name": "Crane (crawler)", "source": "Diesel", "rate": "12", "ef": "2.69"},
    {"name": "Crane (mobile)", "source": "Diesel", "rate": "8", "ef": "2.69"},
    {"name": "Dewatering pump", "source": "Diesel", "rate": "2", "ef": "2.69"},
    {"name": "DG set", "source": "Diesel", "rate": "4", "ef": "2.69"},
    {"name": "Grouting mixer", "source": "Electricity (Grid)", "rate": "1", "ef": "0.71"},
    {"name": "Grouting pump", "source": "Electricity (Grid)", "rate": "5", "ef": "0.71"},
    {"name": "Hydraulic excavator", "source": "Diesel", "rate": "14", "ef": "2.69"},
    {"name": "Hydraulic stressing jack", "source": "Electricity (Grid)", "rate": "3", "ef": "0.71"},
    {"name": "Needle Vibrator", "source": "Electricity (Grid)", "rate": "1", "ef": "0.71"},
    {"name": "Paver finisher", "source": "Diesel", "rate": "7", "ef": "2.69"},
    {"name": "Road roller", "source": "Diesel", "rate": "4", "ef": "2.69"},
    {"name": "Rotary piling rig/Hydraulic piling rig", "source": "Diesel", "rate": "15", "ef": "2.69"},
    {"name": "Site office (If Grid electricity is used)", "source": "Electricity (Grid)", "rate": "4", "ef": "0.71"},
    {"name": "Welding machine", "source": "Electricity (Grid)", "rate": "4", "ef": "0.71"},
]

class DetailedSectionWidget(QWidget):
    """View 1: The detailed table using QGridLayout for better alignment."""
    def __init__(self):
        super().__init__()
        self.row_widgets = [] # Keep track of rows [(w1, w2, ...), ...]
        self.next_row_idx = 1 # Start at 1 (0 is headers)
        self.delayed_tooltip_filter = DelayedTooltipFilter(delay=1200, parent=self)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Removed Title "Detailed Construction Equipment Data" as requested

        # Main Grid Layout
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(10)
        self.grid.setHorizontalSpacing(15)
        layout.addLayout(self.grid)

        # Headers
        headers = [
            "Construction Equipment", "Energy Source", "Diesel Consumption(l/hr)\nor Electricity(Kw)", 
            "Avg Hrs/Day", "No. of Days", "Emission", "Emissions (kgCO2e)", "Actions"
        ]
        
        # approximate widths/stretch to guide resizing
        self.grid.setColumnStretch(0, 2)
        self.grid.setColumnStretch(1, 2)
        self.grid.setColumnStretch(2, 0) # Reduced stretch for Consumption
        self.grid.setColumnStretch(3, 1)
        self.grid.setColumnStretch(4, 1)
        self.grid.setColumnStretch(5, 2) # Increased Width for "Emission"
        self.grid.setColumnStretch(6, 1) # Decreased Width for "Emissions (kgCO2e)" (relative to others, kept 1 but others might push it)
        self.grid.setColumnStretch(7, 1)

        for c, text in enumerate(headers):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; color: #555; font-size: 12px; padding-bottom: 5px;")
            if c == 7:
                lbl.setAlignment(Qt.AlignCenter)
            else:
                lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.grid.addWidget(lbl, 0, c)

        # Add Button
        self.btn_add = QPushButton("+ Add Equipment")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setObjectName("addButton")
        self.btn_add.clicked.connect(lambda: self.add_new_row())
        
        # We put the add button in a container below the grid
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.btn_add)
        btn_container.addStretch()
        
        layout.addLayout(btn_container)
        layout.addStretch() # Push everything up

        # Populate Default Data
        for item in DEFAULT_MACHINERY_DATA:
            self.add_new_row(item)

    def add_new_row(self, data=None):
        row_idx = self.next_row_idx
        self.next_row_idx += 1
        
        # Helper for tooltip setup
        def setup_tooltip(widget):
            widget.setToolTip(widget.text() if widget.text() else "")
            widget.installEventFilter(self.delayed_tooltip_filter)
            widget.textChanged.connect(lambda text, w=widget: w.setToolTip(text))

        # 1. Equipment Name
        input_equip = QLineEdit()
        input_equip.setPlaceholderText("Equipment Name")
        input_equip.setAlignment(Qt.AlignLeft)
        if data: 
            input_equip.setText(data.get("name", ""))
            input_equip.setCursorPosition(0)
        setup_tooltip(input_equip)
        self.grid.addWidget(input_equip, row_idx, 0)
        
        # Validators
        double_validator = QDoubleValidator()
        double_validator.setBottom(0.0)
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        
        int_validator = QIntValidator()
        int_validator.setBottom(0)

        # 2. Energy Source
        input_source = QLineEdit()
        input_source.setPlaceholderText("Source")
        input_source.setAlignment(Qt.AlignLeft)
        if data: input_source.setText(data.get("source", ""))
        setup_tooltip(input_source)
        self.grid.addWidget(input_source, row_idx, 1)

        # 3. Rate (Diesel Consumption) - Numeric
        input_rate = QLineEdit()
        input_rate.setPlaceholderText("consumption")
        input_rate.setValidator(double_validator)
        input_rate.setAlignment(Qt.AlignRight)
        input_rate.setFixedWidth(120) # restrict width
        if data: input_rate.setText(data.get("rate", ""))
        setup_tooltip(input_rate)
        self.grid.addWidget(input_rate, row_idx, 2)

        # 4. Avg Hours/Day - Numeric/Decimal
        input_hours = QLineEdit()
        input_hours.setPlaceholderText("Hrs/Day")
        input_hours.setValidator(double_validator)
        input_hours.setAlignment(Qt.AlignRight)
        if data: input_hours.setText(data.get("hours", ""))
        setup_tooltip(input_hours)
        self.grid.addWidget(input_hours, row_idx, 3)

        # 5. Number of Days - Integer Only
        input_days = QLineEdit()
        input_days.setPlaceholderText("Days")
        input_days.setValidator(int_validator)
        input_days.setAlignment(Qt.AlignRight)
        if data: input_days.setText(data.get("days", ""))
        setup_tooltip(input_days)
        self.grid.addWidget(input_days, row_idx, 4)

        # 6. Emission Factor - Numeric/Decimal
        input_ef = QLineEdit()
        input_ef.setPlaceholderText("Emission") # Updated placeholder
        input_ef.setValidator(double_validator)
        input_ef.setAlignment(Qt.AlignRight)
        if data: input_ef.setText(data.get("ef", ""))
        setup_tooltip(input_ef)
        self.grid.addWidget(input_ef, row_idx, 5)

        # 7. Total Emissions (Result)
        # Using QLineEdit for consistency but readonly <-- OLD COMMENT, NOW EDITABLE
        label_total = QLineEdit("0.00")
        # label_total.setReadOnly(True) # Made editable per user request
        label_total.setValidator(double_validator) # Validation
        label_total.setAlignment(Qt.AlignRight)
        setup_tooltip(label_total)
        self.grid.addWidget(label_total, row_idx, 6)

        # 8. Actions (Delete button)
        
        # Calculate path to delete icon (delete.png)
        current_dir = os.path.dirname(__file__) # .../widgets/carbon_emission_data
        widgets_dir = os.path.dirname(current_dir)
        desktop_app_dir = os.path.dirname(widgets_dir)
        icon_path = os.path.join(desktop_app_dir, 'resources', 'images', 'delete.png')

        btn_delete = QPushButton()
        if os.path.exists(icon_path):
            btn_delete.setIcon(QIcon(icon_path))
        else:
            btn_delete.setText("Delete") # Fallback
            btn_delete.setStyleSheet("background-color: #D32F2F; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-weight: bold;")

        btn_delete.setIconSize(QSize(24, 24))
        btn_delete.setCursor(Qt.PointingHandCursor)
        # Assuming we want a small fixed width for the icon button, e.g. 30px to match others
        btn_delete.setFixedWidth(30)
        btn_delete.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: transparent; }
        """)
        
        btn_delete.setToolTip("Delete")
        btn_delete.installEventFilter(self.delayed_tooltip_filter)

        self.grid.addWidget(btn_delete, row_idx, 7, alignment=Qt.AlignCenter)

        # Store widget references for this row to handle logic & deletion
        row_data = {
            "widgets": [input_equip, input_source, input_rate, input_hours, input_days, input_ef, label_total, btn_delete],
            "inputs": (input_rate, input_hours, input_days, input_ef),
            "output": label_total,
            "row_idx": row_idx
        }
        self.row_widgets.append(row_data)

        # Connect signals
        # Calculation
        calc_func = lambda: self.calculate_row_emission(row_data)
        input_rate.textChanged.connect(calc_func)
        input_hours.textChanged.connect(calc_func)
        input_days.textChanged.connect(calc_func)
        input_ef.textChanged.connect(calc_func)

        # Deletion
        btn_delete.clicked.connect(lambda: self.delete_row(row_data))

    def calculate_row_emission(self, row_data):
        try:
            rate = float(row_data["inputs"][0].text() or 0)
            hours = float(row_data["inputs"][1].text() or 0)
            days = float(row_data["inputs"][2].text() or 0)
            ef = float(row_data["inputs"][3].text() or 0)
            
            total = rate * hours * days * ef
            row_data["output"].setText(f"{total:.2f}")
        except ValueError:
            row_data["output"].setText("0.00")

    def delete_row(self, row_data):
        # Remove widgets from grid and delete them
        for w in row_data["widgets"]:
            self.grid.removeWidget(w)
            w.deleteLater()
        
        if row_data in self.row_widgets:
            self.row_widgets.remove(row_data)




class SummarySectionWidget(QWidget):
    """View 2: The summary format restored per user request."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)

        # ---- Left Block (Electricity) ----
        elec_group = QGroupBox("Estimated Electricity Bill Summary")
        elec_group.setObjectName("summaryGroup")
        elec_layout = QFormLayout(elec_group)
        elec_layout.setVerticalSpacing(15)
        elec_layout.setContentsMargins(20, 25, 20, 20)

        # Validator for numeric inputs (Double)
        validator = QDoubleValidator()
        validator.setBottom(0.0)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        self.e_unit_rate = QLineEdit("8.00")
        self.e_unit_rate.setValidator(validator)
        
        self.e_consumption = QLineEdit("0")
        self.e_consumption.setValidator(validator)
        
        self.e_ef = QLineEdit("0.71")
        self.e_ef.setValidator(validator)
        
        self.e_total = QLineEdit("0")
        self.e_total.setValidator(validator) # Made editable

        elec_layout.addRow("Unit rate of electricity consumption:", self.e_unit_rate)
        elec_layout.addRow("Electricity consumption (kwh):", self.e_consumption)
        elec_layout.addRow("Emission factor (kgCO2e/kwh):", self.e_ef)
        elec_layout.addRow("Total Emission (kgCO2e):", self.e_total)
        
        # Connect signals for calculation
        self.e_consumption.textChanged.connect(self.calc_elec)
        self.e_ef.textChanged.connect(self.calc_elec)



        # ---- Right Block (Fuel) ----
        fuel_group = QGroupBox("Average Fuel Consumption Summary")
        fuel_group.setObjectName("summaryGroup")
        fuel_layout = QFormLayout(fuel_group)
        fuel_layout.setVerticalSpacing(15)
        fuel_layout.setContentsMargins(20, 25, 20, 20)

        self.f_avg_daily = QLineEdit("0.00")
        self.f_avg_daily.setValidator(validator)
        
        self.f_days = QLineEdit("0")
        self.f_days.setValidator(validator)
        
        self.f_total_consumed = QLineEdit("0.00")
        self.f_total_consumed.setValidator(validator) # Made editable
        
        self.f_ef = QLineEdit("2.69")
        self.f_ef.setValidator(validator)
        
        self.f_total_emission = QLineEdit("0.00")
        self.f_total_emission.setValidator(validator) # Made editable

        fuel_layout.addRow("Average fuel consumption per day:", self.f_avg_daily)
        fuel_layout.addRow("Number of days of construction:", self.f_days)
        fuel_layout.addRow("Total fuel consumed (liters):", self.f_total_consumed)
        fuel_layout.addRow("Emission factor (kgco2e/liter):", self.f_ef)
        fuel_layout.addRow("Total Emission (kgCO2e):", self.f_total_emission)

        # Connect signals for calculation
        self.f_avg_daily.textChanged.connect(self.calc_fuel)
        self.f_days.textChanged.connect(self.calc_fuel)
        self.f_ef.textChanged.connect(self.calc_fuel)

        # Add to main layout with equal stretch factor (1) and AlignTop to prevent vertical stretching
        layout.addWidget(elec_group, 1, Qt.AlignTop)
        layout.addWidget(fuel_group, 1, Qt.AlignTop)

    def calc_elec(self):
        try:
            cons = float(self.e_consumption.text() or 0)
            ef = float(self.e_ef.text() or 0)
            self.e_total.setText(f"{cons * ef:.2f}")
        except ValueError: pass

    def calc_fuel(self):
        try:
            avg = float(self.f_avg_daily.text() or 0)
            days = float(self.f_days.text() or 0)
            total_fuel = avg * days
            self.f_total_consumed.setText(f"{total_fuel:.2f}")
            
            ef = float(self.f_ef.text() or 0)
            self.f_total_emission.setText(f"{total_fuel * ef:.2f}")
        except ValueError: pass


class CarbonMachineryWidget(QWidget):
    next = Signal(str)
    back = Signal(str)
    
    def __init__(self, database=None, parent=None):
        # Handle case where parent is UiMainWindow (not a QWidget)
        qt_parent = parent if isinstance(parent, QWidget) else None
        super().__init__(qt_parent)
        print("DEBUG: CarbonMachineryWidget initialized")
        self.database = database
        # Store the controller/parent reference even if it's not the Qt parent
        self.parent_controller = parent 
        self.setObjectName("CarbonMachineryWidget")
        # self.setMinimumSize(1100, 700) # Optional, usually handled by main window layout
        self.setStyleSheet(self.get_stylesheet())
        self.init_ui()

    def get_stylesheet(self):
        return """
            QWidget#CarbonMachineryWidget {
                background-color: #555;
            }
            QScrollArea { background-color: transparent; border: none; }
            QWidget#scrollWrapper { background-color: transparent; }
            QFrame#contentFrame {
                background-color: #FFF9F9;
                border: 1px solid #000000;
                border-radius: 0px;
                padding: 15px;
            }
            QPushButton#addButton {
                background-color: white;
                border: 1px solid #d0c0d8;
                color: black;
                padding: 8px 20px;
                border-radius: 18px;
                font-weight: bold;
            }
            QPushButton#addButton:hover { background-color: #f5f0f7; }
            QPushButton#navButton, QPushButton#backBtn, QPushButton#nextBtn {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #3F3E5E;
                padding: 6px 15px;
                text-align: center;
                min-width: 80px;
                font-weight: bold;
            }
            QPushButton#navButton:hover, QPushButton#backBtn:hover, QPushButton#nextBtn:hover {
                background-color: #F8F8F8;
                border-color: #C0C0C0;
            }
            QPushButton#navButton:pressed, QPushButton#backBtn:pressed, QPushButton#nextBtn:pressed {
                background-color: #E8E8E8;
                border-color: #A0A0A0;
            }
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
                background-color: white;
                color: black;
                min-height: 25px;
            }
            QLineEdit:read-only {
                background-color: #f0f0f0;
                color: #333;
                font-weight: bold;
            }
            QRadioButton { font-weight: bold; font-size: 14px; color: black; }
            QLabel { color: black; font-size: 12px; }
            
            QGroupBox#summaryGroup {
                font-weight: bold;
                font-size: 14px;
                color: black;
                border: 1px solid #d0c0d8;
                border-radius: 10px;
                margin-top: 10px;
                background-color: #FFF9F9;
                min-width: 400px;
                min-height: 340px;
            }
            QGroupBox#summaryGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #FFF9F9; 
            }
        """

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Main Scroll Area for Page Responsiveness
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)

        # 2. Scroll Wrapper to hold content
        self.scroll_wrapper = QWidget()
        self.scroll_wrapper.setObjectName("scrollWrapper")
        self.scroll_area.setWidget(self.scroll_wrapper)
        
        wrapper_layout = QVBoxLayout(self.scroll_wrapper)
        wrapper_layout.setContentsMargins(30, 30, 30, 30)
        wrapper_layout.setSpacing(15)

        # Title (Inside wrapper so it scrolls)
        title_label = QLabel("Carbon Emission Machinery Data")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")
        wrapper_layout.addWidget(title_label)
        
        # Content Box (The "Box of Data")
        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # A. Selection Mechanism (Radio Buttons)
        radio_layout = QHBoxLayout()
        self.rb_detailed = QRadioButton("Detailed Equipment List")
        self.rb_summary = QRadioButton("Summary Estimation Blocks")
        self.rb_detailed.setChecked(True)
        
        self.rb_detailed.toggled.connect(self.switch_view)
        
        radio_layout.addWidget(self.rb_detailed)
        radio_layout.addWidget(self.rb_summary)
        radio_layout.addStretch()
        content_layout.addLayout(radio_layout)
        
        # B. Stacked Widget (Views)
        self.stacked_widget = QStackedWidget()
        
        self.detailed_view = DetailedSectionWidget()
        self.summary_view = SummarySectionWidget()
        
        self.stacked_widget.addWidget(self.detailed_view)
        self.stacked_widget.addWidget(self.summary_view)
        
        content_layout.addWidget(self.stacked_widget)

        # C. Navigation Buttons
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 10, 0, 0)
        
        btn_back = QPushButton("Back")
        btn_back.setObjectName("backBtn")
        btn_back.clicked.connect(lambda: self.back.emit("Carbon Emission Machinery Data"))
        
        btn_next = QPushButton("Next")
        btn_next.setObjectName("nextBtn")
        btn_next.clicked.connect(lambda: self.next.emit("Carbon Emission Machinery Data"))

        nav_layout.addStretch()
        nav_layout.addWidget(btn_back)
        nav_layout.addWidget(btn_next)
        
        content_layout.addLayout(nav_layout)
        
        # Add content frame to wrapper
        wrapper_layout.addWidget(self.content_frame)
        
        # Spacer to push content up if window is large
        wrapper_layout.addStretch()

    def switch_view(self):
        if self.rb_detailed.isChecked():
            self.stacked_widget.setCurrentIndex(0)
        else:
            self.stacked_widget.setCurrentIndex(1)



