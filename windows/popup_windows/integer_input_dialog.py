from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QPushButton, QWidget
)
from PySide6.QtCore import Qt
from typing import List, Tuple, Optional
import sys


class IntegerInputDialog(QDialog):
    """
    A dialog window with multiple integer input fields.
    Each field has a label, configurable bounds, and returns user input.
    """
    
    def __init__(self, fields: List[Tuple[str, int, int, int]], 
                 title: str = "Input Dialog",
                 ok_button_text="Ok",
                 parent: Optional[QWidget] = None):
        """
        Initialize the dialog with specified fields.
        
        Args:
            fields: List of tuples (label, min_value, max_value) for each field
            title: Window title
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.spin_boxes = []
        self.values = None
        
        # Create main layout
        main_layout = QVBoxLayout()
        
        # Create input fields
        for label_text, min_val, max_val, init_val in fields:
            # Create horizontal layout for each field
            field_layout = QHBoxLayout()
            
            # Create label
            label = QLabel(label_text)
            label.setMinimumWidth(150)
            field_layout.addWidget(label)
            
            # Create spin box
            spin_box = QSpinBox()
            spin_box.setMinimum(min_val)
            spin_box.setMaximum(max_val)
            spin_box.setValue(init_val)
            # spin_box.setValue(min_val)  # Set default to minimum value
            spin_box.setMinimumWidth(100)
            field_layout.addWidget(spin_box)
            
            # Add to list for later retrieval
            self.spin_boxes.append(spin_box)
            
            # Add field layout to main layout
            main_layout.addLayout(field_layout)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Create OK button
        ok_button = QPushButton(ok_button_text)
        ok_button.clicked.connect(self.accept_values)
        button_layout.addWidget(ok_button)
        
        # Create Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
        
        # Set the layout
        self.setLayout(main_layout)
    
    def accept_values(self):
        """Collect values and close the dialog with accept status."""
        self.values = [spin_box.value() for spin_box in self.spin_boxes]
        self.accept()
    
    def get_values(self) -> Optional[List[int]]:
        """
        Show the dialog and return the values entered by the user.
        
        Returns:
            List of integers if OK was clicked, None if canceled
        """
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self.values
        return None


# # Example usage
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
    
#     # Define fields: (label, min_value, max_value)
#     fields = [
#         ("Age:", 0, 120),
#         ("Height (cm):", 50, 250),
#         ("Weight (kg):", 20, 300),
#         ("Score:", 0, 100),
#     ]
    
#     # Create and show dialog
#     dialog = IntegerInputDialog(
#         fields=fields,
#         title="Enter Your Information"
#     )
    
#     values = dialog.get_values()
    
#     if values is not None:
#         print("Values entered:")
#         for i, (label, _, _) in enumerate(fields):
#             print(f"  {label} {values[i]}")
#     else:
#         print("Dialog was canceled")
    
#     sys.exit(0)
# # 
