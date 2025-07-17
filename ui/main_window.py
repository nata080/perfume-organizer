from PyQt5.QtWidgets import QMainWindow, QTabWidget, QWidget, QApplication
from PyQt5.QtGui import QIcon

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Organizer Zamówień")
        self.setGeometry(100, 100, 900, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(QWidget(), "Perfumy")
        self.tabs.addTab(QWidget(), "Zamówienia")
        self.tabs.addTab(QWidget(), "Wysyłka")
        self.tabs.addTab(QWidget(), "Wiadomości")
        self.tabs.addTab(QWidget(), "Statystyki")
