from datetime import date

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QCheckBox, QHeaderView, QDateEdit, QMessageBox, QInputDialog, QTextEdit
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtCore import QDate, Qt

from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem
from models.order import Order
from ui.message_popup import MessagePopup

ORDER_VIAL_COST = 4.0
# MOD: Dodano 'Własna etykieta' do sposobów wysyłki
SHIPPING_OPTIONS = {"InPost": 12.0, "DPD": 10.0, "Własna etykieta": 0.0}
ML_OPTIONS = [3, 5, 10, 15, 20, 30]

class AddOrderDialog(QDialog):
    def __init__(self, parent=None, order_to_edit=None):
        super().__init__(parent)
        self.session = Session()
        self.order_to_edit = order_to_edit
        self.setWindowTitle("Nowe zamówienie" if not order_to_edit else "Edytuj zamówienie")
        self.resize(900, 600)
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

        # Uwagi do zamówienia
        notes_row = QHBoxLayout()
        notes_label = QLabel("Uwagi do zamówienia:")
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Wprowadź dodatkowe uwagi, np. życzenia kupującego, prośby, itp.")
        self.notes_input.setFixedHeight(45)
        notes_row.addWidget(notes_label)
        notes_row.addWidget(self.notes_input)
        layout.addLayout(notes_row)

        # Tabela pozycji zamówienia (7 kolumn: 6 + "Usuń")
        self.items_table = QTableWidget(0, 7)
        self.items_table.setHorizontalHeaderLabels(
            ["Perfumy", "Ilość (ml)", "Cena za ml", "Część zam.", "gratis", "Flakon", "Usuń"]
        )
        self.items_table.setColumnHidden(4, True)  # ukryte 'gratis'
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

        # Suma do zapłaty
        self.total_label = QLabel("Suma do zapłaty: 0.00 zł")
        layout.addWidget(self.total_label)

        # Statusy (checkboxy)
        cb_layout = QHBoxLayout()
        self.cb_msg = QCheckBox("Wiadomość")
        self.cb_money = QCheckBox("Pieniądz")
        self.cb_label = QCheckBox("Etykieta")
        self.cb_package = QCheckBox("Paczka")
        self.cb_shipped = QCheckBox("Wysyłka")
        self.cb_confirm = QCheckBox("Potw. pobrania")
        cb_layout.addWidget(self.cb_msg)
        cb_layout.addWidget(self.cb_money)
        cb_layout.addWidget(self.cb_label)
        cb_layout.addWidget(self.cb_package)
        cb_layout.addWidget(self.cb_shipped)
        cb_layout.addWidget(self.cb_confirm)
        layout.addLayout(cb_layout)

        # Data sprzedaży (aktywna tylko gdy zaznaczony "Pieniądz")
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Data sprzedaży:"))
        self.sale_date_edit = QDateEdit(QDate.currentDate())
        self.sale_date_edit.setCalendarPopup(True)
        self.sale_date_edit.setEnabled(False)
        self.cb_money.stateChanged.connect(lambda state: self.sale_date_edit.setEnabled(state == Qt.Checked))
        date_layout.addWidget(self.sale_date_edit)
        date_layout.addStretch()
        layout.addLayout(date_layout)

        self.cb_confirm.stateChanged.connect(self.on_confirm_checkbox_changed)

        self.confirmation_date = None
        if order_to_edit and getattr(order_to_edit, "confirmation_date", None):
            self.confirmation_date = order_to_edit.confirmation_date

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

        self._perfume_cache = self.session.query(Perfume).filter(Perfume.status == "Dostępny").all()
        self.items_table.cellChanged.connect(lambda r, c: self.update_price_for_row(r))

        if self.order_to_edit:
            self.fill_with_order(self.order_to_edit)
        else:
            self.add_item_row(default_ml=5)

    def add_item_row(self, perfume_obj=None, is_gratis=False, default_ml=5):
        from functools import partial
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        combo = QComboBox()
        combo.setFont(self.font())
        for p in self._perfume_cache:
            combo.addItem(f"{p.brand} {p.name}", p.id)
        if perfume_obj:
            idx = next((i for i, p in enumerate(self._perfume_cache) if p.id == perfume_obj.id), 0)
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _, r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row, 0, combo)
        qty_widget = QComboBox()
        for ml in ML_OPTIONS:
            qty_widget.addItem(str(ml), ml)
        if default_ml in ML_OPTIONS:
            qty_widget.setCurrentIndex(ML_OPTIONS.index(default_ml))
        qty_widget.currentIndexChanged.connect(lambda _, r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row, 1, qty_widget)
        price_item = QTableWidgetItem("0.00")
        price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 2, price_item)
        part_item = QTableWidgetItem("0.00")
        part_item.setFlags(part_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 3, part_item)
        flag_item = QTableWidgetItem("1" if is_gratis else "0")
        flag_item.setFlags(flag_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 4, flag_item)
        flask_checkbox = QCheckBox()
        flask_checkbox.setToolTip("Flakon — po zaznaczeniu ilość (ml) można wpisać ręcznie")
        flask_checkbox.stateChanged.connect(lambda state, r=row: self.on_flask_checkbox_changed(r, state))
        self.items_table.setCellWidget(row, 5, flask_checkbox)
        # Przycisk Usuń
        del_btn = QPushButton("Usuń")
        del_btn.setToolTip("Usuń tę pozycję zamówienia")
        del_btn.clicked.connect(partial(self.delete_item_row, row))
        self.items_table.setCellWidget(row, 6, del_btn)
        self.update_price_for_row(row)

    def delete_item_row(self, row):
        self.items_table.removeRow(row)
        # Przeindeksuj przyciski Usuń
        for r in range(self.items_table.rowCount()):
            widget = self.items_table.cellWidget(r, 6)
            if isinstance(widget, QPushButton):
                try:
                    widget.clicked.disconnect()
                except Exception:
                    pass
                from functools import partial
                widget.clicked.connect(partial(self.delete_item_row, r))
        self.recalculate_total()

    def on_flask_checkbox_changed(self, row, state):
        qty_widget = self.items_table.cellWidget(row, 1)
        if state == Qt.Checked:
            current_qty = 0
            if isinstance(qty_widget, QComboBox):
                current_qty = qty_widget.currentData()
            elif isinstance(qty_widget, QLineEdit):
                try:
                    current_qty = float(qty_widget.text())
                except Exception:
                    current_qty = 0
            from PyQt5.QtWidgets import QLineEdit
            from PyQt5.QtGui import QDoubleValidator
            line_edit = QLineEdit()
            line_edit.setValidator(QDoubleValidator(0.01, 10000.0, 2))
            pid = self.items_table.cellWidget(row, 0).currentData()
            perfume = next((p for p in self._perfume_cache if p.id == pid), None)
            if perfume is not None:
                line_edit.setText(str(perfume.to_decant or ''))
            else:
                line_edit.setText(str(current_qty))
            line_edit.editingFinished.connect(lambda r=row: self.update_price_for_row(r))
            self.items_table.setCellWidget(row, 1, line_edit)
        else:
            combo = QComboBox()
            for ml in ML_OPTIONS:
                combo.addItem(str(ml), ml)
            try:
                current_qty = 0
                if isinstance(qty_widget, QLineEdit):
                    current_qty = float(qty_widget.text())
                elif isinstance(qty_widget, QComboBox):
                    current_qty = qty_widget.currentData()
                if current_qty in ML_OPTIONS:
                    combo.setCurrentIndex(ML_OPTIONS.index(current_qty))
            except Exception:
                pass
            combo.currentIndexChanged.connect(lambda _, r=row: self.update_price_for_row(r))
            self.items_table.setCellWidget(row, 1, combo)
        self.update_price_for_row(row)

    def update_price_for_row(self, row):
        flag_item = self.items_table.item(row, 4)
        is_gratis = (flag_item.text() == "1") if flag_item else False
        combo = self.items_table.cellWidget(row, 0)
        pid = combo.currentData() if combo else None
        perfume = next((p for p in self._perfume_cache if p.id == pid), None)
        qty_widget = self.items_table.cellWidget(row, 1)
        if qty_widget is None:
            qty = 0
        elif isinstance(qty_widget, QComboBox):
            qty = qty_widget.currentData() or 0
        elif isinstance(qty_widget, QLineEdit):
            try:
                qty = float(qty_widget.text())
            except ValueError:
                qty = 0
        else:
            qty = 0
        price_ml = 0.0 if is_gratis or perfume is None else (perfume.price_per_ml or 0.0)
        partial = 0.0 if is_gratis else price_ml * qty
        price_item = self.items_table.item(row, 2)
        if price_item is None:
            price_item = QTableWidgetItem()
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, 2, price_item)
        price_item.setText(f"{price_ml:.2f}")
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

        # MOD: Jeśli wybrano 'Własna etykieta', koszt = 0
        ship_cost = 0.0 if ship_key == "Własna etykieta" else SHIPPING_OPTIONS.get(ship_key, 0.0)
        total += ship_cost + count_paid * ORDER_VIAL_COST
        self.total_label.setText(f"Suma do zapłaty: {total:.2f} zł")

    def add_gratis_row(self):
        names = [f"{p.brand} {p.name}" for p in self._perfume_cache]
        idx, ok = QInputDialog.getItem(self, "Gratis", "Wybierz perfumy:", names, 0, False)
        if ok:
            p = self._perfume_cache[names.index(idx)]
            self.add_item_row(perfume_obj=p, is_gratis=True, default_ml=5)

    def fill_with_order(self, order: Order):
        self.buyer_input.setText(order.buyer or "")
        self.notes_input.setPlainText(order.notes or "")
        idx = self.shipping_combo.findData(order.shipping)
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
        self.confirmation_date = order.confirmation_date
        self.items_table.setRowCount(0)
        items = self.session.query(OrderItem).filter_by(order_id=order.id).all()
        for oi in items:
            p = next((x for x in self._perfume_cache if x.id == oi.perfume_id), None)
            self.add_item_row(perfume_obj=p, is_gratis=(oi.price_per_ml == 0), default_ml=int(round(oi.quantity_ml)))

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
        order.notes = self.notes_input.toPlainText().strip()
        ship_key = self.shipping_combo.currentData()
        # MOD: Dla 'Własna etykieta' wymuś koszt 0.0
        order.shipping = 0.0 if ship_key == "Własna etykieta" else SHIPPING_OPTIONS.get(ship_key, 0.0)
        order.total = float(self.total_label.text().split(":")[1].split()[0].replace(",", "."))
        order.sent_message = self.cb_msg.isChecked()
        order.received_money = self.cb_money.isChecked()
        order.generated_label = self.cb_label.isChecked()
        order.packed = self.cb_package.isChecked()
        order.sent = self.cb_shipped.isChecked()
        order.confirmation_obtained = self.cb_confirm.isChecked()
        order.sale_date = self.sale_date_edit.date().toPyDate() if self.cb_money.isChecked() else None
        if self.cb_confirm.isChecked():
            if not self.confirmation_date:
                self.confirmation_date = date.today()
        else:
            self.confirmation_date = None
        order.confirmation_date = self.confirmation_date
        try:
            if self.order_to_edit:
                self.session.query(OrderItem).filter_by(order_id=order.id).delete()
            for r in range(self.items_table.rowCount()):
                flag_item = self.items_table.item(r, 4)
                is_gratis = (flag_item.text() == "1") if flag_item else False
                pid = self.items_table.cellWidget(r, 0).currentData()
                qty_widget = self.items_table.cellWidget(r, 1)
                if isinstance(qty_widget, QComboBox):
                    qty = qty_widget.currentData() or 0
                elif isinstance(qty_widget, QLineEdit):
                    try:
                        qty = float(qty_widget.text())
                    except ValueError:
                        qty = 0
                else:
                    qty = 0
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
            qty_widget = self.items_table.cellWidget(r, 1)
            if isinstance(qty_widget, QComboBox):
                qty = qty_widget.currentData()
            elif isinstance(qty_widget, QLineEdit):
                try:
                    qty = float(qty_widget.text())
                except ValueError:
                    qty = 0
            else:
                qty = 0
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
        # MOD: Sprawdź, czy wybrano 'Własna etykieta'
        is_wlasna_etykieta = delivery_key == "Własna etykieta"
        delivery_cost = 0.0 if is_wlasna_etykieta else SHIPPING_OPTIONS.get(delivery_key, 0.0)
        total_with = total + delivery_cost
        msg = "Podsumowanie:\n" + "\n".join(items_summary)
        if count_paid:
            msg += f"\nDekanty -> {count_paid} x {ORDER_VIAL_COST:.0f} zł = {fmt(vial_sum)}zł"
        # MOD: informacja o wysyłce tylko jeśli to nie 'Własna etykieta'
        if not is_wlasna_etykieta and delivery_cost:
            msg += f"\nZa dostawę {delivery_key} doliczamy {int(delivery_cost)}zł"
        msg += f"\nRazem: {fmt(total_with)}zł\n\n"
        msg += "BLIK: 694604172\nJeśli potrzeba, mogę podać numer konta bankowego"
        popup = MessagePopup(msg, parent=self, checkbox_to_mark=self.cb_msg)
        popup.exec_()

    def on_confirm_checkbox_changed(self, state):
        if state == Qt.Checked:
            self.confirmation_date = date.today()
        else:
            self.confirmation_date = None
