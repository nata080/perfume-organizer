from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QComboBox, QMessageBox, QHeaderView
)
from PyQt5.QtGui import QColor, QFont
from functools import partial
from models.database import Session
from models.order import Order
from models.perfume import Perfume
from models.order_item import OrderItem
from ui.add_order_dialog import AddOrderDialog

class OrdersView(QWidget):
    def __init__(self, perfumes_view=None, parent=None):
        super().__init__(parent)
        self.session = Session()
        self.perfumes_view = perfumes_view
        font = QFont()
        font.setPointSize(9)
        self.setFont(font)
        layout = QVBoxLayout(self)

        # --- Filtr i wyszukiwarka ---
        row1 = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Wszystkie", "Rozbiórka"])
        self.filter_combo.currentIndexChanged.connect(self.load_orders)
        row1.addWidget(QLabel("Filtr:"))
        row1.addWidget(self.filter_combo)

        row1.addStretch()
        row1.addWidget(QLabel("Kupujący:"))
        self.search_buyer_edit = QLineEdit()
        self.search_buyer_edit.setPlaceholderText("Szukaj po kupującym…")
        self.search_buyer_edit.textChanged.connect(self.load_orders)
        row1.addWidget(self.search_buyer_edit)
        layout.addLayout(row1)

        add_btn = QPushButton("Dodaj zamówienie")
        add_btn.clicked.connect(self.open_new_order)
        layout.addWidget(add_btn)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Kupujący", "Perfumy", "Kwota", "Wysyłka", "Stan",
            "Data sprzedaży", "Gratis", "Uwagi", "Data potw.", "Edytuj", "Usuń"
        ])
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setStyleSheet("QTableWidget { gridline-color: #ddd; }")
        self.table.setFont(font)
        self.table.setSortingEnabled(True)

        self.load_orders()

    def load_orders(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        filter_mode = self.filter_combo.currentText()
        buyer_search = self.search_buyer_edit.text().strip().lower()
        orders = self.session.query(Order).all()
        if filter_mode == "Rozbiórka":
            orders = [o for o in orders if getattr(o, "is_split", False)]
        if buyer_search:
            orders = [o for o in orders if buyer_search in (o.buyer or "").lower()]
        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            items = self.session.query(OrderItem).filter_by(order_id=order.id).all()
            paid = ", ".join(
                f"{self.session.get(Perfume, oi.perfume_id).brand} {self.session.get(Perfume, oi.perfume_id).name} ({oi.quantity_ml} ml)"
                for oi in items if oi.price_per_ml > 0 and self.session.get(Perfume, oi.perfume_id)
            )
            gratis = ", ".join(
                f"{self.session.get(Perfume, oi.perfume_id).brand} {self.session.get(Perfume, oi.perfume_id).name}"
                for oi in items if oi.price_per_ml == 0 and self.session.get(Perfume, oi.perfume_id)
            )
            status, color = self.get_status_and_color(order)
            def safeSet(row, col, val, fg=None):
                itm = QTableWidgetItem(val)
                if fg:
                    itm.setForeground(fg)
                self.table.setItem(row, col, itm)
            safeSet(row, 0, order.buyer or "")
            safeSet(row, 1, paid)
            safeSet(row, 2, f"{order.total:.2f}")
            safeSet(row, 3, f"{order.shipping:.2f}")
            safeSet(row, 4, status, color)
            safeSet(row, 5, str(order.sale_date or ""))
            safeSet(row, 6, gratis)
            safeSet(row, 7, order.notes or "")
            confirmation_date_str = order.confirmation_date.isoformat() if order.confirmation_date else ""
            safeSet(row, 8, confirmation_date_str)

            # Edytuj
            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(partial(self.edit_order, order.id))
            self.table.setCellWidget(row, 9, edit_btn)
            # Usuń
            del_btn = QPushButton("Usuń")
            del_btn.clicked.connect(partial(self.delete_order, order.id))
            self.table.setCellWidget(row, 10, del_btn)
            self.table.setRowHeight(row, 24)
            if hasattr(order, "is_split") and order.is_split:
                color_bg = QColor(210, 234, 255)
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(color_bg)
        self.table.setSortingEnabled(True)
        self.resize_rows_to_contents()

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
        self.table.resizeRowsToContents()
        max_height = 48
        for row in range(self.table.rowCount()):
            h = self.table.rowHeight(row)
            if h > max_height:
                self.table.setRowHeight(row, max_height)
