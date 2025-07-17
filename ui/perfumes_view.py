from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QTableWidget, QTableWidgetItem, QMessageBox
)
from models.database import Session
from models.perfume import Perfume

class PerfumesView(QWidget):
    def __init__(self):
        super().__init__()

        self.session = Session()
        self.layout = QVBoxLayout()

        # Formularz do dodawania perfum
        self.form_layout = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nazwa perfum")

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Marka")

        self.buy_price_input = QLineEdit()
        self.buy_price_input.setPlaceholderText("Cena zakupu")

        self.sell_price_input = QLineEdit()
        self.sell_price_input.setPlaceholderText("Cena sprzedaży")

        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText("Ilość")

        self.add_button = QPushButton("Dodaj perfumy")
        self.add_button.clicked.connect(self.add_perfume)

        for widget in [
            self.name_input, self.brand_input, self.buy_price_input, 
            self.sell_price_input, self.qty_input, self.add_button
        ]:
            self.form_layout.addWidget(widget)

        self.layout.addLayout(self.form_layout)

        # Tabela wyświetlająca perfumy
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Nazwa", "Marka", "Cena zakupu", "Cena sprzedaży", "Ilość"
        ])

        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

        self.load_perfumes()

    def load_perfumes(self):
        perfumes = self.session.query(Perfume).all()
        self.table.setRowCount(len(perfumes))

        for row, perfume in enumerate(perfumes):
            self.table.setItem(row, 0, QTableWidgetItem(perfume.name))
            self.table.setItem(row, 1, QTableWidgetItem(perfume.brand or ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(perfume.purchase_price or 0)))
            self.table.setItem(row, 3, QTableWidgetItem(str(perfume.selling_price or 0)))
            self.table.setItem(row, 4, QTableWidgetItem(str(perfume.quantity or 0)))

    def add_perfume(self):
        try:
            if not self.name_input.text().strip():
                QMessageBox.warning(self, "Błąd", "Nazwa perfum jest wymagana.")
                return

            perfume = Perfume(
                name=self.name_input.text().strip(),
                brand=self.brand_input.text().strip(),
                purchase_price=float(self.buy_price_input.text() or 0),
                selling_price=float(self.sell_price_input.text() or 0),
                quantity=int(self.qty_input.text() or 0)
            )

            self.session.add(perfume)
            self.session.commit()

            QMessageBox.information(self, "Sukces", "Perfumy zostały dodane.")
            self.clear_inputs()
            self.load_perfumes()

        except ValueError:
            QMessageBox.warning(self, "Błąd", "Cena zakupu, sprzedaży i ilość muszą być liczbami.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd krytyczny", f"Coś poszło nie tak: {e}")

    def clear_inputs(self):
        self.name_input.clear()
        self.brand_input.clear()
        self.buy_price_input.clear()
        self.sell_price_input.clear()
        self.qty_input.clear()
