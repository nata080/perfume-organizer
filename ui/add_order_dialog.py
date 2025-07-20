# ui/add_order_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QComboBox, QPushButton,
    QCheckBox, QHeaderView, QDateEdit, QMessageBox, QInputDialog
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor
from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem
from models.order import Order

ORDER_VIAL_COST = 4.0
SHIPPING_OPTIONS = {
    "InPost": 12.0,
    "DPD": 10.0,
}
ML_OPTIONS = [3, 5, 10, 15, 20, 30]

class AddOrderDialog(QDialog):
    def __init__(self, parent=None, order_to_edit=None):
        super().__init__(parent)
        self.session = Session()
        self.order_to_edit = order_to_edit
        self.setWindowTitle("Nowe zamówienie" if not order_to_edit else "Edytuj zamówienie")
        layout = QVBoxLayout(self)

        # Kupujący
        form = QHBoxLayout()
        form.addWidget(QLabel("Kupujący:"))
        self.buyer_input = QLineEdit()
        form.addWidget(self.buyer_input)
        layout.addLayout(form)

        # Tabela pozycji
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels([
            "Perfumy", "Ilość (ml)", "Cena za ml", "Część zam.", "gratis"
        ])
        self.items_table.setColumnHidden(4, True)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.items_table)

        # Przyciski dodawania pozycji
        btns = QHBoxLayout()
        add_btn = QPushButton("Dodaj perfumy")
        add_btn.clicked.connect(self.add_item_row)
        btns.addWidget(add_btn)
        gratis_btn = QPushButton("+gratis")
        gratis_btn.clicked.connect(self.add_gratis)
        btns.addWidget(gratis_btn)
        layout.addLayout(btns)

        # Wysyłka
        ship_layout = QHBoxLayout()
        ship_layout.addWidget(QLabel("Wysyłka:"))
        self.shipping_combo = QComboBox()
        self.shipping_combo.addItem("", None)
        for k,v in SHIPPING_OPTIONS.items():
            self.shipping_combo.addItem(f"{k} ({v:.2f} zł)", k)
        self.shipping_combo.currentIndexChanged.connect(self.recalculate_total)
        ship_layout.addWidget(self.shipping_combo)
        layout.addLayout(ship_layout)

        # Suma
        self.total_label = QLabel("Suma do zapłaty: 0.00 zł")
        layout.addWidget(self.total_label)

        # Checkboxy
        cb_layout = QHBoxLayout()
        self.cb_msg = QCheckBox("Wiadomość")
        self.cb_money = QCheckBox("Pieniądz")
        self.cb_label = QCheckBox("Etykieta")
        self.cb_package = QCheckBox("Paczka")
        self.cb_shiped = QCheckBox("Wysyłka")
        self.cb_confirm = QCheckBox("Potw. pobrania")
        for cb in (self.cb_msg, self.cb_money, self.cb_label,
                   self.cb_package, self.cb_shiped, self.cb_confirm):
            cb_layout.addWidget(cb)
        layout.addLayout(cb_layout)

        # Data sprzedaży
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Data sprzedaży:"))
        self.sale_date_edit = QDateEdit(QDate.currentDate())
        self.sale_date_edit.setEnabled(False)
        self.sale_date_edit.setCalendarPopup(True)
        self.cb_money.stateChanged.connect(lambda s: self.sale_date_edit.setEnabled(bool(s)))
        date_layout.addWidget(self.sale_date_edit)
        layout.addLayout(date_layout)

        # Zapis/Anuluj
        action_layout = QHBoxLayout()
        save_btn = QPushButton("Zapisz zamówienie")
        save_btn.clicked.connect(self.save_order)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(save_btn)
        action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)

        self._perfume_cache = self.session.query(Perfume).all()
        self.items_table.cellChanged.connect(lambda r,c: self.update_price_for_row(r))

        # Jeśli edycja, wypełnij okno
        if self.order_to_edit:
            self.fill_with_order(self.order_to_edit)
        else:
            self.add_item_row()

    def fill_with_order(self, order):
        # Ustaw pola główne
        self.buyer_input.setText(order.buyer or "")
        # Ustaw wysyłkę
        idx = self.shipping_combo.findData(order.shipping and order.shipping in SHIPPING_OPTIONS and order.shipping)
        if idx >= 0:
            self.shipping_combo.setCurrentIndex(idx)
        # Checkboxy
        self.cb_msg.setChecked(bool(order.sent_message))
        self.cb_money.setChecked(bool(order.received_money))
        self.cb_label.setChecked(bool(order.generated_label))
        self.cb_package.setChecked(bool(order.packed))
        self.cb_shiped.setChecked(bool(order.sent))
        self.cb_confirm.setChecked(bool(order.confirmation_obtained))
        if order.sale_date:
            self.sale_date_edit.setDate(QDate(order.sale_date.year, order.sale_date.month, order.sale_date.day))

        # Wyczyść tabelę i wczytaj pozycje
        self.items_table.setRowCount(0)
        items = self.session.query(OrderItem).filter_by(order_id=order.id).all()
        for oi in items:
            p = next((x for x in self._perfume_cache if x.id==oi.perfume_id), None)
            self.add_item_row(perfume_obj=p, is_gratis=(oi.price_per_ml==0), qty_val=int(oi.quantity_ml))

    def add_item_row(self, perfume_obj=None, is_gratis=False, qty_val=None):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        # Perfume combo
        combo = QComboBox()
        for p in self._perfume_cache:
            label = f"{p.brand} {p.name}"
            combo.addItem(label, p.id)
        if perfume_obj:
            idx = next((i for i,p in enumerate(self._perfume_cache) if p.id==perfume_obj.id), 0)
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _,r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row,0,combo)

        # Qty combo
        qty_cb = QComboBox()
        if is_gratis:
            qty_cb.addItem("3", 3)
            qty_cb.setEnabled(False)
        else:
            for v in ML_OPTIONS:
                qty_cb.addItem(str(v), v)
            if qty_val:
                try: qty_cb.setCurrentIndex(ML_OPTIONS.index(qty_val))
                except: pass
        qty_cb.currentIndexChanged.connect(lambda _,r=row: self.update_price_for_row(r))
        self.items_table.setCellWidget(row,1,qty_cb)

        # Price and part items
        for col in (2,3):
            item = QTableWidgetItem("0.00")
            if is_gratis:
                item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            else:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row,col,item)

        # Gratis flag
        flag = QTableWidgetItem("1" if is_gratis else "0")
        flag.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        self.items_table.setItem(row,4,flag)

        self.update_price_for_row(row)

    def add_gratis(self):
        names = [f"{p.brand} {p.name}" for p in self._perfume_cache]
        idx, ok = QInputDialog.getItem(self, "Gratis", "Wybierz perfumy:", names, 0, False)
        if ok:
            p = self._perfume_cache[names.index(idx)]
            self.add_item_row(perfume_obj=p, is_gratis=True)

    def update_price_for_row(self, row):
        # Ensure flag exists
        flag = self.items_table.item(row,4)
        if flag is None:
            flag = QTableWidgetItem("0")
            flag.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            self.items_table.setItem(row,4,flag)
        is_gratis = (flag.text()=="1")

        combo = self.items_table.cellWidget(row,0)
        qty_cb = self.items_table.cellWidget(row,1)
        pid = combo.currentData() if combo else None
        p = next((x for x in self._perfume_cache if x.id==pid), None)
        price_ml = p.price_per_ml if p and not is_gratis else 0

        # Price cell
        price_item = self.items_table.item(row,2)
        if price_item is None:
            price_item = QTableWidgetItem("0.00")
            self.items_table.setItem(row,2,price_item)
        price_item.setText(f"{price_ml:.2f}")

        # Part sum
        qty = qty_cb.currentData() or 0
        part = 0 if is_gratis else price_ml * qty
        part_item = self.items_table.item(row,3)
        if part_item is None:
            part_item = QTableWidgetItem("0.00")
            self.items_table.setItem(row,3,part_item)
        part_item.setText(f"{part:.2f}")

        self.recalculate_total()

    def recalculate_total(self):
        total=0; cnt=0
        for r in range(self.items_table.rowCount()):
            if self.items_table.item(r,4).text()=="1":
                continue
            part = float(self.items_table.item(r,3).text().replace(',','.'))
            total += part
            cnt +=1
        ship = SHIPPING_OPTIONS.get(self.shipping_combo.currentData(),0)
        total += ship + cnt*ORDER_VIAL_COST
        self.total_label.setText(f"Suma do zapłaty: {total:.2f} zł")

    def save_order(self):
        from models.order_item import OrderItem

        # Validate positions
        rc = self.items_table.rowCount()
        if rc==0:
            QMessageBox.warning(self,"Błąd","Dodaj przynajmniej jedną pozycję!")
            return
        ok=False
        for r in range(rc):
            price = float(self.items_table.item(r,2).text().replace(',','.'))
            qty = self.items_table.cellWidget(r,1).currentData() or 0
            if price>0 and qty>0:
                ok=True; break
        if not ok:
            QMessageBox.warning(self,"Błąd","Przynajmniej jedna pozycja musi być płatna!")
            return

        # Validate buyer
        buyer = self.buyer_input.text().strip()
        if not buyer:
            QMessageBox.warning(self,"Błąd","Wprowadź kupującego!")
            return

        # Prepare Order
        if self.order_to_edit:
            order = self.order_to_edit
        else:
            order = Order()
            Session.add(order)
        order.buyer = buyer
        ship = self.shipping_combo.currentData()
        order.shipping = SHIPPING_OPTIONS.get(ship,0)
        order.total = self.calc_total()
        order.sent_message = self.cb_msg.isChecked()
        order.received_money = self.cb_money.isChecked()
        order.generated_label = self.cb_label.isChecked()
        order.packed = self.cb_package.isChecked()
        order.sent = self.cb_shiped.isChecked()
        order.confirmation_obtained = self.cb_confirm.isChecked()
        order.sale_date = self.sale_date_edit.date().toPyDate() if self.cb_money.isChecked() else None

        try:
            Session.query(OrderItem).filter_by(order_id=order.id).delete()
            for r in range(rc):
                is_g = self.items_table.item(r,4).text()=="1"
                pid = self.items_table.cellWidget(r,0).currentData()
                qty = self.items_table.cellWidget(r,1).currentData() or 0
                p = float(self.items_table.item(r,2).text().replace(',','.'))
                part = float(self.items_table.item(r,3).text().replace(',','.'))
                itm = OrderItem(
                    order_id=order.id,
                    perfume_id=pid,
                    quantity_ml=qty,
                    price_per_ml=0 if is_g else p,
                    partial_sum=0 if is_g else part
                )
                Session.add(itm)
            Session.commit()
        except Exception as e:
            Session.rollback()
            QMessageBox.critical(self,"Błąd zapisu",str(e))
            return
        finally:
            Session.remove()

        QMessageBox.information(self,"Sukces","Zamówienie zapisane")
        self.accept()

    def clear_inputs(self):
        for w in (self.brand_input,self.name_input,
                  self.to_decant_input,self.price_per_ml_input,
                  self.buy_price_input):
            w.clear()

    def calc_total(self):
        total=0; cnt=0
        for r in range(self.items_table.rowCount()):
            if self.items_table.item(r,4).text()=="1":
                continue
            total += float(self.items_table.item(r,3).text().replace(',','.'))
            cnt +=1
        ship = SHIPPING_OPTIONS.get(self.shipping_combo.currentData(),0)
        return total + ship + cnt*ORDER_VIAL_COST
