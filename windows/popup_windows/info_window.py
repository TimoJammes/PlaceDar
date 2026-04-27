from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
import sys

class InfoWindow(QDialog):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Information")
        self.setMinimumWidth(300)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add info label
        self.label = QLabel(label)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(self.label)
        
        # Add stretch to push button to bottom
        layout.addStretch()
        
        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Add OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)  # Makes Enter key work
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        button_layout.addStretch()
        # Adjust size to content
        self.adjustSize()
