from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView
)
from PyQt5.QtGui import QIcon, QColor
from functools import partial
from models.database import Session
from models.order import Order
from models.perfume import Perfume
from models.order_item import OrderItem
from ui.add_order_dialog import AddOrderDialog
import os

class OrdersView(QWidget):
    def __init__(self, perfumes_view=None, parent=None):
        super().__init__(parent)
        self.session = Session()
        self.perfumes_view = perfumes_view

        layout = QVBoxLayout(self)

        # Przycisk dodawania nowego zamówienia
        add_btn = QPushButton("Dodaj zamówienie")
        add_btn.clicked.connect(self.open_new_order)
        layout.addWidget(add_btn)

        # Tabela zamówień z dodatkową kolumną "Data potw."
        self.table = QTableWidget(0, 11)  # o 1 więcej niż poprzednio
        self.table.setHorizontalHeaderLabels([
            "Kupujący", "Perfumy", "Kwota", "Wysyłka", "Stan",
            "Data sprzedaży", "Gratis", "Uwagi", "Data potw.", "Edytuj", "Usuń"
        ])
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_orders()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(24)  # domyślny stały rozmiar wiersza
        self.table.setStyleSheet("QTableWidget { gridline-color: #ddd; }")  # poprawa wizualna

    def load_orders(self):
        self.table.setRowCount(0)
        orders = self.session.query(Order).all()
        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            items = self.session.query(OrderItem).filter_by(order_id=order.id).all()

            paid = ", ".join(
                f"{self.session.get(Perfume, oi.perfume_id).brand} "
                f"{self.session.get(Perfume, oi.perfume_id).name} ({oi.quantity_ml} ml)"
                for oi in items if oi.price_per_ml > 0
            )
            gratis = ", ".join(
                f"{self.session.get(Perfume, oi.perfume_id).brand} "
                f"{self.session.get(Perfume, oi.perfume_id).name}"
                for oi in items if oi.price_per_ml == 0
            )
            status, color = self.get_status_and_color(order)

            self.table.setItem(row, 0, QTableWidgetItem(order.buyer or ""))
            self.table.setItem(row, 1, QTableWidgetItem(paid))
            self.table.setItem(row, 2, QTableWidgetItem(f"{order.total:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{order.shipping:.2f}"))
            st_item = QTableWidgetItem(status)
            st_item.setForeground(color)
            self.table.setItem(row, 4, st_item)
            self.table.setItem(row, 5, QTableWidgetItem(str(order.sale_date or "")))
            self.table.setItem(row, 6, QTableWidgetItem(gratis))
            self.table.setItem(row, 7, QTableWidgetItem(order.notes or ""))
            # Data potwierdzenia (nowa kolumna)
            confirmation_date_str = order.confirmation_date.isoformat() if order.confirmation_date else ""
            self.table.setItem(row, 8, QTableWidgetItem(confirmation_date_str))

            # Edytuj
            edit_btn = QPushButton()
            icon = os.path.join(os.path.dirname(__file__), "edit_icon.png")
            if os.path.exists(icon):
                edit_btn.setIcon(QIcon(icon))
            else:
                edit_btn.setText("Edytuj")
            edit_btn.clicked.connect(partial(self.edit_order, order.id))
            self.table.setCellWidget(row, 9, edit_btn)

            # Usuń
            del_btn = QPushButton("Usuń")
            del_btn.clicked.connect(partial(self.delete_order, order.id))
            self.table.setCellWidget(row, 10, del_btn)

            # Ustaw wysokość wiersza na stałą (ułatwia spójność)
            self.table.setRowHeight(row, 24)

    def get_status_and_color(self, o):
        if o.confirmation_obtained:
            return "Zakończone", QColor("gray")
        if o.sent:
            return "Pobierz potwierdzenie", QColor("purple")
        if o.generated_label:
            return "Wyślij paczkę", QColor("red")
        if o.received_money:
            return "Wygeneruj etykietę", QColor("red")
        if o.sent_message:
            return "Oczekiwanie na zapłatę", QColor("black")
        return "Wyślij wiadomość", QColor("red")

    def open_new_order(self):
        dlg = AddOrderDialog(self)
        if dlg.exec_():
            if self.perfumes_view:
                self.perfumes_view.load_perfumes()
            self.load_orders()
            # Po dodaniu nowego zamówienia wywołaj dopasowanie wysokości
            self.resize_rows_to_contents()

    def edit_order(self, order_id):
        order = self.session.get(Order, order_id)
        if not order:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono zamówienia.")
            return
        dlg = AddOrderDialog(self, order_to_edit=order)
        if dlg.exec_():
            if self.perfumes_view:
                self.perfumes_view.load_perfumes()
            self.load_orders()
            self.resize_rows_to_contents()

    def delete_order(self, order_id):
        reply = QMessageBox.question(
            self, "Usuń zamówienie",
            "Czy na pewno chcesz usunąć to zamówienie?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.session.query(OrderItem).filter_by(order_id=order_id).delete()
                self.session.query(Order).filter_by(id=order_id).delete()
                self.session.commit()
                if self.perfumes_view:
                    self.perfumes_view.load_perfumes()
                self.load_orders()
                self.resize_rows_to_contents()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć: {e}")

    def resize_rows_to_contents(self):
        """Dopasuj wysokość wszystkich wierszy do zawartości."""
        self.table.resizeRowsToContents()
        # Możesz ograniczyć max wysokość, jeśli potrzeba:
        max_height = 48
        for row in range(self.table.rowCount()):
            h = self.table.rowHeight(row)
            if h > max_height:
                self.table.setRowHeight(row, max_height)
