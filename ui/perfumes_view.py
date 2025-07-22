# ui/perfumes_view.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
from PyQt5.QtGui import QColor, QFont
from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem

DECANT_COST = 4.0  # koszt dekantu na zamówienie

class PerfumesView(QWidget):
    def __init__(self):
        super().__init__()
        self.session = Session()

        # zmniejszona czcionka
        base_font = QFont()
        base_font.setPointSize(9)
        self.setFont(base_font)

        layout = QVBoxLayout(self)

        # Górny panel z przyciskiem dodawania
        top_row = QHBoxLayout()
        self.add_button = QPushButton("Dodaj")
        self.add_button.clicked.connect(self.add_perfume)
        top_row.addWidget(self.add_button)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Tabela perfum
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        headers = [
            "Status","Marka","Nazwa","Do odlania","Pozostało","Cena/ml",
            "Zamówień","Sprzedaż","Cena zakupu","Opłaty","Bilans","Edytuj","Usuń"
        ]
        self.table.setHorizontalHeaderLabels(headers)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_perfumes()

    def load_perfumes(self):
        perfumes = self.session.query(Perfume).all()
        self.table.setRowCount(len(perfumes))
        for row, p in enumerate(perfumes):
            used_ml = sum(oi.quantity_ml for oi in self.session.query(OrderItem).filter_by(perfume_id=p.id))
            remaining = max((p.to_decant or 0) - used_ml, 0)
            orders_count = self.session.query(OrderItem)\
                .filter_by(perfume_id=p.id)\
                .filter(OrderItem.price_per_ml > 0)\
                .count()
            sales_sum = sum(
                oi.quantity_ml * oi.price_per_ml
                for oi in self.session.query(OrderItem).filter_by(perfume_id=p.id)
                if oi.price_per_ml > 0
            ) + orders_count * DECANT_COST
            extra_costs = orders_count * 2 + orders_count
            balance = sales_sum - (p.purchase_price or 0) - extra_costs

            def colored_item(text, fg=None):
                itm = QTableWidgetItem(str(text))
                if fg: itm.setForeground(QColor(fg))
                return itm

            # Wypełnianie kolumn
            color = "green" if p.status == "Dostępny" else "red"
            self.table.setItem(row, 0, colored_item(p.status, color))
            self.table.setItem(row, 1, QTableWidgetItem(p.brand or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.to_decant or 0:.2f}"))
            rem_col = "green" if remaining > 50 else "gold" if remaining > 20 else "red"
            self.table.setItem(row, 4, colored_item(f"{remaining:.2f}", rem_col))
            self.table.setItem(row, 5, QTableWidgetItem(f"{p.price_per_ml or 0:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(str(orders_count)))
            self.table.setItem(row, 7, QTableWidgetItem(f"{sales_sum:.2f}"))
            self.table.setItem(row, 8, QTableWidgetItem(f"{p.purchase_price or 0:.2f}"))
            self.table.setItem(row, 9, QTableWidgetItem(str(extra_costs)))
            bal_col = "green" if balance > 0 else "red" if balance < 0 else None
            self.table.setItem(row, 10, colored_item(f"{balance:.2f}", bal_col))

            # Edytuj
            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(lambda _, pid=p.id: self.edit_perfume(pid))
            self.table.setCellWidget(row, 11, edit_btn)

            # Usuń
            del_btn = QPushButton("Usuń")
            del_btn.clicked.connect(lambda _, pid=p.id: self.delete_perfume(pid))
            self.table.setCellWidget(row, 12, del_btn)

    def add_perfume(self):
        from ui.add_perfume_dialog import AddPerfumeDialog
        dlg = AddPerfumeDialog(self)
        if dlg.exec_():
            data = dlg.get_data()
            try:
                perf = Perfume(**data)
                self.session.add(perf)
                self.session.commit()
                self.load_perfumes()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Błąd", str(e))

    def edit_perfume(self, perfume_id):
        from ui.edit_perfume_dialog import EditPerfumeDialog
        perf = self.session.get(Perfume, perfume_id)
        if not perf:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono perfum.")
            return
        dlg = EditPerfumeDialog(perf, self)
        if dlg.exec_():
            data = dlg.get_data()
            for key, val in data.items():
                setattr(perf, key, val)
            self.session.commit()
            self.load_perfumes()

    def delete_perfume(self, perfume_id):
        reply = QMessageBox.question(
            self, "Usuń perfumy", "Czy na pewno chcesz usunąć te perfumy?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.session.query(Perfume).filter_by(id=perfume_id).delete()
                self.session.commit()
                self.load_perfumes()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Błąd", str(e))
