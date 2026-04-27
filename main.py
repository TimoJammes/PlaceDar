from PySide6.QtWidgets import QApplication
import sys

from windows.point_selector_window import PointSelectorWindow

def main():
    app = QApplication(sys.argv)
        
    window = PointSelectorWindow()
    window.showMaximized()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
