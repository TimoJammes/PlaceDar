from PySide6.QtWidgets import QWidget, QPushButton, QMenu, QWidgetAction, QCheckBox, QVBoxLayout
from PySide6.QtCore import Signal

class CheckableDropdown(QWidget):
    item_checked_changed = Signal(str, bool)
    
    def __init__(self, display_text="Layers", parent=None):
        super().__init__(parent)
        self._display_text = display_text
        self.checkboxes = {}
        
        self.button = QPushButton(display_text, self)
        self.menu = QMenu(self)
        self.button.setMenu(self.menu)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)
    
    def add_item(self, text):
        """Add a checkable item"""
        checkbox = QCheckBox(text)
        checkbox.stateChanged.connect(lambda state, t=text: 
            self.item_checked_changed.emit(t, state == 2))  # 2 = Qt.Checked
        
        action = QWidgetAction(self.menu)
        action.setDefaultWidget(checkbox)
        self.menu.addAction(action)
        
        self.checkboxes[text] = checkbox
        
        return checkbox
    
    def item_checked_by_name(self, text):
        """Check if item is checked by name"""
        if text in self.checkboxes:
            return self.checkboxes[text].isChecked()
        return False
    
    def get_checked_items(self):
        """Get list of checked item names"""
        return [text for text, cb in self.checkboxes.items() if cb.isChecked()]
