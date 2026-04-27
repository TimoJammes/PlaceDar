from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
import sys

class InputWindow(QDialog):
    def __init__(self, label, allowed_chars="[A-Za-z0-9]*", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Required")
        self.setFixedSize(300, 120)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add question label
        self.label = QLabel(label)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        
        # Add input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type here...")
        
        # Set validator to allow only letters and numbers (example)
        # Change the regex pattern to allow different characters
        validator = QRegularExpressionValidator(QRegularExpression(allowed_chars))
        self.input_field.setValidator(validator)
        
        layout.addWidget(self.input_field)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Add OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        # Add Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def get_input(self):
        return self.input_field.text()
