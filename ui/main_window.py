# ui/main_window.py

from PyQt5.QtWidgets import QMainWindow, QTabWidget

from ui.rozbiorki_view import rozbiorkaView
from ui.pelne_flakony_view import PelneFlakonyView
from ui.gotowe_odlewki_view import GotoweOdlewkiView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Organizer Zamówień")
        self.resize(1200, 700)
        
        # Główny widget z zakładkami
        tabs = QTabWidget()
        
        # Tworzenie trzech głównych widoków
        self.rozbiorki_view = rozbiorkaView()
        self.pelne_flakony_view = PelneFlakonyView()
        self.gotowe_odlewki_view = GotoweOdlewkiView()
        
        # Dodanie zakładek
        tabs.addTab(self.rozbiorki_view, "Rozbiórki")
        tabs.addTab(self.pelne_flakony_view, "Pełne flakony")
        tabs.addTab(self.gotowe_odlewki_view, "Gotowe odlewki")
        
        self.setCentralWidget(tabs)
