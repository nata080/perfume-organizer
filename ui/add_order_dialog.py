from datetime import date
from functools import partial
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QCheckBox, QHeaderView, QDateEdit, QMessageBox, QInputDialog, QTextEdit, QWidget, QHBoxLayout
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtCore import QDate, Qt, QTimer

from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem
from models.order import Order
from ui.message_popup import MessagePopup

ORDER_VIAL_COST = 4.0
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
        form = QHBoxLayout()
        form.addWidget(QLabel("Kupujący:"))
        self.buyer_input = QLineEdit()
        self.buyer_input.setPlaceholderText("Imię i nazwisko")
        form.addWidget(self.buyer_input)
        layout.addLayout(form)

        notes_row = QHBoxLayout()
        notes_label = QLabel("Uwagi do zamówienia:")
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Wprowadź dodatkowe uwagi, np. życzenia kupującego, prośby, itp.")
        self.notes_input.setFixedHeight(45)
        notes_row.addWidget(notes_label)
        notes_row.addWidget(self.notes_input)
        layout.addLayout(notes_row)

        self.items_table = QTableWidget(0, 9)
        self.items_table.setHorizontalHeaderLabels(
            ["Perfumy", "Ilość (ml)", "Cena za ml", "Część zam.", "gratis", "Flakon", "Rozbiórka", "Usuń", ""]
        )
        self.items_table.setColumnHidden(4, True)
        self.items_table.setColumnHidden(8, True)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.items_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("Dodaj perfumy")
        add_btn.clicked.connect(lambda: self.add_item_row())
        btns.addWidget(add_btn)
        gratis_btn = QPushButton("+ Gratis")
        gratis_btn.clicked.connect(self.add_gratis_row)
        btns.addWidget(gratis_btn)
        btns.addStretch()
        layout.addLayout(btns)

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

        self.total_label = QLabel("Suma do zapłaty: 0.00 zł")
        layout.addWidget(self.total_label)

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

        # KLUCZOWA ZMIANA: Lista do przechowywania danych checkboxów - IDENTYCZNE jak dla nowych zamówień
        self._pending_checkbox_states = []

        if self.order_to_edit:
            # KLUCZOWA ZMIANA: Opóźnij wypełnienie formularza - IDENTYCZNE jak dla nowych zamówień
            QTimer.singleShot(0, lambda: self.fill_with_order(self.order_to_edit))
        else:
            # Opóźnij inicjalizację pierwszego wiersza dla nowych zamówień
            QTimer.singleShot(0, lambda: self.add_item_row(default_ml=5))

    def get_perfume_id_from_combo(self, combo):
        """
        Bezpieczne pobieranie ID perfumy z QComboBox
        Rozwiązuje problem z currentData() zwracającym None dla pierwszej opcji
        """
        if combo is None:
            return None
        
        # Spróbuj najpierw currentData() - normalny sposób
        pid = combo.currentData()
        if pid is not None:
            return pid
        
        # FALLBACK: jeśli currentData() zwraca None, użyj currentIndex()
        current_index = combo.currentIndex()
        if 0 <= current_index < len(self._perfume_cache):
            return self._perfume_cache[current_index].id
        
        return None

    def add_item_row(self, perfume_obj=None, is_gratis=False, default_ml=5):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        combo = QComboBox()
        combo.setFont(self.font())
        for p in self._perfume_cache:
            combo.addItem(f"{p.brand} {p.name}", p.id)
        if perfume_obj:
            idx = next((i for i, p in enumerate(self._perfume_cache) if p.id == perfume_obj.id), 0)
            combo.setCurrentIndex(idx)
        
        # Wymuś aktualizację dla pierwszej opcji
        if not perfume_obj and self._perfume_cache:
            combo.setCurrentIndex(0)
        
        combo.currentIndexChanged.connect(partial(self.update_price_for_row, row))
        self.items_table.setCellWidget(row, 0, combo)

        qty_widget = QComboBox()
        for ml in ML_OPTIONS:
            qty_widget.addItem(str(ml), ml)
        if default_ml in ML_OPTIONS:
            qty_widget.setCurrentIndex(ML_OPTIONS.index(default_ml))
        qty_widget.currentIndexChanged.connect(partial(self.update_price_for_row, row))
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

        # Wyśrodkowane checkboxy przez QCheckBox w QWidget z QHBoxLayout
        if not is_gratis:
            # Flakon
            flask_checkbox = QCheckBox()
            flask_checkbox.setToolTip("Flakon — po zaznaczeniu ilość (ml) można wpisać ręcznie")
            flask_checkbox.stateChanged.connect(partial(self.on_flask_checkbox_changed, row))
            flask_widget = QWidget()
            flask_layout = QHBoxLayout(flask_widget)
            flask_layout.setContentsMargins(0, 0, 0, 0)
            flask_layout.setAlignment(Qt.AlignCenter)
            flask_layout.addWidget(flask_checkbox)
            flask_widget.show()
            self.items_table.setCellWidget(row, 5, flask_widget)
            
            # Rozbiórka
            split_checkbox = QCheckBox()
            split_checkbox.setToolTip("Pozycja zamówienia jest rozbiórkowa")
            split_checkbox.stateChanged.connect(partial(self.on_split_checkbox_changed, row))
            split_widget = QWidget()
            split_layout = QHBoxLayout(split_widget)
            split_layout.setContentsMargins(0, 0, 0, 0)
            split_layout.setAlignment(Qt.AlignCenter)
            split_layout.addWidget(split_checkbox)
            split_widget.show()
            self.items_table.setCellWidget(row, 6, split_widget)
        else:
            self.items_table.setCellWidget(row, 5, QWidget())
            self.items_table.setCellWidget(row, 6, QWidget())

        del_btn = QPushButton("Usuń")
        del_btn.setToolTip("Usuń tę pozycję zamówienia")
        del_btn.clicked.connect(partial(self.delete_item_row, row))
        self.items_table.setCellWidget(row, 7, del_btn)
        self.items_table.setCellWidget(row, 8, QWidget())

        # KLUCZOWA ZMIANA: Opóźnij aktualizację ceny - IDENTYCZNE jak dla nowych zamówień
        QTimer.singleShot(0, lambda: self.update_price_for_row(row))

    def delete_item_row(self, row):
        self.items_table.removeRow(row)
        # Po usunięciu wiersza aktualizuj callbacki
        for r in range(self.items_table.rowCount()):
            widget = self.items_table.cellWidget(r, 7)
            if isinstance(widget, QPushButton):
                try: widget.clicked.disconnect()
                except Exception: pass
                widget.clicked.connect(partial(self.delete_item_row, r))
            flask_checkbox = self.get_flask_checkbox(r)
            if flask_checkbox:
                try: flask_checkbox.stateChanged.disconnect()
                except Exception: pass
                flask_checkbox.stateChanged.connect(partial(self.on_flask_checkbox_changed, r))
            split_checkbox = self.get_split_checkbox(r)
            if split_checkbox:
                try: split_checkbox.stateChanged.disconnect()
                except Exception: pass
                split_checkbox.stateChanged.connect(partial(self.on_split_checkbox_changed, r))
        self.recalculate_total()

    def get_flask_checkbox(self, row):
        widget = self.items_table.cellWidget(row, 5)
        if widget:
            for cb in widget.findChildren(QCheckBox):
                return cb
        return None

    def get_split_checkbox(self, row):
        widget = self.items_table.cellWidget(row, 6)
        if widget:
            for cb in widget.findChildren(QCheckBox):
                return cb
        return None

    def get_flask_checkbox_state(self, row):
        cb = self.get_flask_checkbox(row)
        return cb and cb.isChecked()

    def get_split_checkbox_state(self, row):
        cb = self.get_split_checkbox(row)
        return cb and cb.isChecked()

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
            line_edit = QLineEdit()
            line_edit.setValidator(QDoubleValidator(0.01, 10000.0, 2))
            
            # Użyj bezpiecznej metody pobierania ID perfumy
            combo = self.items_table.cellWidget(row, 0)
            pid = self.get_perfume_id_from_combo(combo)
            perfume = next((p for p in self._perfume_cache if p.id == pid), None)
            
            if perfume is not None:
                line_edit.setText(str(perfume.to_decant or ''))
            else:
                line_edit.setText(str(current_qty))
            line_edit.editingFinished.connect(partial(self.update_price_for_row, row))
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
            combo.currentIndexChanged.connect(partial(self.update_price_for_row, row))
            self.items_table.setCellWidget(row, 1, combo)
        self.update_price_for_row(row)

    def on_split_checkbox_changed(self, row, state):
        # Możesz dodać tu własną logikę - np. markowanie w tabeli
        pass

    def update_price_for_row(self, row):
        flag_item = self.items_table.item(row, 4)
        is_gratis = (flag_item.text() == "1") if flag_item else False
        
        # Użyj bezpiecznej metody pobierania ID perfumy
        combo = self.items_table.cellWidget(row, 0)
        pid = self.get_perfume_id_from_combo(combo)
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
        partial_sum = 0.0 if is_gratis else price_ml * qty

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
        part_item.setText(f"{partial_sum:.2f}")

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
            if part_item:  # Dodatkowe sprawdzenie bezpieczeństwa
                part = float(part_item.text().replace(",", "."))
                total += part
                count_paid += 1
        ship_key = self.shipping_combo.currentData()
        ship_cost = 0.0 if ship_key == "Własna etykieta" else SHIPPING_OPTIONS.get(ship_key, 0.0)
        total += ship_cost + count_paid * ORDER_VIAL_COST
        self.total_label.setText(f"Suma do zapłaty: {total:.2f} zł")

    def add_gratis_row(self):
        names = [f"{p.brand} {p.name}" for p in self._perfume_cache]
        idx, ok = QInputDialog.getItem(self, "Gratis", "Wybierz perfumy:", names, 0, False)
        if ok:
            p = self._perfume_cache[names.index(idx)]
            self.add_item_row(perfume_obj=p, is_gratis=True, default_ml=3)

    def fill_with_order(self, order: Order):
        """KLUCZOWA ZMIANA: Zastosowano IDENTYCZNY sposób jak dla nowych zamówień"""
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
        
        # KLUCZOWA ZMIANA: Przygotuj dane checkboxów do opóźnionego ustawienia
        self._pending_checkbox_states = []
        
        for i, oi in enumerate(items):
            p = next((x for x in self._perfume_cache if x.id == oi.perfume_id), None)
            is_gratis = (oi.price_per_ml == 0)
            
            # KLUCZOWA ZMIANA: Opóźnij dodanie każdego wiersza - IDENTYCZNE jak dla nowych zamówień
            QTimer.singleShot(0, lambda row=i, perfume=p, gratis=is_gratis, qty=int(round(oi.quantity_ml)): 
                              self.add_item_row(perfume_obj=perfume, is_gratis=gratis, default_ml=qty))
            
            if not is_gratis:
                # Zapisz stany checkboxów do późniejszego ustawienia
                flask_state = bool(getattr(oi, "is_flask", False))
                split_state = bool(getattr(oi, "is_split", False))
                self._pending_checkbox_states.append({
                    'row': i,
                    'flask_state': flask_state,
                    'split_state': split_state
                })
        
        # KLUCZOWA ZMIANA: Opóźnij ustawienie checkboxów - IDENTYCZNE jak dla nowych zamówień
        QTimer.singleShot(100, self.apply_pending_checkbox_states)

    def apply_pending_checkbox_states(self):
        """KLUCZOWA METODA: Zastosuj zapamiętane stany checkboxów - IDENTYCZNE jak dla nowych zamówień"""
        for state_data in self._pending_checkbox_states:
            row = state_data['row']
            flask_state = state_data['flask_state']
            split_state = state_data['split_state']
            
            # Ustaw checkbox flakonu
            flask_checkbox = self.get_flask_checkbox(row)
            if flask_checkbox:
                flask_checkbox.setChecked(flask_state)
            
            # Ustaw checkbox rozbiórki
            split_checkbox = self.get_split_checkbox(row)
            if split_checkbox:
                split_checkbox.setChecked(split_state)
        
        # Wyczyść listę po zastosowaniu
        self._pending_checkbox_states = []

    def save_order(self):
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "Błąd", "Dodaj przynajmniej jedną pozycję!")
            return
        
        # Sprawdź czy jest przynajmniej jedna pozycja płatna (bezpieczne sprawdzenie)
        has_paid_item = False
        for r in range(self.items_table.rowCount()):
            flag_item = self.items_table.item(r, 4)
            price_item = self.items_table.item(r, 2)
            if flag_item and price_item and flag_item.text() == "0" and float(price_item.text()) > 0:
                has_paid_item = True
                break

        if not has_paid_item:
            QMessageBox.warning(self, "Błąd", "Przynajmniej jedna pozycja musi być płatna!")
            return
        
        buyer = self.buyer_input.text().strip()
        if not buyer:
            QMessageBox.warning(self, "Błąd", "Wprowadź kupującego!")
            return
        
        order = self.order_to_edit or Order()
        new_order = not self.order_to_edit
        if new_order:
            self.session.add(order)
            self.session.flush()
        
        order.buyer = buyer
        order.notes = self.notes_input.toPlainText().strip()
        ship_key = self.shipping_combo.currentData()
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
        
        is_split = any([
            self.get_split_checkbox_state(r)
            for r in range(self.items_table.rowCount())
        ])
        order.is_split = is_split

        try:
            if self.order_to_edit:
                self.session.query(OrderItem).filter_by(order_id=order.id).delete()
            
            for r in range(self.items_table.rowCount()):
                flag_item = self.items_table.item(r, 4)
                is_gratis = (flag_item.text() == "1") if flag_item else False
                
                # Użyj bezpiecznej metody pobierania ID perfumy
                combo = self.items_table.cellWidget(r, 0)
                pid = self.get_perfume_id_from_combo(combo)
                
                # Sprawdź czy udało się pobrać ID
                if pid is None:
                    QMessageBox.warning(self, "Błąd", f"Nie można zapisać pozycji w wierszu {r+1} - nie wybrano perfum.")
                    self.session.rollback()
                    return
                
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
                
                price_item = self.items_table.item(r, 2)
                part_item = self.items_table.item(r, 3)
                
                price = 0.0 if (is_gratis or not price_item) else float(price_item.text().replace(",", "."))
                part = 0.0 if (is_gratis or not part_item) else float(part_item.text().replace(",", "."))
                
                is_flask = self.get_flask_checkbox_state(r)
                is_split_poz = self.get_split_checkbox_state(r)
                
                oi = OrderItem(
                    order_id=order.id,
                    perfume_id=pid,
                    quantity_ml=qty,
                    price_per_ml=price,
                    partial_sum=part,
                    is_flask=is_flask,
                    is_split=is_split_poz
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
            
            # Użyj bezpiecznej metody pobierania ID perfumy
            combo = self.items_table.cellWidget(r, 0)
            pid = self.get_perfume_id_from_combo(combo)
            
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
            
            price_item = self.items_table.item(r, 2)
            part_item = self.items_table.item(r, 3)
            
            if not price_item or not part_item or pid is None:
                continue
            
            price = float(price_item.text().replace(",", "."))
            part = float(part_item.text().replace(",", "."))
            
            p = perfume_map.get(pid)
            if not p:
                continue
            
            items_summary.append(f"{p.brand} {p.name} -> {fmt(qty)} x {fmt(price)} = {fmt(part)}zł")
            total += part
            count_paid += 1
        
        vial_sum = count_paid * ORDER_VIAL_COST
        total += vial_sum
        
        delivery_key = self.shipping_combo.currentData()
        is_wlasna_etykieta = delivery_key == "Własna etykieta"
        delivery_cost = 0.0 if is_wlasna_etykieta else SHIPPING_OPTIONS.get(delivery_key, 0.0)
        total_with = total + delivery_cost
        
        msg = "Podsumowanie:\n" + "\n".join(items_summary)
        if count_paid:
            msg += f"\nDekanty -> {count_paid} x {ORDER_VIAL_COST:.0f} zł = {fmt(vial_sum)}zł"
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
