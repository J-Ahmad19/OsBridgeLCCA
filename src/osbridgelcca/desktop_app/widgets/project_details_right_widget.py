from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtCore import QCoreApplication, QSize, Qt, QPropertyAnimation, QEasingCurve, Signal, Slot
from PySide6.QtGui import (QIcon)
from PySide6.QtWidgets import (QHBoxLayout, QTextEdit, QScrollArea, QSpacerItem, QSizePolicy,
    QPushButton, QWidget, QLabel, QVBoxLayout, QGridLayout, QLineEdit, QComboBox)
from osbridgelcca.desktop_app.widgets.utils.data import *
from osbridgelcca.desktop_app.resources.resources_rc import *
import sys

# Import Backend Logic
try:
    from osbridgelcca.desktop_app.core.project_creator import ProjectCreator
except ImportError:
    print("Warning: ProjectCreator backend not found.")
    ProjectCreator = None

# JAWWAD : Added import for sor_backend to handle dynamic Region and SOR logic
try:
    from osbridgelcca.desktop_app.widgets.utils.sor_backend import sor_manager
except ImportError:
    print("Warning: sor_backend.py not found. Search features will be limited.")
    sor_manager = None

class ProjectDetailsWidget(QWidget):
    closed = Signal()
    projectCreated = Signal(str)  # Signal emitted when project is successfully created

    # Country to Currency Mapping
    COUNTRY_CURRENCY_MAP = {
        "India": "INR", "United States of America": "USD", "United Kingdom": "GBP",
        "Germany": "EUR", "France": "EUR", "Italy": "EUR", "Spain": "EUR", "Netherlands": "EUR",
        "Australia": "AUD", "Canada": "CAD", "Japan": "JPY", "China": "CNY",
        "Russia": "RUB", "Brazil": "BRL", "South Africa": "ZAR", "Saudi Arabia": "SAR",
        "United Arab Emirates": "AED", "Singapore": "SGD", "Switzerland": "CHF",
        "Afghanistan": "AFN", "Bangladesh": "BDT", "Pakistan": "PKR", "Sri Lanka": "LKR",
        "Nepal": "NPR", "Bhutan": "BTN", "Maldives": "MVR", "Kuwait": "KWD",
        "Qatar": "QAR", "Oman": "OMR", "Bahrain": "BHD", "Turkey": "TRY",
        "Thailand": "THB", "Vietnam": "VND", "Indonesia": "IDR", "Malaysia": "MYR",
        "Philippines": "PHP", "South Korea": "KRW", "North Korea": "KPW",
        "Egypt": "EGP", "Nigeria": "NGN", "Kenya": "KES", "Mexico": "MXN",
        "Argentina": "ARS", "Chile": "CLP", "Colombia": "COP", "Peru": "PEN",
        "New Zealand": "NZD", "Sweden": "SEK", "Norway": "NOK", "Denmark": "DKK",
        "Poland": "PLN", "Hungary": "HUF", "Czechia (Czech Republic)": "CZK",
        "Romania": "RON", "Bulgaria": "BGN", "Ukraine": "UAH", "Israel": "ILS"
    }

    def __init__(self, parent=None):
        super().__init__()
        
        # Initialize Backend Logic
        if ProjectCreator:
            self.creator = ProjectCreator()
            self.creator.projectCreated.connect(self.on_creation_success)
            self.creator.errorOccurred.connect(self.on_creation_error)
        else:
            self.creator = None

        self.setObjectName("central_panel_widget")
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
                border: 1px solid #000000;
                background-color: transparent;
                outline: none;
            }
            #scroll_content_widget {
                background-color: #FFF9F9;
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
            QPushButton#general_info, QPushButton#parameter_button, QPushButton#output_button {
                background-color: #FDEFEF;
                border: 1px solid #000000;
                text-align: left;
                padding: 3px 10px;
                color: #000000;
                font-size: 14px;
            }
            QPushButton#general_info:hover, QPushButton#parameter_button:hover, QPushButton#output_button:hover {
                background-color: #F0E6E6;
                border: 1px solid #000000;
            }
            QPushButton#general_info:pressed, QPushButton#parameter_button:pressed, QPushButton#output_button:pressed {
                background-color: #FFF3F3;
                border-color: #606060;
            }
            QPushButton#top_button_right_panel {
                background-color: #FDEFEF;
                border-top: 1px solid #000000;
                border-left: 1px solid #000000;
                border-right: 1px solid #000000;
                text-align: left;
                padding: 4px 10px;
                color: #000000;
            }
            QPushButton#top_button_right_panel:hover {
                background-color: #F0E6E6;
                border-color: #808080;
            }
            QPushButton#top_button_right_panel:pressed {
                background-color: #FFF3F3;
                border-color: #606060;
            }
            QPushButton#top_button_right_panel:hover QIcon {
                color: red;
            }
            /* Create Button Style */
            QPushButton#create_btn {
                background-color: #2E8B57; 
                color: white; 
                font-weight: bold;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton#create_btn:hover { background-color: #3CB371; }
            QPushButton#create_btn:disabled { background-color: #A0A0A0; }
        """)
        left_panel_vlayout = QVBoxLayout(self)
        left_panel_vlayout.setContentsMargins(0, 0, 0, 0)
        left_panel_vlayout.setSpacing(0)

        # --- Top Section ---
        top_h_layout_left_panel = QHBoxLayout()
        self.top_button_right_panel = QPushButton("Project Details Window      ")
        self.top_button_right_panel.setObjectName("top_button_right_panel")
        self.top_button_right_panel.setIcon(QIcon(":/images/close.png"))
        self.top_button_right_panel.setIconSize(QSize(13, 13))
        self.top_button_right_panel.setLayoutDirection(Qt.RightToLeft)
        self.top_button_right_panel.clicked.connect(self.close_widget)
        top_h_layout_left_panel.addWidget(self.top_button_right_panel)
        top_h_layout_left_panel.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        left_panel_vlayout.addLayout(top_h_layout_left_panel)

        # --- Scroll Area Setup ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        scroll_content_widget.setObjectName("scroll_content_widget")
        self.scroll_area.setWidget(scroll_content_widget)
        scroll_content_layout = QVBoxLayout(scroll_content_widget)
        scroll_content_layout.addStretch(1)

        # --- General Information Section Button ---
        self.general_info_button = QPushButton("   General Information")
        self.general_info_button.setObjectName("general_info")
        self.general_info_button.setCursor(Qt.PointingHandCursor)
        self.unactive_arrow_icon = QIcon(":/images/play_button_unselected.png")
        self.active_arrow_icon = QIcon(":/images/arrow_down.png")
        self.general_info_button.setIcon(self.unactive_arrow_icon)
        self.general_info_button.setIconSize(QSize(10, 10))
        self.general_info_button.setLayoutDirection(Qt.LeftToRight)
        scroll_content_layout.insertWidget(0, self.general_info_button)

        # --- General Information Form Widget ---
        self.general_button_active = False
        self.general_widget = QWidget()
        self.general_widget.setObjectName("general_info_form_widget")
        self.general_widget.setStyleSheet(f"""
            #general_info_form_widget QLineEdit,
            #general_info_form_widget QTextEdit,
            #general_info_form_widget QComboBox {{
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
                background-color: #FFFFFF;
            }}
            #general_info_form_widget QTextEdit::viewport {{
                background-color: #FFFFFF;
            }}
            #general_info_form_widget QLineEdit:focus,
            #general_info_form_widget QTextEdit:focus,
            #general_info_form_widget QComboBox:focus {{
                border: 1px solid #DDDCE0;
                background-color: #FFFFFF;
            }}
            #general_info_form_widget QTextEdit:focus::viewport {{
                background-color: #FFFFFF;
            }}
            #left_label {{
                margin-right: 20px;
            }}
            #info_button {{
                margin-right: {self.general_info_button.width()//2}px;
            }}
        """)
        grid_layout = QGridLayout(self.general_widget)
        grid_layout.setContentsMargins(30, 20, 30, 20)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)
        
        # Company Name
        label = QLabel("Company Name *")
        label.setObjectName("left_label")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 0, 0, 1, 1)
        self.company_name = QLineEdit(self.general_widget)
        grid_layout.addWidget(self.company_name, 0, 1, 1, 2)
        
        # Project Title
        label = QLabel("Project Title *")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 1, 0, 1, 1)
        self.project_title = QLineEdit(self.general_widget)
        grid_layout.addWidget(self.project_title, 1, 1, 1, 2)
        
        # Project Description
        label = QLabel("Project Description")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 2, 0, 1, 1)
        self.description = QTextEdit(self.general_widget)
        self.description.setPlaceholderText("Enter project description here...")
        grid_layout.addWidget(self.description, 2, 1, 1, 2)
        
        # Name of Valuer
        label = QLabel("Name of Valuer *")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 3, 0, 1, 1)
        self.valuer_name = QLineEdit(self.general_widget)
        self.valuer_name.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        grid_layout.addWidget(self.valuer_name, 3, 1, 1, 1)
        
        # Job Number
        label = QLabel("Job Number *")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 4, 0, 1, 1)
        self.job_number = QLineEdit(self.general_widget)
        self.job_number.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        grid_layout.addWidget(self.job_number, 4, 1, 1, 1)
        
        # Client
        label = QLabel("Client *")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 5, 0, 1, 1)
        self.client_name = QLineEdit(self.general_widget)
        self.client_name.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        grid_layout.addWidget(self.client_name, 5, 1, 1, 1)
        
        # --- FEATURE ADDITION: Currency Input (Moved UP to avoid AttributeError) ---
        # NOTE: We define this BEFORE the Country ComboBox logic so it exists when the signal fires.
        currency_label = QLabel("Currency *")
        currency_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # We will add it to the grid at row 7 later, but defining it here is key.
        
        self.currency_input = QLineEdit(self.general_widget)
        self.currency_input.setReadOnly(True)  # Auto-filled based on country
        self.currency_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
                background-color: #F2F2F2; /* Slightly grey to indicate read-only */
                color: #555555;
            }
        """)
        
        # Country ComboBox
        label = QLabel("Country *")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 6, 0, 1, 1)
        self.country_combo = QComboBox(self.general_widget)
        
        # Comprehensive list of countries
        countries = [
            "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
            "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
            "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo (Congo-Brazzaville)", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czechia (Czech Republic)",
            "Democratic Republic of the Congo", "Denmark", "Djibouti", "Dominica", "Dominican Republic",
            "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini (fmr. Swaziland)", "Ethiopia",
            "Fiji", "Finland", "France",
            "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
            "Haiti", "Holy See", "Honduras", "Hungary",
            "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
            "Jamaica", "Japan", "Jordan",
            "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan",
            "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
            "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar (formerly Burma)",
            "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway",
            "Oman",
            "Pakistan", "Palau", "Palestine State", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
            "Qatar",
            "Romania", "Russia", "Rwanda",
            "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
            "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu",
            "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States of America", "Uruguay", "Uzbekistan",
            "Vanuatu", "Venezuela", "Vietnam",
            "Yemen",
            "Zambia", "Zimbabwe"
        ]
        self.country_combo.addItems(countries)
        
        # Stylesheet for Dropdowns (reused for Region and SOR)
        combo_style = """
            QComboBox{
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 5px;
            }
            QComboBox::down-arrow {
                image: url(:/images/country_arrow.png);
                width: 18px;
                height: 18px;
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
        """
        
        self.country_combo.setStyleSheet(combo_style)
        
        # Connect Country change to slot for currency update
        # Now safe because self.currency_input exists
        self.country_combo.currentTextChanged.connect(self.on_country_changed)
        
        # Set default to India if in list, otherwise first item
        index = self.country_combo.findText("India")
        if index >= 0:
            self.country_combo.setCurrentIndex(index)
            
        grid_layout.addWidget(self.country_combo, 6, 1, 1, 1)
        info_icon = QLabel("ⓘ")
        info_icon.setStyleSheet("color: grey; font-size: 14px;")
        info_icon.setObjectName("info_button")
        info_icon.setToolTip("Social Cost of Carbon varies as per selected region")
        info_icon.setCursor(Qt.PointingHandCursor)
        info_icon.setAlignment(Qt.AlignRight)
        grid_layout.addWidget(info_icon, 6, 2, 1, 1)

        # -----------------------------------------------------------
        # ADD Currency Widget to Grid (Row 7)
        # -----------------------------------------------------------
        grid_layout.addWidget(currency_label, 7, 0, 1, 1)
        grid_layout.addWidget(self.currency_input, 7, 1, 1, 1)
        
        # Initialize currency based on default country
        self.on_country_changed(self.country_combo.currentText())

        # -----------------------------------------------------------
        # JAWWAD : START: Region and SOR Logic Frontend with Backend Integration
        # -----------------------------------------------------------
        
        # JAWWAD : 1. Region Dropdown (Shifted to Row 8)
        region_label = QLabel("Region *")
        region_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(region_label, 8, 0, 1, 1)
        
        self.region_combo = QComboBox(self.general_widget)
        self.region_combo.setStyleSheet(combo_style)
        
        # JAWWAD : Populate region combo from backend if available
        if sor_manager:
            self.region_combo.addItems(sor_manager.get_regions())
            # Connect registry update signal
            sor_manager.registry_updated.connect(self.refresh_ui_options)
        else:
            # Fallback
            self.region_combo.addItems(["India", "USA"])
            
        # JAWWAD : Connect Region change to slot
        self.region_combo.currentTextChanged.connect(self.on_region_changed)
        grid_layout.addWidget(self.region_combo, 8, 1, 1, 1)

        # JAWWAD : 2. Selected SOR Dropdown (Shifted to Row 9)
        sor_label = QLabel("Selected SOR *")
        sor_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(sor_label, 9, 0, 1, 1)
        
        self.sor_combo = QComboBox(self.general_widget)
        self.sor_combo.setStyleSheet(combo_style)
        
        # JAWWAD : Connect SOR change to slot
        self.sor_combo.currentTextChanged.connect(self.on_sor_changed)
        
        # JAWWAD : Trigger initial population of SOR based on default region
        self.on_region_changed(self.region_combo.currentText())
        
        grid_layout.addWidget(self.sor_combo, 9, 1, 1, 1)

        # -----------------------------------------------------------
        # JAWWAD : END Region and SOR Logic
        # -----------------------------------------------------------
        
        # Base Year (Shifted to Row 10)
        label = QLabel("Base Year *")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grid_layout.addWidget(label, 10, 0, 1, 1) 
        self.base_year = QLineEdit(self.general_widget)
        self.base_year.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDCE0;
                border-radius: 10px;
                padding: 3px 10px;
            }
        """)
        grid_layout.addWidget(self.base_year, 10, 1, 1, 1)

        # --- CREATE PROJECT BUTTON (Shifted to Row 11) ---
        self.create_btn = QPushButton("Create Project")
        self.create_btn.setObjectName("create_btn")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self.on_create_clicked)
        
        # Add a container layout for the button to align it right or stretch
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.create_btn)
        
        # Add to grid at Row 11, spanning 2 columns
        grid_layout.addLayout(btn_container, 11, 1, 1, 2)

        scroll_content_layout.insertWidget(1, self.general_widget)
        self.general_widget.show()
        self.general_widget.adjustSize()
        self.original_general_widget_height = self.general_widget.sizeHint().height()
        self.general_widget.hide()
        self.general_widget_animation = QPropertyAnimation(self.general_widget, b"maximumHeight")
        self.general_widget_animation.setDuration(300)
        self.general_widget_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.general_widget.setMaximumHeight(0)
        self.general_widget.hide()
        
        # Input Parameters Section
        self.input_param_unactive_icon = QIcon(":/images/play_button_unselected.png")
        self.input_param_active_icon = QIcon(":/images/arrow_down.png")
        
        # JAWWAD: Define styles for enabled/disabled states
        self.input_param_button_css_inactive = """
            QPushButton#parameter_button {
              background-color: transparent;
                border: 1px solid #000000;
                text-align: left;
                padding: 3px 10px;
                color: #000000;
                font-size: 16px;
            }
            QPushButton#parameter_button:hover {
                background-color: #F0E6E6;
            }
            QPushButton#parameter_button:pressed {
                background-color: #FFF3F3;
                border-color: #606060;
            }
        """
        self.input_param_button_css_active = """
            QPushButton#parameter_button {
                background-color: transparent;
                text-align: left;
                padding: 3px 10px;
                color: #000000;
                font-size: 16px;
                border-top: 1px solid #000000;
                border-left: 1px solid #000000;
                border-right: 1px solid #000000;
            }
            QPushButton#parameter_button:hover {
                background-color: #F0E6E6;
            }
            QPushButton#parameter_button:pressed {
                background-color: #FFF3F3;
            }
        """
        # JAWWAD: New disabled style
        self.input_param_button_css_disabled = """
            QPushButton#parameter_button {
                background-color: #E0E0E0;
                border: 1px solid #B0B0B0;
                text-align: left;
                padding: 3px 10px;
                color: #808080;
                font-size: 16px;
            }
        """

        self.input_param_widget = QWidget()
        self.input_param_widget.setObjectName("input_param_widget")
        self.input_param_widget.setStyleSheet("""
                #input_param_widget{
                        background-color: #FDEFEF;
                        border: 1px solid #000000;
                }
        """)
        self.input_param_layout = QVBoxLayout(self.input_param_widget)
        self.input_param_layout.setContentsMargins(0, 0, 0, 0)
        self.input_param_layout.setSpacing(0)
        
        self.input_param_button = QPushButton("   Input Parameters")
        # JAWWAD: Disable by default
        self.input_param_button.setEnabled(False)
        self.input_param_button.setStyleSheet(self.input_param_button_css_disabled)
        self.input_param_button.setObjectName("parameter_button")
        self.input_param_button.setCursor(Qt.ForbiddenCursor) # Changed to Forbidden
        self.input_param_button.clicked.connect(self.input_button_toggle)
        self.input_param_button.setIcon(self.input_param_unactive_icon)
        self.input_param_button.setIconSize(QSize(10, 10))
        self.input_param_button.setLayoutDirection(Qt.LeftToRight)
        
        self.input_param_layout.addWidget(self.input_param_button)
        self.input_param_option_widget = QWidget()
        self.input_param_option_widget.hide()
        self.input_option_active = False
        self.input_param_option_widget.setObjectName("input_param_option_widget")
        self.input_param_option_layout = QVBoxLayout(self.input_param_option_widget)
        self.input_param_option_layout.setContentsMargins(8, 8, 8, 8)
        self.input_param_option_layout.setSpacing(2)
        button_labels = [
            KEY_STRUCTURE_WORKS_DATA,
            KEY_FINANCIAL,
            KEY_CARBON_EMISSION,
            KEY_BRIDGE_TRAFFIC,
            KEY_MAINTAINANCE_REPAIR,
            KEY_DEMOLITION_RECYCLE
        ]
        self.selected_icon = QIcon(":/images/play_button_selected.png")
        self.param_buttons = []
        for label in button_labels:
            display_text = label
            # Change name of "Structure Works Data" to "Construction work data"
            if label == KEY_STRUCTURE_WORKS_DATA:
                display_text = "Construction work data"
                
            btn = QPushButton(f"   {display_text}")
            # Ensure the object name is set for styling, but we keep the text as requested
            btn.setObjectName("parameter_button")
            btn.setIcon(QIcon(":/images/play_button_unselected.png"))
            btn.setIconSize(QSize(10, 10))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setLayoutDirection(Qt.LeftToRight)
            btn.setStyleSheet("""
                QPushButton#parameter_button {
                    background-color: none;
                    border: none;
                    text-align: left;
                    padding: 2px 10px;
                    color: #000;
                    font-size: 12px;
                    margin-left: 40px
                }
                QPushButton#parameter_button:hover {
                    background-color: #F0E6E6;
                }
            """)
            btn.clicked.connect(lambda checked, b=btn: self.select_param_button(b))
            self.input_param_option_layout.addWidget(btn)
            self.param_buttons.append(btn)
        self.input_param_layout.addWidget(self.input_param_option_widget)
        scroll_content_layout.insertWidget(2, self.input_param_widget)
        
        self.output_button = QPushButton("   Outputs")
        self.output_button.setObjectName("output_button")
        self.output_button.setIcon(QIcon(":/images/play_button_unselected.png"))
        self.output_button.setIconSize(QSize(10, 10))
        self.output_button.setLayoutDirection(Qt.LeftToRight)
        
        # JAWWAD: Disable by default
        self.output_button.setEnabled(False)
        self.output_button.setCursor(Qt.ForbiddenCursor)
        self.output_button.setStyleSheet("""
            QPushButton#output_button {
                background-color: #E0E0E0;
                border: 1px solid #B0B0B0;
                text-align: left;
                padding: 3px 10px;
                color: #808080;
                font-size: 14px;
            }
        """)

        scroll_content_layout.insertWidget(3, self.output_button)
        left_panel_vlayout.addWidget(self.scroll_area)
        self.bottom_widget = QWidget()
        self.bottom_widget.setObjectName("bottom_widget")
        self.bottom_widget.setStyleSheet("""
            #bottom_widget {
                background-color: #F0E6E6;
                border-left: 1px solid #000000;
                border-bottom: 1px solid #000000;
                border-right: 1px solid #000000;
            }
        """)
        left_panel_vlayout.addWidget(self.bottom_widget)
        self.general_info_button.clicked.connect(self.expand_general_area)

    # --- PROJECT CREATION LOGIC ---

    def on_create_clicked(self):
        """Collects data from form fields and calls backend to create project."""
        # 1. Validation
        if not self.company_name.text().strip() or not self.project_title.text().strip():
            QMessageBox.warning(self, "Required Fields", "Company Name and Project Title are required!")
            return
            
        if not self.base_year.text().strip():
             QMessageBox.warning(self, "Required Fields", "Base Year is required!")
             return

        # 2. Gather Data
        data = {
            "company_name": self.company_name.text(),
            "project_title": self.project_title.text(),
            "description": self.description.toPlainText(),
            "valuer": self.valuer_name.text(),
            "job_number": self.job_number.text(),
            "client": self.client_name.text(),
            "country": self.country_combo.currentText(),
            "currency": self.currency_input.text(),  # Dynamic Currency Input
            "region": self.region_combo.currentText(),
            "sor": self.sor_combo.currentText(),
            "base_year": self.base_year.text()
        }

        # 3. Call Backend
        self.create_btn.setText("Creating...")
        self.create_btn.setEnabled(False)
        
        if self.creator:
            self.creator.create_new_project(data)
        else:
            # Fallback if backend missing
            print("Mock Data Submitted:", data)
            QMessageBox.information(self, "Mock Mode", "Backend not connected. Data printed to console.")
            self.create_btn.setText("Create Project")
            self.create_btn.setEnabled(True)

    @Slot(str)
    def on_creation_success(self, uuid):
        self.create_btn.setText("Success!")
        self.create_btn.setEnabled(False) # Disable create button to prevent double-creation
        
        QMessageBox.information(self, "Success", f"Project Created Successfully!\nID: {uuid}")
        
        # JAWWAD: Enable Input and Output parameters now
        self.enable_project_features()
        
        self.projectCreated.emit(uuid)
        
        # JAWWAD: DEBUG INFO
        # This confirms emission. Ensure your MainWindow connects this signal to Foundation.set_project_id()!
        print(f"Signal 'projectCreated' emitted with UUID: {uuid}")

    @Slot(str)
    def on_creation_error(self, msg):
        self.create_btn.setText("Create Project")
        self.create_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Failed to create project:\n{msg}")

    # JAWWAD: Helper to enable features
    def enable_project_features(self):
        # Enable Input Parameters
        self.input_param_button.setEnabled(True)
        self.input_param_button.setCursor(Qt.PointingHandCursor)
        self.input_param_button.setStyleSheet(self.input_param_button_css_inactive)
        
        # Enable Outputs
        self.output_button.setEnabled(True)
        self.output_button.setCursor(Qt.PointingHandCursor)
        self.output_button.setStyleSheet("""
             QPushButton#output_button {
                background-color: #FDEFEF;
                border: 1px solid #000000;
                text-align: left;
                padding: 3px 10px;
                color: #000000;
                font-size: 14px;
            }
            QPushButton#output_button:hover {
                background-color: #F0E6E6;
                border: 1px solid #000000;
            }
            QPushButton#output_button:pressed {
                background-color: #FFF3F3;
                border-color: #606060;
            }
        """)

        # Optional: Collapse General Info to show progress
        if self.general_button_active:
            self.expand_general_area() 

    # --- EXISTING LOGIC ---

    # JAWWAD : NEW METHOD: Handle Country Changes to update Currency
    @Slot(str)
    def on_country_changed(self, country_name):
        """Update the Currency field based on the selected Country."""
        # Retrieve currency from map, default to "USD" if not found
        currency = self.COUNTRY_CURRENCY_MAP.get(country_name, "USD")
        self.currency_input.setText(currency)

    # JAWWAD : NEW METHOD: Auto-Refresh UI Options from backend
    @Slot() 
    def refresh_ui_options(self):
        """Called automatically when SOR backend updates."""
        print("UI: Refreshing Region/SOR dropdowns in Project Details...")
        
        # Save current selection to restore it after refresh if possible
        current_region = self.region_combo.currentText()
        current_sor = self.sor_combo.currentText()
        
        # Reload Regions
        self.region_combo.blockSignals(True)
        self.region_combo.clear()
        if sor_manager:
            self.region_combo.addItems(sor_manager.get_regions())
        else:
            self.region_combo.addItems(["India", "USA"])
        self.region_combo.blockSignals(False)
        
        # Restore Region Selection
        idx = self.region_combo.findText(current_region)
        if idx != -1:
            self.region_combo.setCurrentIndex(idx)
        elif self.region_combo.count() > 0:
            self.region_combo.setCurrentIndex(0)
            
        # Trigger update for SOR list based on the (potentially new) region
        self.on_region_changed(self.region_combo.currentText())
        
        # Restore SOR Selection
        idx_sor = self.sor_combo.findText(current_sor)
        if idx_sor != -1:
            self.sor_combo.setCurrentIndex(idx_sor)

    # JAWWAD : NEW METHOD: Handle Region Changes
    def on_region_changed(self, new_region):
        """Update SOR dropdown when Region changes"""
        if not sor_manager: return
        sors = sor_manager.get_sors_for_region(new_region)
        self.sor_combo.blockSignals(True)
        self.sor_combo.clear()
        self.sor_combo.addItems(sors)
        self.sor_combo.blockSignals(False)
        # Trigger update for the first SOR in the new list if available
        if sors:
            self.sor_combo.setCurrentIndex(0)
            self.on_sor_changed(sors[0])

    # JAWWAD : NEW METHOD: Handle SOR Changes
    def on_sor_changed(self, new_sor):
        """Tell backend to load new data when SOR changes"""
        if not sor_manager or not new_sor: return
        region = self.region_combo.currentText()
        success, msg = sor_manager.set_active_sor(region, new_sor)
        if success:
            print(f"UI: Successfully loaded {new_sor}")
        else:
            print(f"UI: Failed to load {new_sor}: {msg}")

    def expand_general_area(self):
        try:
            self.general_widget_animation.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        if self.general_button_active:
            self.general_info_button.setIcon(self.unactive_arrow_icon)
            self.general_widget_animation.setStartValue(self.general_widget.height())
            self.general_widget_animation.setEndValue(0)
            self.general_widget_animation.finished.connect(self.general_widget.hide)
            self.general_button_active = False
        else:
            self.general_info_button.setIcon(self.active_arrow_icon)
            self.general_widget.show()
            self.general_widget_animation.setStartValue(0)
            self.general_widget_animation.setEndValue(self.original_general_widget_height)
            self.general_widget_animation.finished.connect(lambda: self.general_widget.setMaximumHeight(16777215))
            self.general_button_active = True
        self.general_widget_animation.start()

    def input_button_toggle(self):
        if self.input_option_active:
            self.input_param_option_widget.hide()
            self.input_param_button.setStyleSheet(self.input_param_button_css_inactive)
            self.input_param_button.setIcon(self.input_param_unactive_icon)
            self.input_option_active = False
        else:
            self.input_param_option_widget.show()
            self.input_option_active = True
            self.input_param_button.setStyleSheet(self.input_param_button_css_active)
            self.input_param_button.setIcon(self.input_param_active_icon)

    def select_param_button(self, selected_btn):
        for btn in self.param_buttons:
            if btn == selected_btn:
                btn.setIcon(self.selected_icon)
            else:
                btn.setIcon(QIcon(":/images/play_button_unselected.png"))

    def close_widget(self):
        self.closed.emit()
        self.setParent(None)