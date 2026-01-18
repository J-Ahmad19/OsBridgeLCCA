
"""
Main application window for Osdag GUI.
Handles tab management, docking icons, and main window controls.
"""
from osbridgelcca.desktop_app.resources.resources_rc import *

from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Signal

import sys
import os, yaml
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QApplication, QFileDialog,
    QMainWindow, QTabBar, QTabWidget,
)
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QTimer
from PySide6.QtGui import QIcon, QGuiApplication, QPixmap

from osbridgelcca.desktop_app.widgets.home.home_widget import HomeWidget
from osbridgelcca.desktop_app.widgets.home.custom_messagebox import CustomMessageBox, MessageBoxType

class HomeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.main_widget_instance = None
        self.setWindowIcon(QIcon(":/images/3pslcc_logo.png"))
        self.setCursor(Qt.CursorShape.ArrowCursor)
        # Apply global QToolTip stylesheet here

        screen = QGuiApplication.primaryScreen()
        screen_size = screen.availableGeometry()

        screen_width = screen_size.width()
        screen_height = screen_size.height()

        # Calculate window size
        window_width = int(7 * screen_width / 10)
        window_height = int((7 * screen_height) / 8)

        # Set window size
        self.resize(window_width, window_height)

        # Center the window
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)

        self.setGeometry(x, y, window_width, window_height)
        self.setWindowFlags(Qt.FramelessWindowHint) # Make the window frameless for custom buttons
        self.current_tab_index = 0 # To keep track of the next tab index
        self.btn_size = QSize(46, 30)

        # Initialize UI first, as sidebar will overlay it
        self.init_ui() # Call init_ui before sidebar creation to ensure main content exists
        self.handle_add_tab("Home")

        # Using QTimer to delay maximizing until after the window is fully initialized
        # Before maximizing, so that when we click on Restore it comes to normal state.
        QTimer.singleShot(0, self.showMaximized)


    def init_ui(self):
        # Main Vertical Layout for the entire window's *content*
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_v_layout = QVBoxLayout(central_widget)
        main_v_layout.setContentsMargins(1, 0, 1, 1)
        main_v_layout.setSpacing(0)

        # --- Top HBox Layout (Contains logo, tabs, and window control buttons) ---
        top_h_layout = QHBoxLayout()
        top_h_layout.setContentsMargins(0, 0, 0, 0)
        top_h_layout.setSpacing(0)

        icon_label_widget = QWidget()
        icon_label_h_layout = QHBoxLayout(icon_label_widget)
        icon_label_h_layout.setContentsMargins(5, 0, 5, 0)
        icon_label_h_layout.setSpacing(0)

        # SVG Widget (Dummy SVG for demonstration)
        self.svg_widget = QSvgWidget()
        self.svg_widget.load(":/vectors/LCC_logo.svg")
        self.svg_widget.setFixedSize(18, 18)

        icon_label_h_layout.addWidget(self.svg_widget)
        top_h_layout.addWidget(icon_label_widget)
        
        # Keep a reference for event filtering (double-click to maximize/restore)
        self.icon_label_widget = icon_label_widget

        tabs_h_layout = QHBoxLayout()
        tabs_h_layout.setSpacing(0)
        tabs_h_layout.setContentsMargins(0, 2, 0, 0)

        # QTabBar
        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName("main_tabs")
        self.tab_bar.setExpanding(False)
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(False)
        self.tab_bar.tabCloseRequested.connect(self.handle_close_tab)
        tabs_h_layout.addWidget(self.tab_bar)
        top_h_layout.addLayout(tabs_h_layout)
        
        # Install event filters for double-click maximize/restore on title widgets
        self.tab_bar.installEventFilter(self)
        self.icon_label_widget.installEventFilter(self)

        # Stretch to push buttons to the right
        top_h_layout.addStretch(1)

        # Helper function to create a styled button
        def create_button(icon_svg, is_close=False):
            btn = QPushButton()
            btn.setFixedSize(self.btn_size)
            btn.setIcon(QIcon(QPixmap.fromImage(QPixmap(icon_svg).toImage())))
            btn.setIconSize(QSize(14, 14))
            if is_close:
                btn.setObjectName("close_button")
            else:
                btn.setObjectName("window_control_button")
            return btn

        self.minimize_button = create_button(":/vectors/window_minimize_light.svg")
        self.minimize_button.clicked.connect(self.showMinimized)
        top_h_layout.addWidget(self.minimize_button)

        self.maximize_button = create_button(":/vectors/window_maximize_light.svg")
        self.maximize_button.clicked.connect(self.toggle_maximize_restore)
        top_h_layout.addWidget(self.maximize_button)

        self.close_button = create_button(":/vectors/window_close_light.svg", is_close=True)
        self.close_button.clicked.connect(self.close)
        top_h_layout.addWidget(self.close_button)

        self.start_pos = None
        self.start_geometry = None

        # Add top HBox to main VBox
        main_v_layout.addLayout(top_h_layout)

        # QTabWidget
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()
        self.tab_widget.setTabsClosable(True) # Allow closing tabs
        self.tab_widget.setMovable(False) # Allow reordering tabs
        self.tab_widget_content = []
        self.tab_widget.tabCloseRequested.connect(self.handle_close_tab)
        main_v_layout.addWidget(self.tab_widget)

        # Connect the QTabBar to custom handler
        self.tab_bar.currentChanged.connect(self.handle_tab_change)

        # Ensure initial synchronization
        if self.tab_bar.count() > 0:
            self.tab_widget.setCurrentIndex(self.tab_bar.currentIndex())

    def paintEvent(self, event):
        if self.isMaximized():
            self.maximize_button.setIcon(QIcon(QPixmap.fromImage(QPixmap(":/vectors/window_restore_light.svg").toImage())))
        else:
            self.maximize_button.setIcon(QIcon(QPixmap.fromImage(QPixmap(":/vectors/window_maximize_light.svg").toImage())))
        super().paintEvent(event)

    def set_maximize_icon(self):
        self.maximize_button.setIcon(QIcon(QPixmap.fromImage(QPixmap(":/vectors/window_maximize_light.svg").toImage())))

    def set_restore_icon(self):
        self.maximize_button.setIcon(QIcon(QPixmap.fromImage(QPixmap(":/vectors/window_restore_light.svg").toImage())))
        
    def toggle_maximize_restore(self):
        """Toggles between maximized and normal window states and updates the icon."""
        if self.isMaximized():
            self.showNormal()
            self.set_maximize_icon()
        else:
            self.showMaximized()
            self.set_restore_icon()

    def add_new_tab(self, module):
        """Helper to add a new tab to QTabWidget."""
        body_widget = QWidget()

        # Create and set layout for body_widget first
        self.main_widget_layout = QHBoxLayout(body_widget)
        self.main_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.main_widget_layout.setSpacing(0)

        # it initially sets the home on the Tab
        self.open_home_page(module)
        # Widget of the Module
        self.tab_widget_content.append(body_widget)
        self.tab_widget.addTab(body_widget, f"Tab {self.current_tab_index + 1}")
        # Update main_widget_layout to the layout of the new tab's body_widget
        if hasattr(body_widget, 'layout'):
            self.main_widget_layout = body_widget.layout()

    def handle_add_tab(self, module):
        """Handles the 'Add New Tab' button click."""
        self.current_tab_index += 1
        self.tab_bar.addTab("Home") # Add to tab bar
        # Set the newly added tab as current
        self.add_new_tab(module) # Add to tab widget
        
        new_index = self.tab_bar.count() - 1
        self.tab_bar.setCurrentIndex(new_index)
        self.tab_widget.setCurrentIndex(new_index)

    def handle_tab_change(self, index):
        # Switch the QTabWidget to the new tab
        if index < len(self.tab_widget_content) and index >= 0:
            self.tab_widget.setCurrentIndex(index)

            # Update main_widget_instance to the main widget in the current tab
            body_widget = self.tab_widget_content[index]
            if hasattr(body_widget, 'layout') and body_widget.layout().count() > 0:
                widget_item = body_widget.layout().itemAt(0)
                if widget_item is not None:
                    widget = widget_item.widget()
                    if widget is not None:
                        self.main_widget_instance = widget
            # Update main_widget_layout to the layout of the current tab's body_widget
            if hasattr(body_widget, 'layout'):
                self.main_widget_layout = body_widget.layout()

    # This is triggered by Quit button in Menu bar on template_page
    def close_current_tab(self):
        current_index = self.tab_bar.currentIndex()
        self.handle_close_tab(current_index)

    # General closing function
    def handle_close_tab(self, index):

        tab_title = self.tab_bar.tabText(index) if index >= 0 else "Module"
        is_last_tab = self.tab_widget.count() == 1
        to_save = self._check_design_done(index)
        module = self._get_template_instance(index)
        
        if to_save and is_last_tab:
            result = CustomMessageBox(
                title="Confirm Exit",
                text=(
                    f"'{tab_title}' is the last tab.\n"
                     "Closing it will exit Osdag.\n"
                    f"Do you want to save your '{tab_title}' design before closing?"
                ),
                buttons=["Save and Exit", "Exit Without Saving", "Cancel"]
            ).exec()
            
            if result == "Save and Exit":
                # Call Save Function
                module.saveDesign_inputs()
                # Exit Osdag
                self.close()
            elif result == "Exit Without Saving":
                # Exit Osdag
                self.close()
        
        elif to_save:
            result = CustomMessageBox(
                title="Save Design",
                text=f" Do you want to Save Your '{tab_title}' design before closing?",
                buttons=["Yes", "No"],
                dialogType=MessageBoxType.Warning,
            ).exec()

            if result == "Yes":
                # Call Save Function
                module.saveDesign_inputs()
                self._close_tab(index)
            elif result == "No":
                # Close Tab
                self._close_tab(index)

        elif is_last_tab:
            result = CustomMessageBox(
                title="Confirm Exit",
                text=f"'{tab_title}' is the last tab.\nClosing it will exit Osdag.\nDo you really want to close this tab?",
                buttons=["Yes", "No"],
                dialogType=MessageBoxType.Warning,
            ).exec()

            # Handle result
            if result == "Yes":
                self.close()  # Close the main window (exit Osdag)
        else:
            self._close_tab(index)

    # Check if design is created in the module or not
    def _check_design_done(self, index) -> bool:
        module = self._get_template_instance(index)
        if hasattr(module, 'backend'):
            return module.backend.design_status
        else:
            return False

    
    def _get_template_instance(self, index) -> object:
        return self.tab_widget_content[index].layout().itemAt(0).widget()

    def clear_layout(self, layout):
        """Properly clear layout with signal disconnection and widget cleanup."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                try:
                    widget.setUpdatesEnabled(False)
                    widget.blockSignals(True)
                    widget.hide()
                    
                    # Disconnect specific signals if they exist
                    signals = ['openNewTab', 'downloadDatabase', 'triggerLoadOsi',
                            'openProject', 'openModule', 'cardOpenClicked']
                    
                    for sig in signals:
                        if hasattr(widget, sig):
                            try:
                                getattr(widget, sig).disconnect()
                            except:
                                pass
                    
                    widget.setParent(None)
                    widget.deleteLater()
                except (RuntimeError, TypeError):
                    pass
            else:
                sub_layout = item.layout()
                if sub_layout:
                    self.clear_layout(sub_layout)
                    sub_layout.deleteLater()

    def _cleanup_scroll_area(self, scroll_area):
        """Special cleanup for QScrollArea widgets."""
        from PySide6.QtWidgets import QScrollArea
        
        if not isinstance(scroll_area, QScrollArea):
            return
        
        try:
            # Get and clean the viewport widget
            viewport = scroll_area.viewport()
            if viewport:
                viewport_widget = scroll_area.widget()
                if viewport_widget:
                    self.delete_all_children(viewport_widget)
                    viewport_widget.setParent(None)
                    viewport_widget.deleteLater()
                
                # Clear the scroll area
                scroll_area.setWidget(None)
                
        except (RuntimeError, AttributeError) as e:
            print(f"[ERROR] Error cleaning scroll area: {e}")

    def _close_tab(self, index):
        """Close tab with comprehensive cleanup."""
        widget = self.tab_widget.widget(index)
                
        template_instance = self._get_template_instance(index)
        
        if template_instance:
            try:
                # Disable updates immediately
                template_instance.setUpdatesEnabled(False)
                template_instance.blockSignals(True)
                template_instance.hide()
                
                # Find and clean all scroll areas first (they create the container widgets)
                from PySide6.QtWidgets import QScrollArea
                scroll_areas = template_instance.findChildren(QScrollArea)
                for scroll_area in scroll_areas:
                    self._cleanup_scroll_area(scroll_area)
                
                # Recursively delete all children
                self.delete_all_children(template_instance)
                
                # Finally delete the template instance itself
                template_instance.setParent(None)
                template_instance.deleteLater()
                        
            except (RuntimeError, AttributeError) as e:
                print(f"[ERROR] Error in pre-cleanup: {e}")
        
        # Remove from UI structures
        self.tab_widget.removeTab(index)
        self.tab_bar.removeTab(index)
        self.tab_widget_content.pop(index)
        
        if widget:
            widget.setParent(None)
            widget.deleteLater()
        
        self._synchronize_tab_widget()
        
        # Force immediate processing of deferred deletions
        QApplication.processEvents()
        
        # Force garbage collection
        import gc
        gc.collect()
    
    def delete_all_children(self, widget):
            """
            Recursively delete all child widgets of the given widget.
            Traverses depth-first, deleting only QWidget children on the way back up.
            """
            from PySide6.QtWidgets import QWidget
            
            # Get all immediate children
            children = widget.children()
            
            # Recursively process each child
            for child in children:
                # Only process QWidget instances
                if isinstance(child, QWidget):
                    # First, recursively delete this child's children
                    self.delete_all_children(child)
                    
                    # Then delete this child itself
                    child.deleteLater()

    def _synchronize_tab_widget(self):
        current_index = self.tab_bar.currentIndex()
        self.tab_widget.setCurrentIndex(current_index)
        # Update global variables and icons
        body_widget = self.tab_widget_content[current_index]
        if hasattr(body_widget, 'layout') and body_widget.layout().count() > 0:
            widget = body_widget.layout().itemAt(0).widget()
            self.main_widget_instance = widget
        # Ensure main_widget_layout points to the currently active tab's layout
        if hasattr(body_widget, 'layout'):
            self.main_widget_layout = body_widget.layout()

    # Allow dragging the window when frameless
    def mousePressEvent(self, event):
        # The draggable area is the combined height of the top_h_layout (tab bar + buttons) and the menu_bar
        if self.isMaximized():
            return
        draggable_height = self.tab_bar.height() + (self.layout().contentsMargins().top() * 2) # Account for potential margins/spacing
        # A more robust way might be to check if the cursor is within the bounding box of top_h_layout or menu_bar
        if event.button() == Qt.LeftButton and event.position().y() < draggable_height:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.isMaximized():
            return
        if hasattr(self, 'old_pos'):
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if self.isMaximized():
            return
        if event.button() == Qt.LeftButton:
            if hasattr(self, 'old_pos'):
                del self.old_pos
        
        # restore holding cursor so cursor can update
        self.unsetCursor()
        QApplication.restoreOverrideCursor()
        self.releaseMouse()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Toggle maximize/restore when double-clicking in the draggable title area
        if event.button() == Qt.LeftButton:
            draggable_height = self.tab_bar.height() + (self.layout().contentsMargins().top() * 2)
            if event.position().y() < draggable_height:
                self.toggle_maximize_restore()

    def eventFilter(self, obj, event):
        # Handle double-click on title widgets (e.g., tab bar, logo area)
        if event.type() == QEvent.MouseButtonDblClick:
            if event.button() == Qt.LeftButton:
                self.toggle_maximize_restore()
                return True
        return super().eventFilter(obj, event)

    def handle_card_open_clicked(self, card_title):
        # print(f"[INFO] Card opened: {card_title}")

        if card_title == "Fin Plate":
            self.open_fin_plate_shear_conn()

    #-------------Functions-to-load-modules-in-Tabwidget-START---------------------------

    def open_home_page(self, module):
        self.clear_layout(self.main_widget_layout)
        home_widget = HomeWidget()
        home_widget.createNewProject.connect(self.openNewProject)
        self.main_widget_instance = home_widget
        self.main_widget_layout.addWidget(home_widget)
    
    def openNewProject(self):
        from osbridgelcca.desktop_app.main_template import UiMainWindow
        class LCCA(QMainWindow):
            def __init__(self):
                super().__init__()
                self.ui = UiMainWindow()
                self.ui.setupUi(self)

        app = QApplication.instance()
        app.home_window.close()
        app.main_window = LCCA()
        app.setStyleSheet(None)
        app.main_window.show()

# if __name__ == "__main__":
#     import sys, os
#     sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#     from PySide6.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     main_window = HomeWindow()
#     main_window.show()
#     sys.exit(app.exec())
