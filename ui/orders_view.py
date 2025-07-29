# ui/orders_view.py
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView,
)

from models.database import Session
from models.order import Order
from models.order_item import OrderItem
from models.perfume import Perfume
from ui.add_order_dialog import AddOrderDialog


# ─────────────────────────────────────────────────────────────────────────────
#  WŁASNE KOMÓRKI → POPRAWNE SORTOWANIE LICZB
# ─────────────────────────────────────────────────────────────────────────────
class IntItem(QTableWidgetItem):
    """Komórka sortowana jako liczba całkowita."""
    def __init__(self, value: int):
        super().__init__(str(value))
        self._v = value

    def __lt__(self, other):
        if isinstance(other, IntItem):
            return self._v < other._v
        return super().__lt__(other)


class FloatItem(QTableWidgetItem):
    """Komórka sortowana jako liczba zmiennoprzecinkowa."""
    def __init__(self, value: float, prec: int = 2):
        super().__init__(f"{value:.{prec}f}")
        self._v = value

    def __lt__(self, other):
        if isinstance(other, FloatItem):
            return self._v < other._v
        return super().__lt__(other)


# ─────────────────────────────────────────────────────────────────────────────
class OrdersView(QWidget):
    """Zakładka z listą zamówień."""
    def __init__(self, perfumes_view=None, parent=None):
        super().__init__(parent)
        self.session = Session()
        self.perfumes_view = perfumes_view

        font = QFont()
        font.setPointSize(9)
        self.setFont(font)

        root = QVBoxLayout(self)

        # ── FILTRY ──────────────────────────────────────────────────────────
        filters = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Wszystkie", "Rozbiórka"])
        self.filter_combo.currentIndexChanged.connect(self.load_orders)

        filters.addWidget(QLabel("Filtr:"))
        filters.addWidget(self.filter_combo)
        filters.addStretch()

        filters.addWidget(QLabel("Kupujący:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Szukaj po kupującym…")
        self.search_edit.textChanged.connect(self.load_orders)
        filters.addWidget(self.search_edit)

        root.addLayout(filters)

        # ── PRZYCISK „DODAJ” ───────────────────────────────────────────────
        add_btn = QPushButton("Dodaj zamówienie")
        add_btn.clicked.connect(self.open_new_order)
        root.addWidget(add_btn)

        # ── TABELA ─────────────────────────────────────────────────────────
        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "Lp", "Kupujący", "Perfumy", "Kwota", "Wysyłka", "Stan",
            "Data sprzedaży", "Gratis", "Uwagi", "Data potw.",
            "Edytuj", "Usuń",
        ])
        root.addWidget(self.table)
        self.setLayout(root)

        # Konfiguracja tabeli
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(24)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)

        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setFont(font)

        # BLOKADA EDYCJI
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.load_orders()

    # ─────────────────────────────────────────────────────────────────────
    #                              ŁADOWANIE
    # ─────────────────────────────────────────────────────────────────────
    def load_orders(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        orders = self.session.query(Order).all()

        # filtr
        if self.filter_combo.currentText() == "Rozbiórka":
            orders = [o for o in orders if getattr(o, "is_split", False)]

        # wyszukiwarka
        buyer_q = self.search_edit.text().strip().lower()
        if buyer_q:
            orders = [o for o in orders if buyer_q in (o.buyer or "").lower()]

        for lp, order in enumerate(orders, 1):
            items = self.session.query(OrderItem).filter_by(order_id=order.id).all()
            row = self.table.rowCount()
            self.table.insertRow(row)

            paid = ", ".join(
                f"{self.session.get(Perfume, i.perfume_id).brand} "
                f"{self.session.get(Perfume, i.perfume_id).name} ({i.quantity_ml} ml)"
                for i in items if i.price_per_ml > 0 and self.session.get(Perfume, i.perfume_id)
            )
            gratis = ", ".join(
                f"{self.session.get(Perfume, i.perfume_id).brand} "
                f"{self.session.get(Perfume, i.perfume_id).name}"
                for i in items if i.price_per_ml == 0 and self.session.get(Perfume, i.perfume_id)
            )

            status_txt, status_col = self._status(order)

            self.table.setItem(row, 0, IntItem(lp))
            self.table.setItem(row, 1, QTableWidgetItem(order.buyer or ""))
            self.table.setItem(row, 2, QTableWidgetItem(paid))
            self.table.setItem(row, 3, FloatItem(order.total))
            self.table.setItem(row, 4, FloatItem(order.shipping))
            self.table.setItem(row, 5, self._colored_item(status_txt, status_col))
            self.table.setItem(row, 6, QTableWidgetItem(str(order.sale_date or "")))
            self.table.setItem(row, 7, QTableWidgetItem(gratis))
            self.table.setItem(row, 8, QTableWidgetItem(order.notes or ""))
            self.table.setItem(
                row, 9,
                QTableWidgetItem(order.confirmation_date.isoformat() if order.confirmation_date else "")
            )

            # przyciski
            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(partial(self.edit_order, order.id))
            self.table.setCellWidget(row, 10, edit_btn)

            del_btn = QPushButton("Usuń")
            del_btn.clicked.connect(partial(self.delete_order, order.id))
            self.table.setCellWidget(row, 11, del_btn)

            # podświetlenie rozbiórek
            if getattr(order, "is_split", False):
                bg = QColor(210, 234, 255)
                for c in range(self.table.columnCount()):
                    cell = self.table.item(row, c)
                    if cell:
                        cell.setBackground(bg)

        # Domyślne sortowanie numeryczne po Lp
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.AscendingOrder)

    # ─────────────────────────────────────────────────────────────────────
    #                           POMOCNICZE
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _colored_item(text, color: QColor):
        item = QTableWidgetItem(text)
        item.setForeground(color)
        return item

    @staticmethod
    def _status(o: Order):
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

    # ─────────────────────────────────────────────────────────────────────
    #                               CRUD
    # ─────────────────────────────────────────────────────────────────────
    def open_new_order(self):
        dlg = AddOrderDialog(self)
        if dlg.exec_():
            if self.perfumes_view:
                self.perfumes_view.load_perfumes()
            self.load_orders()

    def edit_order(self, order_id: int):
        order = self.session.get(Order, order_id)
        if not order:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono zamówienia.")
            return
        dlg = AddOrderDialog(self, order_to_edit=order)
        if dlg.exec_():
            if self.perfumes_view:
                self.perfumes_view.load_perfumes()
            self.load_orders()

    def delete_order(self, order_id: int):
        if QMessageBox.question(
            self, "Usuń zamówienie",
            "Czy na pewno chcesz usunąć to zamówienie?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            self.session.query(OrderItem).filter_by(order_id=order_id).delete()
            self.session.query(Order).filter_by(id=order_id).delete()
            self.session.commit()
            if self.perfumes_view:
                self.perfumes_view.load_perfumes()
            self.load_orders()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć: {e}")
