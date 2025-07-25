from PyQt5.QtWidgets import QMainWindow, QTabWidget
from PyQt5.QtCore import Qt, QTimer

from ui.rozbiorki_view import rozbiorkaView
from ui.pelne_flakony_view import PelneFlakonyView
from ui.gotowe_odlewki_view import GotoweOdlewkiView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Organizer Zamówień")
        self.setWindowState(Qt.WindowMaximized)  # Maksymalizuj po otwarciu

        # Główny widget z zakładkami
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)
        tabs.setMovable(True)

        # Tworzenie trzech głównych widoków
        self.rozbiorki_view = rozbiorkaView()
        self.pelne_flakony_view = PelneFlakonyView()
        self.gotowe_odlewki_view = GotoweOdlewkiView()

        # Dodanie zakładek
        tabs.addTab(self.rozbiorki_view, "Rozbiórki")
        tabs.addTab(self.pelne_flakony_view, "Pełne flakony")
        tabs.addTab(self.gotowe_odlewki_view, "Gotowe odlewki")

        self.setCentralWidget(tabs)

        # Dopasuj do ekranu przy starcie oraz przy każdym resize
        QTimer.singleShot(10, self.resize_to_screen)

    def resize_to_screen(self):
        desktop = self.screen().geometry()
        self.resize(desktop.width(), desktop.height())
