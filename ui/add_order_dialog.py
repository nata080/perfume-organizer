# ui/add_order_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QComboBox, QPushButton,
    QCheckBox, QHeaderView, QDateEdit, QMessageBox, QInputDialog
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QDate, Qt
from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem
from models.order import Order
from ui.message_popup import MessagePopup

ORDER_VIAL_COST = 4.0
SHIPPING_OPTIONS = {"InPost": 12.0, "DPD": 10.0}
ML_OPTIONS = [3, 5, 10, 15, 20, 30]

class AddOrderDialog(QDialog):
    def __init__(self, parent=None, order_to_edit=None):
        super().__init__(parent)
        self.session = Session()
        self.order_to_edit = order_to_edit

        self.setWindowTitle("Nowe zamówienie" if not order_to_edit else "Edytuj zamówienie")
        self.resize(800, 500)
        base_font = QFont()
        base_font.setPointSize(9)
        self.setFont(base_font)

        layout = QVBoxLayout(self)

        # Kupujący
        form = QHBoxLayout()
        form.addWidget(QLabel("Kupujący:"))
        self.buyer_input = QLineEdit()
        self.buyer_input.setPlaceholderText("Imię i nazwisko")
        form.addWidget(self.buyer_input)
        layout.addLayout(form)

        # Tabela pozycji
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(
            ["Perfumy", "Ilość (ml)", "Cena za ml", "Część zam.", "gratis"]
        )
        self.items_table.setColumnHidden(4, True)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.items_table)

        # Przyciski dodawania
        btns = QHBoxLayout()
        add_btn = QPushButton("Dodaj perfumy")
        add_btn.clicked.connect(lambda: self.add_item_row(default_ml=5))
        btns.addWidget(add_btn)
        gratis_btn = QPushButton("+ Gratis")
        gratis_btn.clicked.connect(self.add_gratis_row)
        btns.addWidget(gratis_btn)
        btns.addStretch()
        layout.addLayout(btns)

        # Wysyłka
        ship_layout = QHBoxLayout()
        ship_layout.addWidget(QLabel("Wysyłka:"))
        self.shipping_combo = QComboBox()
        self.shipping_combo.addItem("", None)
        for name, cost in SHIPPING_OPTIONS.items():
            self.shipping_combo.addItem(f"{name} ({cost:.2f} zł)", name)
        self.shipping_combo.currentIndexChanged.connect(self.recalculate_total)
        ship_layout.addWidget(self.shipping_combo)
        ship_layout.addStretch()
        layout.addLayout(ship_layout)

        # Suma
        self.total_label = QLabel("Suma do zapłaty: 0.00 zł")
        layout.addWidget(self.total_label)

        # Statusy
        cb_layout = QHBoxLayout()
        self.cb_msg = QCheckBox("Wiadomość")
        self.cb_money = QCheckBox("Pieniądz")
        self.cb_label = QCheckBox("Etykieta")
        self.cb_package = QCheckBox("Paczka")
        self.cb_shipped = QCheckBox("Wysyłka")
        self.cb_confirm = QCheckBox("Potw. pobrania")
        for cb in (self.cb_msg, self.cb_money, self.cb_label, self.cb_package, self.cb_shipped, self.cb_confirm):
            cb_layout.addWidget(cb)
        layout.addLayout(cb_layout)

        # Data sprzedaży
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Data sprzedaży:"))
        self.sale_date_edit = QDateEdit(QDate.currentDate())
        self.sale_date_edit.setCalendarPopup(True)
        self.sale_date_edit.setEnabled(False)
        self.cb_money.stateChanged.connect(lambda state: self.sale_date_edit.setEnabled(state == Qt.Checked))
        date_layout.addWidget(self.sale_date_edit)
        date_layout.addStretch()
        layout.addLayout(date_layout)

        # Akcje
        action_layout = QHBoxLayout()
        msg_btn = QPushButton("Generuj wiadomość")
        msg_btn.clicked.connect(self.generate_message_popup)
        save_btn = QPushButton("Zapisz zamówienie")
        save_btn.clicked.connect(self.save_order)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        action_layout.addStretch()
        action_layout.addWidget(msg_btn)
        action_layout.addWidget(save_btn)
        action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)

        # Cache perfum
        self._perfume_cache = self.session.query(Perfume).all()
        self.items_table.cellChanged.connect(lambda r, c: self.update_price_for_row(r))

        # Inicjalizacja wierszy
        if self.order_to_edit:
            self.fill_with_order(self.order_to_edit)
        else:
            self.add_item_row(default_ml=5)

    def add_item_row(self, perfume_obj=None, is_gratis=False, default_ml=5):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        # Perfumy
        combo = QComboBox()
        combo.setFont(self.font())
        for p in self._perfume_cache:
            combo.addItem(f"{p.brand} {p.name}", p.id)
        if perfume_obj:
            idx = next((i for i, p in enumerate(self._perfume_cache) if p.id == perfume_obj.id), 0)
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _, r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row, 0, combo)

        # Ilość (ml)
        qty_cb = QComboBox()
        for ml in ML_OPTIONS:
            qty_cb.addItem(str(ml), ml)
        if default_ml in ML_OPTIONS:
            qty_cb.setCurrentIndex(ML_OPTIONS.index(default_ml))
        qty_cb.currentIndexChanged.connect(lambda _, r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row, 1, qty_cb)

        # Cena za ml
        price_item = QTableWidgetItem("0.00")
        price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 2, price_item)

        # Część zam.
        part_item = QTableWidgetItem("0.00")
        part_item.setFlags(part_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 3, part_item)

        # Flaga gratis
        flag_item = QTableWidgetItem("1" if is_gratis else "0")
        flag_item.setFlags(flag_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 4, flag_item)

        self.update_price_for_row(row)

    def add_gratis_row(self):
        names = [f"{p.brand} {p.name}" for p in self._perfume_cache]
        idx, ok = QInputDialog.getItem(self, "Gratis", "Wybierz perfumy:", names, 0, False)
        if ok:
            p = self._perfume_cache[names.index(idx)]
            self.add_item_row(perfume_obj=p, is_gratis=True, default_ml=5)

    def update_price_for_row(self, row):
        # Pobranie flagi gratis (zabezpieczenie przed None)
        flag_item = self.items_table.item(row, 4)
        is_gratis = (flag_item.text() == "1") if flag_item else False

        combo = self.items_table.cellWidget(row, 0)
        pid = combo.currentData() if combo else None
        perfume = next((p for p in self._perfume_cache if p.id == pid), None)

        qty_cb = self.items_table.cellWidget(row, 1)
        qty = qty_cb.currentData() or 0

        price_ml = 0.0 if is_gratis or perfume is None else (perfume.price_per_ml or 0.0)
        partial = 0.0 if is_gratis else price_ml * qty

        # Ustawienie ceny za ml
        price_item = self.items_table.item(row, 2)
        if price_item is None:
            price_item = QTableWidgetItem()
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, 2, price_item)
        price_item.setText(f"{price_ml:.2f}")

        # Ustawienie części zam.
        part_item = self.items_table.item(row, 3)
        if part_item is None:
            part_item = QTableWidgetItem()
            part_item.setFlags(part_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, 3, part_item)
        part_item.setText(f"{partial:.2f}")

        self.recalculate_total()

    def recalculate_total(self):
        total = 0.0
        count_paid = 0
        for r in range(self.items_table.rowCount()):
            flag_item = self.items_table.item(r, 4)
            is_gratis = (flag_item.text() == "1") if flag_item else False
            if is_gratis:
                continue
            part_item = self.items_table.item(r, 3)
            part = float(part_item.text().replace(",", ".")) if part_item else 0.0
            total += part
            count_paid += 1

        ship_key = self.shipping_combo.currentData()
        ship_cost = SHIPPING_OPTIONS.get(ship_key, 0.0)
        total += ship_cost + count_paid * ORDER_VIAL_COST

        self.total_label.setText(f"Suma do zapłaty: {total:.2f} zł")

    def fill_with_order(self, order: Order):
        self.buyer_input.setText(order.buyer or "")
        idx = self.shipping_combo.findData(order.shipping and order.shipping in SHIPPING_OPTIONS and order.shipping)
        if idx >= 0:
            self.shipping_combo.setCurrentIndex(idx)
        self.cb_msg.setChecked(order.sent_message)
        self.cb_money.setChecked(order.received_money)
        self.cb_label.setChecked(order.generated_label)
        self.cb_package.setChecked(order.packed)
        self.cb_shipped.setChecked(order.sent)
        self.cb_confirm.setChecked(order.confirmation_obtained)
        if order.sale_date:
            self.sale_date_edit.setDate(QDate(order.sale_date.year, order.sale_date.month, order.sale_date.day))

        self.items_table.setRowCount(0)
        items = self.session.query(OrderItem).filter_by(order_id=order.id).all()
        for oi in items:
            p = next((x for x in self._perfume_cache if x.id == oi.perfume_id), None)
            self.add_item_row(perfume_obj=p, is_gratis=(oi.price_per_ml == 0), default_ml=int(oi.quantity_ml))

    def save_order(self):
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "Błąd", "Dodaj przynajmniej jedną pozycję!")
            return
        if not any(
            float(self.items_table.item(r, 2).text()) > 0
            for r in range(self.items_table.rowCount())
            if self.items_table.item(r, 4) and self.items_table.item(r, 4).text() == "0"
        ):
            QMessageBox.warning(self, "Błąd", "Przynajmniej jedna pozycja musi być płatna!")
            return
        buyer = self.buyer_input.text().strip()
        if not buyer:
            QMessageBox.warning(self, "Błąd", "Wprowadź kupującego!")
            return

        order = self.order_to_edit or Order()
        if not self.order_to_edit:
            self.session.add(order)

        order.buyer = buyer
        ship_key = self.shipping_combo.currentData()
        order.shipping = SHIPPING_OPTIONS.get(ship_key, 0.0)
        order.total = float(self.total_label.text().split(":")[1].split()[0].replace(",", "."))
        order.sent_message = self.cb_msg.isChecked()
        order.received_money = self.cb_money.isChecked()
        order.generated_label = self.cb_label.isChecked()
        order.packed = self.cb_package.isChecked()
        order.sent = self.cb_shipped.isChecked()
        order.confirmation_obtained = self.cb_confirm.isChecked()
        order.sale_date = self.sale_date_edit.date().toPyDate() if self.cb_money.isChecked() else None

        try:
            if self.order_to_edit:
                self.session.query(OrderItem).filter_by(order_id=order.id).delete()
            for r in range(self.items_table.rowCount()):
                flag_item = self.items_table.item(r, 4)
                is_gratis = (flag_item.text() == "1") if flag_item else False
                pid = self.items_table.cellWidget(r, 0).currentData()
                qty = self.items_table.cellWidget(r, 1).currentData() or 0
                price = 0.0 if is_gratis else float(self.items_table.item(r, 2).text().replace(",", "."))
                part = 0.0 if is_gratis else float(self.items_table.item(r, 3).text().replace(",", "."))
                oi = OrderItem(
                    order_id=order.id,
                    perfume_id=pid,
                    quantity_ml=qty,
                    price_per_ml=price,
                    partial_sum=part
                )
                self.session.add(oi)
            self.session.commit()
            QMessageBox.information(self, "Sukces", "Zamówienie zapisane.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Błąd zapisu", str(e))

    def generate_message_popup(self):
        def fmt(v):
            return f"{int(v)}" if float(v).is_integer() else f"{v:.2f}".replace(".", ",")
        perfume_map = {p.id: p for p in self._perfume_cache}
        items_summary = []
        count_paid = 0
        total = 0.0
        for r in range(self.items_table.rowCount()):
            flag_item = self.items_table.item(r, 4)
            if flag_item and flag_item.text() == "1":
                continue
            pid = self.items_table.cellWidget(r, 0).currentData()
            qty = self.items_table.cellWidget(r, 1).currentData()
            price = float(self.items_table.item(r, 2).text().replace(",", "."))
            part = float(self.items_table.item(r, 3).text().replace(",", "."))
            p = perfume_map.get(pid)
            if not p:
                continue
            items_summary.append(f"{p.brand} {p.name} -> {fmt(qty)} x {fmt(price)} = {fmt(part)}zł")
            total += part
            count_paid += 1
        vial_sum = count_paid * ORDER_VIAL_COST
        total += vial_sum
        delivery_key = self.shipping_combo.currentData()
        delivery_cost = SHIPPING_OPTIONS.get(delivery_key, 0.0)
        total_with = total + delivery_cost
        msg = "Podsumowanie:\n" + "\n".join(items_summary)
        if count_paid:
            msg += f"\nDekanty -> {count_paid} x {ORDER_VIAL_COST:.0f} zł = {fmt(vial_sum)}zł"
        if delivery_cost:
            msg += f"\nZa dostawę {delivery_key} doliczamy {int(delivery_cost)}zł"
        msg += f"\nRazem: {fmt(total_with)}zł\n\nBLIK: 694604172\nJeśli potrzeba, mogę podać numer konta bankowego"
        MessagePopup(msg, parent=self, checkbox_to_mark=self.cb_msg).exec_()
