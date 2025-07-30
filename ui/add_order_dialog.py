from datetime import date
from functools import partial
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QCheckBox, QHeaderView, QDateEdit, QMessageBox, QInputDialog, 
    QTextEdit, QWidget, QGridLayout
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
        self.resize(1000, 700)
        
        base_font = QFont()
        base_font.setPointSize(9)
        self.setFont(base_font)
        
        layout = QVBoxLayout(self)
        
        # === SEKCJA DANYCH KUPUJĄCEGO ===
        customer_section = QVBoxLayout()
        customer_section.addWidget(QLabel("DANE KUPUJĄCEGO:"))
        
        # Główny wiersz z najważniejszymi danymi
        main_row = QHBoxLayout()
        main_row.addWidget(QLabel("Nazwa na FB:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nazwa profilu na Facebook")
        main_row.addWidget(self.name_input)
        customer_section.addLayout(main_row)
        
        # Dodatkowe dane kontaktowe w siatce 2x2
        contact_grid = QGridLayout()
        
        contact_grid.addWidget(QLabel("Imię:"), 0, 0)
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Nieobowiązkowe")
        contact_grid.addWidget(self.first_name_input, 0, 1)
        
        contact_grid.addWidget(QLabel("Nazwisko:"), 0, 2)
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Nieobowiązkowe")
        contact_grid.addWidget(self.last_name_input, 0, 3)
        
        contact_grid.addWidget(QLabel("E-mail:"), 1, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Nieobowiązkowe")
        contact_grid.addWidget(self.email_input, 1, 1)
        
        contact_grid.addWidget(QLabel("Telefon:"), 1, 2)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Nieobowiązkowe")
        contact_grid.addWidget(self.phone_input, 1, 3)
        
        customer_section.addLayout(contact_grid)
        layout.addLayout(customer_section)
        
        # === UWAGI ===
        notes_row = QHBoxLayout()
        notes_label = QLabel("Uwagi do zamówienia:")
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Wprowadź dodatkowe uwagi, np. życzenia kupującego, prośby, itp.")
        self.notes_input.setFixedHeight(45)
        notes_row.addWidget(notes_label)
        notes_row.addWidget(self.notes_input)
        layout.addLayout(notes_row)
        
        # === TABELA PERFUM ===
        self.items_table = QTableWidget(0, 9)
        self.items_table.setHorizontalHeaderLabels([
            "Perfumy", "Ilość (ml)", "Cena za ml", "Część zam.", "gratis", "Flakon", "Rozbiórka", "Usuń", ""
        ])
        self.items_table.setColumnHidden(4, True)
        self.items_table.setColumnHidden(8, True)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.items_table)
        
        # === PRZYCISKI DODAWANIA ===
        btns = QHBoxLayout()
        add_btn = QPushButton("Dodaj perfumy")
        add_btn.clicked.connect(lambda: self.add_item_row())
        btns.addWidget(add_btn)
        
        gratis_btn = QPushButton("+ Gratis")
        gratis_btn.clicked.connect(self.add_gratis_row)
        btns.addWidget(gratis_btn)
        btns.addStretch()
        layout.addLayout(btns)
        
        # === WYSYŁKA ===
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
        
        # === SUMA ===
        self.total_label = QLabel("Suma do zapłaty: 0.00 zł")
        layout.addWidget(self.total_label)
        
        # === CHECKBOXY STANU ===
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
        
        # === DATA SPRZEDAŻY ===
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Data sprzedaży:"))
        self.sale_date_edit = QDateEdit(QDate.currentDate())
        self.sale_date_edit.setCalendarPopup(True)
        self.sale_date_edit.setEnabled(False)
        self.cb_money.stateChanged.connect(lambda state: self.sale_date_edit.setEnabled(state == Qt.Checked))
        date_layout.addWidget(self.sale_date_edit)
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # === OBSŁUGA POTW. POBRANIA ===
        self.cb_confirm.stateChanged.connect(self.on_confirm_checkbox_changed)
        self.confirmation_date = None
        if order_to_edit and getattr(order_to_edit, "confirmation_date", None):
            self.confirmation_date = order_to_edit.confirmation_date
        
        # === PRZYCISKI AKCJI ===
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
        
        # === INICJALIZACJA ===
        self._perfume_cache = self.session.query(Perfume).filter(Perfume.status == "Dostępny").all()  
        self.items_table.cellChanged.connect(lambda r, c: self.update_price_for_row(r))
        self._pending_checkbox_states = []
        
        if self.order_to_edit:
            QTimer.singleShot(0, lambda: self.fill_with_order(self.order_to_edit))
        else:
            QTimer.singleShot(0, lambda: self.add_item_row(default_ml=5))

    def get_perfume_id_from_combo(self, combo):
        """Bezpieczne pobieranie ID perfumy z QComboBox"""
        if combo is None:
            return None
        
        pid = combo.currentData()
        if pid is not None:
            return pid
        
        current_index = combo.currentIndex()
        if 0 <= current_index < len(self._perfume_cache):
            return self._perfume_cache[current_index].id
        return None

    def add_item_row(self, perfume_obj=None, is_gratis=False, default_ml=5):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # COMBO PERFUM
        combo = QComboBox()
        combo.setFont(self.font())
        for p in self._perfume_cache:
            combo.addItem(f"{p.brand} {p.name}", p.id)
        
        if perfume_obj:
            idx = next((i for i, p in enumerate(self._perfume_cache) if p.id == perfume_obj.id), 0)
            combo.setCurrentIndex(idx)
        elif self._perfume_cache:
            combo.setCurrentIndex(0)
            
        combo.currentIndexChanged.connect(partial(self.update_price_for_row, row))
        self.items_table.setCellWidget(row, 0, combo)
        
        # ILOŚĆ ML
        qty_widget = QComboBox()
        for ml in ML_OPTIONS:
            qty_widget.addItem(str(ml), ml)
        if default_ml in ML_OPTIONS:
            qty_widget.setCurrentIndex(ML_OPTIONS.index(default_ml))
        qty_widget.currentIndexChanged.connect(partial(self.update_price_for_row, row))
        self.items_table.setCellWidget(row, 1, qty_widget)
        
        # CENA ZA ML (readonly)
        price_item = QTableWidgetItem("0.00")
        price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 2, price_item)
        
        # CZĘŚĆ ZAMÓWIENIA (readonly)
        part_item = QTableWidgetItem("0.00")
        part_item.setFlags(part_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 3, part_item)
        
        # FLAGA GRATIS (hidden)
        flag_item = QTableWidgetItem("1" if is_gratis else "0")
        flag_item.setFlags(flag_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 4, flag_item)
        
        # CHECKBOXY
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
        
        # PRZYCISK USUŃ
        del_btn = QPushButton("Usuń")
        del_btn.setToolTip("Usuń tę pozycję zamówienia")
        del_btn.clicked.connect(partial(self.delete_item_row, row))
        self.items_table.setCellWidget(row, 7, del_btn)
        
        self.items_table.setCellWidget(row, 8, QWidget())
        
        QTimer.singleShot(0, lambda: self.update_price_for_row(row))

    def delete_item_row(self, row):
        self.items_table.removeRow(row)
        
        # Aktualizuj callbacki po usunięciu
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
        pass

    def update_price_for_row(self, row):
        flag_item = self.items_table.item(row, 4)
        is_gratis = (flag_item.text() == "1") if flag_item else False
        
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
            if part_item:
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
        """Wypełnienie formularza danymi istniejącego zamówienia"""
        # NOWE POLA - kompatybilność wsteczna
        self.name_input.setText(getattr(order, 'name', '') or getattr(order, 'buyer', '') or "")
        self.first_name_input.setText(getattr(order, 'first_name', '') or "")
        self.last_name_input.setText(getattr(order, 'last_name', '') or "")
        self.email_input.setText(getattr(order, 'email', '') or "")
        self.phone_input.setText(getattr(order, 'phone', '') or "")
        
        self.notes_input.setPlainText(order.notes or "")
        
        # Wysyłka - najpierw próbuj znaleźć po nazwie klucza
        shipping_found = False
        if hasattr(order, 'shipping_type'):
            for i in range(self.shipping_combo.count()):
                if self.shipping_combo.itemData(i) == order.shipping_type:
                    self.shipping_combo.setCurrentIndex(i)
                    shipping_found = True
                    break
        
        # Jeśli nie znaleziono po typie, spróbuj po wartości (fallback)
        if not shipping_found and hasattr(order, 'shipping'):
            for name, cost in SHIPPING_OPTIONS.items():
                if abs(cost - (order.shipping or 0)) < 0.01:
                    for i in range(self.shipping_combo.count()):
                        if self.shipping_combo.itemData(i) == name:
                            self.shipping_combo.setCurrentIndex(i)
                            break
                    break
        
        # Checkboxy
        self.cb_msg.setChecked(order.sent_message)
        self.cb_money.setChecked(order.received_money)
        self.cb_label.setChecked(order.generated_label)
        self.cb_package.setChecked(order.packed)
        self.cb_shipped.setChecked(order.sent)
        self.cb_confirm.setChecked(order.confirmation_obtained)
        
        if order.sale_date:
            self.sale_date_edit.setDate(QDate(order.sale_date.year, order.sale_date.month, order.sale_date.day))
        
        self.confirmation_date = order.confirmation_date
        
        # Wczytaj pozycje zamówienia
        self.items_table.setRowCount(0)
        items = self.session.query(OrderItem).filter_by(order_id=order.id).all()
        
        self._pending_checkbox_states = []
        
        for i, oi in enumerate(items):
            p = next((x for x in self._perfume_cache if x.id == oi.perfume_id), None)
            is_gratis = (oi.price_per_ml == 0)
            
            QTimer.singleShot(0, lambda row=i, perfume=p, gratis=is_gratis, qty=int(round(oi.quantity_ml)):
                self.add_item_row(perfume_obj=perfume, is_gratis=gratis, default_ml=qty))
            
            if not is_gratis:
                flask_state = bool(getattr(oi, "is_flask", False))
                split_state = bool(getattr(oi, "is_split", False))
                self._pending_checkbox_states.append({
                    'row': i,
                    'flask_state': flask_state,
                    'split_state': split_state
                })
        
        QTimer.singleShot(100, self.apply_pending_checkbox_states)

    def apply_pending_checkbox_states(self):
        """Zastosuj zapamiętane stany checkboxów"""
        for state_data in self._pending_checkbox_states:
            row = state_data['row']
            flask_state = state_data['flask_state']
            split_state = state_data['split_state']
            
            flask_checkbox = self.get_flask_checkbox(row)
            if flask_checkbox:
                flask_checkbox.setChecked(flask_state)
            
            split_checkbox = self.get_split_checkbox(row)
            if split_checkbox:
                split_checkbox.setChecked(split_state)
        
        self._pending_checkbox_states = []

    def save_order(self):
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "Błąd", "Dodaj przynajmniej jedną pozycję!")
            return
        
        # Sprawdź czy jest przynajmniej jedna pozycja płatna
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
        
        # ZMIANA: sprawdź nazwę na FB zamiast "kupującego"
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Błąd", "Wprowadź nazwę profilu (FB)!")
            return
        
        order = self.order_to_edit or Order()
        new_order = not self.order_to_edit
        
        if new_order:
            self.session.add(order)
            self.session.flush()
        
        # NOWE POLA
        order.name = name
        order.first_name = self.first_name_input.text().strip() or None
        order.last_name = self.last_name_input.text().strip() or None  
        order.email = self.email_input.text().strip() or None
        order.phone = self.phone_input.text().strip() or None
        
        # KOMPATYBILNOŚĆ WSTECZNA - ustaw też buyer dla starych wersji
        if hasattr(order, 'buyer'):
            order.buyer = name
        
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
                
                combo = self.items_table.cellWidget(r, 0)
                pid = self.get_perfume_id_from_combo(combo)
                
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
    # ZMIANA: Jeśli tylko jedna pozycja płatna, użyj "Dekant" i uproszczoną formę
            if count_paid == 1:
                msg += f"\n\nDekant -> {fmt(vial_sum)}zł"
            else:
                msg += f"\n\nDekanty -> {count_paid} x {ORDER_VIAL_COST:.0f} zł = {fmt(vial_sum)}zł"

        if not is_wlasna_etykieta and delivery_cost:
            msg += f"\n\nZa dostawę {delivery_key} doliczamy {int(delivery_cost)}zł"

        # ZMIANA: Dodano enter przed "Razem"
        msg += f"\n\nRazem: {fmt(total_with)}zł\n\n"
        msg += "BLIK: 694604172\nJeśli potrzeba, mogę podać numer konta bankowego"
        
        popup = MessagePopup(msg, parent=self, checkbox_to_mark=self.cb_msg)
        popup.exec_()

    def on_confirm_checkbox_changed(self, state):
        if state == Qt.Checked:
            self.confirmation_date = date.today()
        else:
            self.confirmation_date = None
