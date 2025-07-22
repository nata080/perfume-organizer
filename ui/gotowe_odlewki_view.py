# ui/gotowe_odlewki_view.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class GotoweOdlewkiView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        # Placeholder content
        label = QLabel("Widok Gotowe odlewki - w przygotowaniu")
        label.setStyleSheet("font-size: 16px; padding: 20px; color: #666;")
        layout.addWidget(label)
        
        self.setLayout(layout)
