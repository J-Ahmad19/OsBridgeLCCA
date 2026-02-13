from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QCoreApplication, Qt, QSize, Signal
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QLineEdit, QComboBox, QGridLayout, QWidget, QLabel, QVBoxLayout, QScrollArea, QSpacerItem, QSizePolicy, QRadioButton, QStackedWidget, QFrame, QGroupBox, QFormLayout)
from PySide6.QtGui import QIcon, QIntValidator
from osbridgelcca.desktop_app.widgets.utils.data import *
import sys
import os

class GlobalSectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        print("DEBUG: Initializing GlobalSectionWidget with Updated Spacing 0")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignTop)

        # Create a QGroupBox to match CarbonMachineryWidget's summary blocks
        self.box_group = QGroupBox("Total Road User Cost Data")
        self.box_group.setObjectName("summaryGroup")
        
        # Using QHBoxLayout for precise control over alignment
        content_layout = QHBoxLayout()
        # Adjusted margins to be tighter if needed, but spacing=0 is key for "between" elements
        content_layout.setContentsMargins(10, 20, 10, 20) 
        content_layout.setSpacing(0)
        content_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.box_group.setLayout(content_layout)

        # Label for Total Road User Cost
        label = QLabel("Total Road User Cost:")
        # Explicit zero margins/padding.
        label.setStyleSheet("color: #333333; font-size: 12px; font-weight: normal; border: none; margin: 0px; padding: 0px;") 
        
        self.cost_input = QLineEdit()
        self.cost_input.setPlaceholderText("Enter Total Cost")
        self.cost_input.setFixedWidth(200)
        self.cost_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 6px; 
                padding: 6px 10px;
                font-size: 13px;
                color: #333333;
                background-color: white;
                margin: 0px;
            }
            QLineEdit:focus {
                border: 1px solid #999999; /* Neutral grey focus instead of blue */
            }
        """)
        
        content_layout.addWidget(label)
        content_layout.addWidget(self.cost_input)
        content_layout.addStretch() # Force items to the left
        
        layout.addWidget(self.box_group)

 

    def get_data(self):
        return self.cost_input.text()


class IndiaSectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widgets = []
        self.init_ui()

    def init_ui(self):
        self.general_layout = QVBoxLayout(self)
        self.general_layout.setContentsMargins(10, 20, 10, 10)
        self.general_layout.setSpacing(10)

        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(20)

        field_width = 200

        # 1. Annual Routine Inspection cost rate as percentage of total construction cost
        label2 = QLabel("Routine Inspection Cost Rate\n(Percentage of Initial Construction Cost)")
        label2.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        ari_input = QLineEdit()
        self.widgets.append(ari_input)
        ari_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        ari_input.setFixedWidth(field_width)
        ari_input.setText("1")
        ari_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        ari_unit = QLabel("(%)")
        ari_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label2, 0, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(ari_input, 0, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(ari_unit, 0, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(ari_suggested, 0, 3, alignment=Qt.AlignVCenter)

        # 2. Routine Inspection Frequency
        label5 = QLabel("Routine Inspection Frequency")
        label5.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fri_input = QLineEdit()
        fri_input.setValidator(QIntValidator(fri_input))
        self.widgets.append(fri_input)
        fri_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        fri_input.setFixedWidth(field_width)
        fri_input.setText("1")
        fri_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        fri_unit = QLabel("(years)")
        fri_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label5, 1, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_input, 1, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_unit, 1, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_suggested, 1, 3, alignment=Qt.AlignVCenter)

        # 3. Periodic Maintenance Cost Rate
        label1 = QLabel("Periodic Maintenance Cost\n(Percentage of Initial Construction Cost)")
        label1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        pmc_input = QLineEdit()
        self.widgets.append(pmc_input)
        pmc_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        pmc_input.setFixedWidth(field_width)
        pmc_input.setText("0.55")
        pmc_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        pmc_unit = QLabel("(%)")
        pmc_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label1, 2, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_input, 2, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_unit, 2, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_suggested, 2, 3, alignment=Qt.AlignVCenter)

        # 4. Periodic Maintenance Frequency
        label4 = QLabel("Periodic Maintenance Frequency")
        label4.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fpm_input = QLineEdit()
        fri_input.setValidator(QIntValidator(fri_input))
        self.widgets.append(fpm_input)
        fpm_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        fpm_input.setFixedWidth(field_width)
        fpm_input.setText("5")
        fpm_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        fpm_unit = QLabel("(years)")
        fpm_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label4, 3, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fpm_input, 3, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fpm_unit, 3, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fpm_suggested, 3, 3, alignment=Qt.AlignVCenter)

        # 5. Major Inspection Cost Rate
        label1 = QLabel("Major Inspection Cost\n(Percentage of Initial Construction Cost)")
        label1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        pmc_input = QLineEdit()
        self.widgets.append(pmc_input)
        pmc_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        pmc_input.setFixedWidth(field_width)
        pmc_input.setText("0.5")
        pmc_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        pmc_unit = QLabel("(%)")
        pmc_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label1, 4, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_input, 4, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_unit, 4, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_suggested, 4, 3, alignment=Qt.AlignVCenter)

        # 6. Major Inspection Frequency
        label5 = QLabel("Major Inspection Frequency")
        label5.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fri_input = QLineEdit()
        fri_input.setValidator(QIntValidator(fri_input))
        self.widgets.append(fri_input)
        fri_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        fri_input.setFixedWidth(field_width)
        fri_input.setText("5")
        fri_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        fri_unit = QLabel("(years)")
        pmc_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label5, 5, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_input, 5, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_unit, 5, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_suggested, 5, 3, alignment=Qt.AlignVCenter)

        # 5. Major Repair Cost Rate
        label1 = QLabel("Major Repair Cost\n(Percentage of Initial Construction Cost)")
        label1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        pmc_input = QLineEdit()
        self.widgets.append(pmc_input)
        pmc_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        pmc_input.setFixedWidth(field_width)
        pmc_input.setText("10")
        pmc_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        pmc_unit = QLabel("(%)")
        pmc_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label1, 6, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_input, 6, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_unit, 6, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_suggested, 6, 3, alignment=Qt.AlignVCenter)


        # 6. Major Repairs Frequency
        label5 = QLabel("Major Repair Frequency")
        label5.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fri_input = QLineEdit()
        fri_input.setValidator(QIntValidator(fri_input))
        self.widgets.append(fri_input)
        fri_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        fri_input.setFixedWidth(field_width)
        fri_input.setText("20")
        fri_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        fri_unit = QLabel("(years)")
        pmc_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label5, 7, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_input, 7, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_unit, 7, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_suggested, 7, 3, alignment=Qt.AlignVCenter)

        # 7. Replacement cost of bearing and expansion joint
        label3 = QLabel("Replacement cost of bearing and expansion joint\n(Percentage of Initial Construction Cost of the Superstructure)")
        label3.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        rr_input = QLineEdit()
        self.widgets.append(rr_input)
        rr_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        rr_input.setFixedWidth(field_width)
        rr_input.setText("12.5")
        rr_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        rr_unit = QLabel("(%)")
        rr_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label3, 8, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(rr_input, 8, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(rr_unit, 8, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(rr_suggested, 8, 3, alignment=Qt.AlignVCenter)

        # 8. Frequency of Repair cost of bearing and expansion joints
        label5 = QLabel("Frequency of Repair cost of bearing and expansion joints")
        label5.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fri_input = QLineEdit()
        fri_input.setValidator(QIntValidator(fri_input))
        self.widgets.append(fri_input)
        fri_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        fri_input.setFixedWidth(field_width)
        fri_input.setText("25")
        fri_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        fri_unit = QLabel("(years)")
        pmc_suggested = QLabel("Suggested", parent=self, styleSheet="color: #B3AEAE; font-size: 10px;")
        grid_layout.addWidget(label5, 9, 0, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_input, 9, 1, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(fri_unit, 9, 2, alignment=Qt.AlignVCenter)
        grid_layout.addWidget(pmc_suggested, 9, 3, alignment=Qt.AlignVCenter)

        self.general_layout.addLayout(grid_layout)
        self.general_layout.addStretch(1)

class MaintenanceRepairData(QWidget):
    closed = Signal()
    next = Signal(str)
    back = Signal(str)
    def __init__(self, database, parent=None):
        super().__init__()
        self.parent = parent
        self.database_manager = database
        self.widgets = []

        self.component_widgets = []

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

            /* Updated Styling for navigation buttons to match the Add Material/Component buttons */
            QPushButton#nav_button {
                background-color: #FFFFFF; /* White background */
                border: 1px solid #E0E0E0; /* Light grey border */
                border-radius: 8px; /* Slightly more rounded corners */
                color: #3F3E5E; /* Dark text color */
                padding: 6px 15px; /* Increased padding */
                text-align: center;
                min-width: 80px; /* Ensure a minimum width */
            }
            QPushButton#nav_button:hover {
                background-color: #F8F8F8; /* Very subtle light grey on hover */
                border-color: #C0C0C0; /* Darker border on hover */
            }
            QPushButton#nav_button:pressed {
                background-color: #E8E8E8; /* Darker grey on pressed */
                border-color: #A0A0A0; /* Even darker border */
            }
            QRadioButton { font-weight: bold; font-size: 14px; color: black; }
            
            /* Styling for the Summary Group Box (copied from CarbonMachineryWidget) */
            QGroupBox#summaryGroup {
                font-weight: bold;
                font-size: 14px;
                color: black;
                border: 1px solid #d0c0d8;
                border-radius: 10px;
                margin-top: 10px;
                background-color: #FFF9F9;
                min-width: 400px;
                /* min-height: 340px;  Removed min-height to fit content */
            }
            QGroupBox#summaryGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #FFF9F9; 
            }
        """)



        self.setObjectName("central_panel_widget")
        left_panel_vlayout = QVBoxLayout(self)
        left_panel_vlayout.setContentsMargins(0, 0, 0, 0)
        left_panel_vlayout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        scroll_content_widget = QWidget()
        scroll_content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        scroll_content_widget.setObjectName("scroll_content_widget")
        self.scroll_area.setWidget(scroll_content_widget)

        self.scroll_content_layout = QVBoxLayout(scroll_content_widget)
        self.scroll_content_layout.setContentsMargins(0,0,0,0)
        self.scroll_content_layout.setSpacing(0)

        # --- Selection Mechanism (Radio Buttons) ---
        radio_container = QWidget()
        radio_layout = QHBoxLayout(radio_container)
        radio_layout.setContentsMargins(20, 10, 20, 0)
        radio_layout.setSpacing(20)
        
        self.rb_india = QRadioButton("India")
        self.rb_global = QRadioButton("Global")
        self.rb_india.setChecked(True)
        self.rb_india.setCursor(Qt.PointingHandCursor)
        self.rb_global.setCursor(Qt.PointingHandCursor)
        
        self.rb_india.toggled.connect(self.switch_view)
        
        radio_layout.addWidget(self.rb_india)
        radio_layout.addWidget(self.rb_global)
        radio_layout.addStretch()
        
        self.scroll_content_layout.addWidget(radio_container)

        # --- Stacked Widget (Views) ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding) # Allow it to grow
        
        self.india_view = IndiaSectionWidget()
        self.global_view = GlobalSectionWidget()
        
        self.stacked_widget.addWidget(self.india_view)
        self.stacked_widget.addWidget(self.global_view)
        
        self.scroll_content_layout.addWidget(self.stacked_widget)


        # Create the navigation buttons layout
        self.button_h_layout = QHBoxLayout()
        self.button_h_layout.setSpacing(10)
        self.button_h_layout.setContentsMargins(10,10,10,10)

        # Adjust these stretch factors to control the position
        self.button_h_layout.addStretch(6) # Larger stretch on the left to push it more right

        back_button = QPushButton("Back")
        back_button.setObjectName("nav_button")
        back_button.clicked.connect(lambda: self.back.emit(KEY_MAINTAINANCE_REPAIR))
        self.button_h_layout.addWidget(back_button)

        next_button = QPushButton("Next")
        next_button.setObjectName("nav_button")
        next_button.clicked.connect(self.collect_data)
        next_button.clicked.connect(lambda: self.next.emit(KEY_MAINTAINANCE_REPAIR))
        self.button_h_layout.addWidget(next_button)


        # Add initial spacing before the navigation buttons
        self.scroll_content_layout.addLayout(self.button_h_layout)

        # --- Add a corner spacer to the scroll_content_layout ---
        self.button_h_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.scroll_content_layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        left_panel_vlayout.addWidget(self.scroll_area)

    def close_widget(self):
        self.closed.emit()
        self.setParent(None)


    def switch_view(self):
        if self.rb_india.isChecked():
            self.stacked_widget.setCurrentIndex(0)
        else:
            self.stacked_widget.setCurrentIndex(1)

    def collect_data(self):
        from pprint import pprint
        
        # Check which view is active
        if self.rb_india.isChecked():
            # Collecting Data from India View (Existing logic)
            # We access the widgets via self.india_view.widgets
            widgets = self.india_view.widgets
            
            data = {
                KEY_ROUTINE_INSP_COST: 0.0 if not widgets[0].text() else float(widgets[0].text())/100,
                KEY_ROUTINE_INSP_FREQ: 0 if not widgets[1].text() else int(widgets[1].text()),
                KEY_PERIODIC_MAINT_COST: 0.0 if not widgets[2].text() else float(widgets[2].text())/100,
                KEY_PERIODIC_MAINT_FREQ: 0 if not widgets[3].text() else int(widgets[3].text()),
                KEY_MAJOR_INSP_COST: 0.0 if not widgets[4].text() else float(widgets[4].text())/100,
                KEY_MAJOR_INSP_FREQ: 0 if not widgets[5].text() else int(widgets[5].text()),
                KEY_MAJOR_REPAIR_COST: 0.0 if not widgets[6].text() else float(widgets[6].text())/100,
                KEY_MAJOR_REPAIR_FREQ: 0 if not widgets[7].text() else int(widgets[7].text()),
                KEY_BEARING_EXP_JOINT_REPAIR_COST: 0.0 if not widgets[8].text() else float(widgets[8].text())/100,
                KEY_BEARING_EXP_JOINT_REPAIR_FREQ: 0 if not widgets[9].text() else int(widgets[9].text())
            }
            print("\nCollected Data from Maintenance UI (India):")
            pprint(data)

            # Save UI Data to Backend - Existing calculations
            self.database_manager.maintainance_and_repair_data = data
            self.database_manager.routine_inspection_cost() 
            self.database_manager.periodic_maintainance_cost()
            self.database_manager.periodic_maintainance_carbon_emission_cost()
            self.database_manager.major_inspection_cost()
            self.database_manager.major_repair_cost()
            self.database_manager.major_repair_related_carbon_emission_cost()
            self.database_manager.bearing_expansion_joint_replacement_cost()
            self.database_manager.carbon_emission_rerouting_during_major_repairs()
            self.database_manager.carbon_emission_rerouting_during_replacement()

        else:
            # Collecting Data from Global View
            global_cost = self.global_view.get_data()
            print(f"\nCollected Data from Maintenance UI (Global): Total Road User Cost = {global_cost}")
            # Placeholder: We currently don't have a backend slot for "Global Total Cost". 
            # If needed, we would update self.database_manager or similar here.


#----------------Standalone-Test-Code--------------------------------

# class MyMainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.setStyleSheet("border: none")

#         self.central_widget = QWidget()
#         self.central_widget.setObjectName("central_widget")
#         self.setCentralWidget(self.central_widget)

#         self.main_h_layout = QHBoxLayout(self.central_widget)
#         self.main_h_layout.addStretch(1)

#         self.main_h_layout.addWidget(MaintenanceRepairData(), 2)

#         self.setWindowState(Qt.WindowMaximized)


# if __name__ == "__main__":
#     QCoreApplication.setAttribute(Qt.AA_DontShowIconsInMenus, False)
#     app = QApplication(sys.argv)
#     window = MyMainWindow()
#     window.show()
#     sys.exit(app.exec())