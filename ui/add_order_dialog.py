from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QComboBox, QPushButton,
    QCheckBox, QHeaderView, QDateEdit, QMessageBox
)
from PyQt5.QtCore import QDate, Qt
from models.database import Session
from models.perfume import Perfume

ORDER_VIAL_COST = 4.0
SHIPPING_OPTIONS = {
    "InPost": 12.0,
    "DPD": 10.0,
}
ML_OPTIONS = [3, 5, 10, 15, 20, 30]

class AddOrderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = Session()
        self.setWindowTitle("Nowe zamówienie")
        self.layout = QVBoxLayout(self)

        self.buyer_input = QLineEdit()
        self.buyer_input.setPlaceholderText("Kupujący")
        self.layout.addWidget(QLabel("Kupujący:"))
        self.layout.addWidget(self.buyer_input)

        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels([
            "Perfumy", "Ilość (ml)", "Cena za ml", "Część zam."
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(QLabel("Zamawiane perfumy:"))
        self.layout.addWidget(self.items_table)

        row_btns = QHBoxLayout()
        add_item_btn = QPushButton("Dodaj perfumy")
        add_item_btn.clicked.connect(self.add_item_row)
        row_btns.addWidget(add_item_btn)

        self.btn_gratis = QPushButton("+gratis")
        self.btn_gratis.clicked.connect(self.add_gratis)
        row_btns.addWidget(self.btn_gratis)
        self.layout.addLayout(row_btns)

        self.shipping_combo = QComboBox()
        self.shipping_combo.addItem("", userData=None)
        for opt in SHIPPING_OPTIONS:
            self.shipping_combo.addItem(f"{opt} ({SHIPPING_OPTIONS[opt]:.2f} zł)", userData=opt)
        self.layout.addWidget(QLabel("Wysyłka:"))
        self.layout.addWidget(self.shipping_combo)
        self.shipping_combo.currentIndexChanged.connect(self.recalculate_total)

        self.total_label = QLabel("Suma do zapłaty: 0.00 zł")
        self.layout.addWidget(self.total_label)

        cb_layout = QHBoxLayout()
        self.cb_msg = QCheckBox("Wiadomość")
        self.cb_money = QCheckBox("Pieniądz")
        self.cb_label = QCheckBox("Etykieta")
        self.cb_package = QCheckBox("Paczka")
        self.cb_ship = QCheckBox("Wysyłka")
        self.cb_confirm = QCheckBox("Potw. pobrania")
        for cb in [
            self.cb_msg, self.cb_money, self.cb_label,
            self.cb_package, self.cb_ship, self.cb_confirm
        ]:
            cb_layout.addWidget(cb)
        self.layout.addLayout(cb_layout)

        self.sale_date_edit = QDateEdit(QDate.currentDate())
        self.sale_date_edit.setEnabled(False)
        self.sale_date_edit.setCalendarPopup(True)
        self.layout.addWidget(QLabel("Data sprzedaży:"))
        self.layout.addWidget(self.sale_date_edit)
        self.cb_money.stateChanged.connect(self.handle_money_checkbox)

        self.btn_gen_msg = QPushButton("Generuj wiadomość")
        self.btn_gen_msg.clicked.connect(self.open_message_popup)
        self.layout.addWidget(self.btn_gen_msg)

        btns = QHBoxLayout()
        save_btn = QPushButton("Zapisz zamówienie")
        cancel_btn = QPushButton("Anuluj")
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        self.layout.addLayout(btns)
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.save_order)

        self.items_table.cellChanged.connect(self.cell_update)
        self._perfume_cache = []
        self.load_perfume_list()
        self.add_item_row()

    def load_perfume_list(self):
        self._perfume_cache = sorted(
            self.session.query(Perfume).all(),
            key=lambda p: (p.brand.lower(), p.name.lower())
        )

    def add_item_row(self, perfume_obj=None, is_gratis=False):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        perfume_combo = QComboBox()
        for p in self._perfume_cache:
            label = f"{p.brand} {p.name}"
            if is_gratis and p == perfume_obj:
                label += " (GRATIS)"
            perfume_combo.addItem(label, userData=p.id)
        if perfume_obj:
            perfume_combo.setCurrentIndex(
                next((i for i, p in enumerate(self._perfume_cache) if p.id == perfume_obj.id), 0)
            )
        perfume_combo.currentIndexChanged.connect(lambda idx, r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row, 0, perfume_combo)

        if is_gratis:
            qty_combo = QComboBox()
            qty_combo.addItem("3", userData=3)
            qty_combo.setEnabled(False)
        else:
            qty_combo = QComboBox()
            for v in ML_OPTIONS:
                qty_combo.addItem(str(v), userData=v)
            qty_combo.setCurrentIndex(ML_OPTIONS.index(5))
        qty_combo.currentIndexChanged.connect(lambda idx, r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row, 1, qty_combo)

        price_item = QTableWidgetItem("0.00")
        price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 2, price_item)

        part_item = QTableWidgetItem("0.00")
        part_item.setFlags(part_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 3, part_item)

        self.update_price_for_row(row, force_gratis=is_gratis)

    def add_gratis(self):
        from PyQt5.QtWidgets import QInputDialog
        perfume_names = [f"{p.brand} {p.name}" for p in self._perfume_cache]
        idx, ok = QInputDialog.getItem(self, "Wybierz perfumy na gratis", "Perfumy:", perfume_names, 0, False)
        if ok:
            sel_p = self._perfume_cache[perfume_names.index(idx)]
            self.add_item_row(perfume_obj=sel_p, is_gratis=True)

    def update_price_for_row(self, row, force_gratis=False):
        perfume_combo = self.items_table.cellWidget(row, 0)
        qty_combo = self.items_table.cellWidget(row, 1)
        if perfume_combo is None or qty_combo is None:
            return
        perfume_id = perfume_combo.currentData()
        perfume = next((p for p in self._perfume_cache if p.id == perfume_id), None)
        is_gratis = False
        label = perfume_combo.currentText()
        if "GRATIS" in label or force_gratis:
            is_gratis = True
        price_ml = perfume.price_per_ml if perfume and perfume.price_per_ml else 0
        price_item = self.items_table.item(row, 2)
        if price_item is None:
            price_item = QTableWidgetItem("0.00")
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, 2, price_item)
        price_item.setText(self.format_value(0 if is_gratis else price_ml))

        qty = qty_combo.currentData() if qty_combo.currentData() is not None else 0
        part_sum = 0 if is_gratis else price_ml * qty
        part_item = self.items_table.item(row, 3)
        if part_item is None:
            part_item = QTableWidgetItem("0.00")
            part_item.setFlags(part_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, 3, part_item)
        part_item.setText(self.format_value(part_sum))
        self.recalculate_total()

    def cell_update(self, row, col):
        self.update_price_for_row(row)

    def recalculate_total(self):
        total = 0.0
        for row in range(self.items_table.rowCount()):
            part_item = self.items_table.item(row, 3)
            try:
                val = float(part_item.text().replace(',', '.')) if part_item else 0.0
            except Exception:
                val = 0.0
            total += val
        shipping_opt = self.shipping_combo.currentData()
        shipping_cost = SHIPPING_OPTIONS[shipping_opt] if shipping_opt in SHIPPING_OPTIONS else 0.0
        num_items = self.items_table.rowCount()
        total += shipping_cost + num_items * ORDER_VIAL_COST
        self.total_label.setText(f"Suma do zapłaty: {self.format_value(total)} zł")

    def handle_money_checkbox(self, state):
        self.sale_date_edit.setEnabled(bool(state))
        if state:
            self.sale_date_edit.setDate(QDate.currentDate())

    def save_order(self):
        from models.order import Order
        from models.order_item import OrderItem
        buyer = self.buyer_input.text().strip()
        if not buyer:
            QMessageBox.warning(self, "Błąd", "Wprowadź kupującego!")
            return
        self.recalculate_total()
        shipping_opt = self.shipping_combo.currentData()
        shipping_cost = SHIPPING_OPTIONS[shipping_opt] if shipping_opt in SHIPPING_OPTIONS else 0.0
        order = Order(
            buyer=buyer,
            shipping=shipping_cost,
            total=self.calc_total(),
            sent_message=self.cb_msg.isChecked(),
            received_money=self.cb_money.isChecked(),
            generated_label=self.cb_label.isChecked(),
            packed=self.cb_package.isChecked(),
            sent=self.cb_ship.isChecked(),
            confirmation_obtained=self.cb_confirm.isChecked(),
            sale_date=self.sale_date_edit.date().toPyDate() if self.cb_money.isChecked() else None
        )
        self.session.add(order)
        self.session.commit()
        for row in range(self.items_table.rowCount()):
            perfume_combo = self.items_table.cellWidget(row, 0)
            qty_combo = self.items_table.cellWidget(row, 1)
            perfume_id = perfume_combo.currentData()
            pml = self.field_to_float(self.items_table.item(row, 2).text())
            qty = qty_combo.currentData() if qty_combo.currentData() is not None else 0
            part_sum = self.field_to_float(self.items_table.item(row, 3).text())
            item = OrderItem(
                order_id=order.id,
                perfume_id=perfume_id,
                quantity_ml=qty,
                price_per_ml=pml,
                partial_sum=part_sum
            )
            self.session.add(item)
        self.session.commit()
        QMessageBox.information(self, "OK", "Zamówienie zostało zapisane")
        self.accept()

    def field_to_float(self, val):
        try:
            return float((val or '0').replace(',', '.'))
        except Exception:
            return 0.0

    def calc_total(self):
        total = 0.0
        for row in range(self.items_table.rowCount()):
            try:
                total += float(self.items_table.item(row, 3).text().replace(',', '.'))
            except Exception:
                pass
        shipping_opt = self.shipping_combo.currentData()
        shipping_cost = SHIPPING_OPTIONS[shipping_opt] if shipping_opt in SHIPPING_OPTIONS else 0.0
        num_items = self.items_table.rowCount()
        return total + shipping_cost + num_items * ORDER_VIAL_COST

    def open_message_popup(self):
        message = self.generate_buyer_message()
        from ui.message_popup import MessagePopup
        popup = MessagePopup(message, self, checkbox_to_mark=self.cb_msg)
        popup.exec_()

    def generate_buyer_message(self):
        lines = []
        lines.append("Podsumowanie:")
        for row in range(self.items_table.rowCount()):
            perfume_combo = self.items_table.cellWidget(row, 0)
            qty_combo = self.items_table.cellWidget(row, 1)
            perfume_name = perfume_combo.currentText()
            qty = qty_combo.currentData() if qty_combo.currentData() is not None else 0
            price_item = self.items_table.item(row, 2)
            part_item = self.items_table.item(row, 3)
            price_txt = self.format_value(float(price_item.text().replace(',', '.')))
            part_txt = self.format_value(float(part_item.text().replace(',', '.')))
            lines.append(f"{perfume_name} -> {qty} x {price_txt} = {part_txt} zł")
        num_dekants = self.items_table.rowCount()
        dekanty_sum = num_dekants * ORDER_VIAL_COST
        dekanty_sum_txt = self.format_value(dekanty_sum)
        lines.append(f"\ndekanty -> {num_dekants} x 4 = {dekanty_sum_txt} zł")
        total = 0.0
        for row in range(self.items_table.rowCount()):
            p = self.items_table.item(row, 3)
            try:
                total += float(p.text().replace(',', '.'))
            except Exception:
                pass
        total += dekanty_sum
        total_txt = self.format_value(total)
        lines.append(f"\nRazem: {total_txt} zł (bez wysyłki)")
        lines.append("\nZa dostawę doliczamy 10zł (DPD), 12zł (inPost) lub własna etykieta (wtedy nic)\n")
        lines.append("BLIK: 694604172")
        lines.append("Jeśli potrzeba, mogę podać numer konta bankowego")
        return "\n".join(lines)

    def format_value(self, val):
        return str(int(val)) if val == int(val) else f"{val:.2f}".replace('.', ',')

