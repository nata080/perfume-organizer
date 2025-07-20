from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout
from models.database import Session
from models.order import Order
from models.perfume import Perfume
from models.order_item import OrderItem
from ui.add_order_dialog import AddOrderDialog

class OrdersView(QWidget):
    def __init__(self):
        super().__init__()
        self.session = Session()
        self.layout = QVBoxLayout(self)
        
        add_btn = QPushButton("Dodaj zamówienie")
        add_btn.clicked.connect(self.open_new_order)
        self.layout.addWidget(add_btn)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Kupujący", "Perfumy", "Kwota", "Wysyłka", "Stan", "Data sprzedaży"
        ])
        self.layout.addWidget(self.table)
        self.load_orders()

    def load_orders(self):
        self.table.setRowCount(0)
        orders = self.session.query(Order).all()
        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            buyer = order.buyer
            items = self.session.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            perfumes = ', '.join(
                [f"{self.session.query(Perfume).get(oi.perfume_id).brand} {self.session.query(Perfume).get(oi.perfume_id).name} ({oi.quantity_ml} ml)" for oi in items]
            )
            status = "zakończone" if order.received_money else "oczekiwane"
            self.table.setItem(row, 0, QTableWidgetItem(buyer))
            self.table.setItem(row, 1, QTableWidgetItem(perfumes))
            self.table.setItem(row, 2, QTableWidgetItem(f"{order.total or 0:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{order.shipping or 0:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(status))
            self.table.setItem(row, 5, QTableWidgetItem(str(order.sale_date) if order.sale_date else ""))

    def open_new_order(self):
        dialog = AddOrderDialog(self)
        if dialog.exec_():
            self.load_orders()
