"""
Entry point for GUI application.
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase, QFont
from PySide6.QtCore import QFile, QTextStream
from osbridgelcca.desktop_app.resources.resources_rc import *

def main():
    
    app = QApplication(sys.argv)
    icon = QIcon(":/images/3pslcca_logo.ico")
    app.setWindowIcon(icon)
    
    file = QFile(":/themes/lightstyle.qss")
    if file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(file)
        stylesheet = stream.readAll()
        file.close()
        app.setStyleSheet(stylesheet)

    from osbridgelcca.desktop_app.home_window import HomeWindow
    app.home_window = HomeWindow()
    app.home_window.setWindowIcon(icon)
    app.home_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
