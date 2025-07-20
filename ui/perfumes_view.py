# ui/perfumes_view.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt5.QtGui import QColor
from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem

DECANT_COST = 4.0  # koszt dekantu na zamówienie

class PerfumesView(QWidget):
    def __init__(self):
        super().__init__()
        self.session = Session()
        self.layout = QVBoxLayout(self)

        # Formularz do dodawania perfum
        self.form_layout = QHBoxLayout()
        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Marka")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nazwa perfum")
        self.to_decant_input = QLineEdit()
        self.to_decant_input.setPlaceholderText("Do odlania (ml)")
        self.price_per_ml_input = QLineEdit()
        self.price_per_ml_input.setPlaceholderText("Cena za ml")
        self.buy_price_input = QLineEdit()
        self.buy_price_input.setPlaceholderText("Cena zakupu")
        self.add_button = QPushButton("Dodaj perfumy")
        self.add_button.clicked.connect(self.add_perfume)

        for widget in (
            self.brand_input, self.name_input, self.to_decant_input,
            self.price_per_ml_input, self.buy_price_input, self.add_button
        ):
            self.form_layout.addWidget(widget)
        self.layout.addLayout(self.form_layout)

        # Tabela perfum
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Marka", "Nazwa", "Do odlania", "Pozostało", "Cena/ml",
            "Zamówień", "Sprzedaż", "Cena zakupu", "Opłaty", "Bilans"
        ])
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

        self.load_perfumes()

    def load_perfumes(self):
        perfumes = self.session.query(Perfume).all()
        self.table.setRowCount(len(perfumes))

        for row, p in enumerate(perfumes):
            # 1. Pozostało = to_decant − suma quantity_ml wszystkich OrderItem
            used_ml = sum(
                oi.quantity_ml
                for oi in self.session.query(OrderItem).filter_by(perfume_id=p.id)
            )
            remaining = max((p.to_decant or 0) - used_ml, 0)

            # 2. Zamówień (tylko płatne)
            orders_count = self.session.query(OrderItem)\
                .filter_by(perfume_id=p.id)\
                .filter(OrderItem.price_per_ml > 0)\
                .count()

            # 3. Sprzedaż = suma(quantity_ml*price_per_ml) + DECANT_COST × orders_count
            sales_sum = sum(
                oi.quantity_ml * oi.price_per_ml
                for oi in self.session.query(OrderItem).filter_by(perfume_id=p.id)
                if oi.price_per_ml > 0
            ) + orders_count * DECANT_COST

            # 4. Opłaty = orders_count*2 + orders_count
            extra_costs = orders_count * 2 + orders_count

            # 5. Bilans = sales_sum − purchase_price − extra_costs
            balance = sales_sum - (p.purchase_price or 0) - extra_costs

            # Wypełnianie tabeli
            self.table.setItem(row, 0, QTableWidgetItem(p.brand or ""))
            self.table.setItem(row, 1, QTableWidgetItem(p.name or ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(p.to_decant or 0)))

            rem_item = QTableWidgetItem(f"{remaining:.2f}")
            if remaining > 50:
                rem_item.setForeground(QColor("green"))
            elif remaining > 20:
                rem_item.setForeground(QColor("gold"))
            else:
                rem_item.setForeground(QColor("red"))
            self.table.setItem(row, 3, rem_item)

            self.table.setItem(row, 4, QTableWidgetItem(f"{p.price_per_ml or 0:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(str(orders_count)))
            self.table.setItem(row, 6, QTableWidgetItem(f"{sales_sum:.2f}"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{p.purchase_price or 0:.2f}"))
            self.table.setItem(row, 8, QTableWidgetItem(str(extra_costs)))

            bal_item = QTableWidgetItem(f"{balance:.2f}")
            if balance > 0:
                bal_item.setForeground(QColor("green"))
            elif balance < 0:
                bal_item.setForeground(QColor("red"))
            else:
                bal_item.setForeground(QColor("black"))
            self.table.setItem(row, 9, bal_item)

    def add_perfume(self):
        try:
            brand = self.brand_input.text().strip()
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Błąd", "Nazwa perfum jest wymagana.")
                return

            to_decant = float(self.to_decant_input.text().replace(",", ".") or 0)
            price_per_ml = float(self.price_per_ml_input.text().replace(",", ".") or 0)
            purchase_price = float(self.buy_price_input.text().replace(",", ".") or 0)

            perfume = Perfume(
                brand=brand,
                name=name,
                to_decant=to_decant,
                price_per_ml=price_per_ml,
                purchase_price=purchase_price
            )
            self.session.add(perfume)
            self.session.commit()

            QMessageBox.information(self, "Sukces", "Perfumy zostały dodane.")
            self.clear_inputs()
            self.load_perfumes()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Błąd", f"Nie udało się dodać perfum: {e}")

    def clear_inputs(self):
        for widget in (
            self.brand_input, self.name_input,
            self.to_decant_input, self.price_per_ml_input,
            self.buy_price_input
        ):
            widget.clear()
