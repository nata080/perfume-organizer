from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt5.QtGui import QColor
from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem

class PerfumesView(QWidget):
    def __init__(self):
        super().__init__()
        self.session = Session()
        self.layout = QVBoxLayout()

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

        for widget in [
            self.brand_input, self.name_input, self.to_decant_input,
            self.price_per_ml_input, self.buy_price_input, self.add_button
        ]:
            self.form_layout.addWidget(widget)
        self.layout.addLayout(self.form_layout)

        # Tabela wyświetlająca perfumy
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Marka", "Nazwa", "Do odlania", "Pozostało", "Cena/ml",
            "Liczba zamówień", "Cena zakupu", "Cena sprzedaży",
            "Opłaty dodatkowe", "Bilans"
        ])
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        self.load_perfumes()

    def load_perfumes(self):
        perfumes = self.session.query(Perfume).all()
        self.table.setRowCount(len(perfumes))
        for row, p in enumerate(perfumes):
            # Wylicz Pozostało: Do odlania - suma wszystkich zamówionych ml (OrderItem)
            used_ml = sum(
                oi.quantity_ml for oi in self.session.query(OrderItem).filter_by(perfume_id=p.id)
            )
            remaining = max((p.to_decant or 0) - used_ml, 0)
            item_rem = QTableWidgetItem(str(round(remaining, 2)))
            # Kolorowanie Pozostało: zielony >50, żółty (20,50], czerwony <=20
            if remaining > 50:
                item_rem.setForeground(QColor('green'))
            elif 20 < remaining <= 50:
                item_rem.setForeground(QColor('gold'))
            else:
                item_rem.setForeground(QColor('red'))

            self.table.setItem(row, 0, QTableWidgetItem(p.brand))
            self.table.setItem(row, 1, QTableWidgetItem(p.name))
            self.table.setItem(row, 2, QTableWidgetItem(str(p.to_decant or 0)))
            self.table.setItem(row, 3, item_rem)
            self.table.setItem(row, 4, QTableWidgetItem(str(p.price_per_ml or 0)))
            self.table.setItem(row, 5, QTableWidgetItem(str(p.order_count or 0)))
            self.table.setItem(row, 6, QTableWidgetItem(str(p.purchase_price or 0)))
            self.table.setItem(row, 7, QTableWidgetItem(str(p.selling_price or 0)))
            self.table.setItem(row, 8, QTableWidgetItem(str(p.extra_costs or 0)))
            self.table.setItem(row, 9, QTableWidgetItem(str(p.balance or 0)))

    @staticmethod
    def parse_number(text):
        text = (text or '').replace(',', '.').strip()
        try:
            return float(text) if text else 0.0
        except ValueError:
            return 0.0

    def add_perfume(self):
        try:
            if not self.name_input.text().strip():
                QMessageBox.warning(self, "Błąd", "Nazwa perfum jest wymagana.")
                return
            perfume = Perfume(
                brand=self.brand_input.text().strip(),
                name=self.name_input.text().strip(),
                to_decant=self.parse_number(self.to_decant_input.text()),
                price_per_ml=self.parse_number(self.price_per_ml_input.text()),
                purchase_price=self.parse_number(self.buy_price_input.text())
            )
            perfume.remaining = 0  # zostanie wyliczone na podstawie zamówień
            perfume.order_count = 0
            perfume.selling_price = 0
            perfume.extra_costs = 4 + 1  # np. 4 zł dekant + 1 zł koperta
            perfume.compute_balance()
            self.session.add(perfume)
            self.session.commit()
            QMessageBox.information(self, "Sukces", "Perfumy zostały dodane.")
            self.clear_inputs()
            self.load_perfumes()
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Upewnij się, że wszystkie pola liczbowe zawierają poprawne dane.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd krytyczny", f"Coś poszło nie tak: {e}")

    def clear_inputs(self):
        self.brand_input.clear()
        self.name_input.clear()
        self.to_decant_input.clear()
        self.price_per_ml_input.clear()
        self.buy_price_input.clear()
