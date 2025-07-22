# ui/rozbiorki_view.py

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout

from ui.perfumes_view import PerfumesView
from ui.orders_view import OrdersView

class rozbiorkaView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        # Podział na dwie zakładki: Perfumy i Zamówienia
        sub_tabs = QTabWidget()
        
        self.perfumes_view = PerfumesView()
        self.orders_view = OrdersView(self.perfumes_view)
        
        sub_tabs.addTab(self.perfumes_view, "Perfumy")
        sub_tabs.addTab(self.orders_view, "Zamówienia")
        
        layout.addWidget(sub_tabs)
        self.setLayout(layout)
