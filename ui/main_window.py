# ui/main_window.py

from PyQt5.QtWidgets import QMainWindow, QTabWidget
from ui.perfumes_view import PerfumesView
from ui.orders_view import OrdersView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Organizer Zamówień")
        self.resize(1000,600)
        tabs=QTabWidget()
        self.perfumes_view=PerfumesView()
        self.orders_view=OrdersView(self.perfumes_view)
        tabs.addTab(self.perfumes_view,"Perfumy")
        tabs.addTab(self.orders_view,"Zamówienia")
        self.setCentralWidget(tabs)
