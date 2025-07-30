# ui/orders_view.py

from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QCheckBox,
)

from models.database import Session
from models.order import Order
from models.order_item import OrderItem
from models.perfume import Perfume
from ui.add_order_dialog import AddOrderDialog

# ─────────────────────────────────────────────────────────────────────────────
# WŁASNE KOMÓRKI → POPRAWNE SORTOWANIE LICZB
# ─────────────────────────────────────────────────────────────────────────────

class IntItem(QTableWidgetItem):
    """Komórka sortowana jako liczba całkowita."""
    def __init__(self, value: int):
        super().__init__(str(value))
        self._v = value

    def __lt__(self, other):
        if isinstance(other, IntItem):
            return self._v < other._v
        return super().__lt__(other)

class FloatItem(QTableWidgetItem):
    """Komórka sortowana jako liczba zmiennoprzecinkowa."""
    def __init__(self, value: float, prec: int = 2):
        super().__init__(f"{value:.{prec}f}")
        self._v = value

    def __lt__(self, other):
        if isinstance(other, FloatItem):
            return self._v < other._v
        return super().__lt__(other)

# ─────────────────────────────────────────────────────────────────────────────

class OrdersView(QWidget):
    """Zakładka z listą zamówień."""
    
    def __init__(self, perfumes_view=None, parent=None):
        super().__init__(parent)
        self.session = Session()
        self.perfumes_view = perfumes_view
        
        font = QFont()
        font.setPointSize(9)
        self.setFont(font)
        
        root = QVBoxLayout(self)
        
        # ── FILTRY ──────────────────────────────────────────────────────────
        filters = QHBoxLayout()
        
        # Filtr po stanie
        filters.addWidget(QLabel("Stan:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "Wszystkie", "Wyślij wiadomość", "Oczekiwanie na zapłatę", 
            "Wygeneruj etykietę", "Wyślij paczkę", "Pobierz potwierdzenie", 
            "Uzupełnij dane kupującego", "Zakończone"
        ])
        self.status_combo.currentIndexChanged.connect(self.load_orders)
        filters.addWidget(self.status_combo)
        
        # Checkbox dla rozbiórek
        self.split_checkbox = QCheckBox("Tylko rozbiórki")
        self.split_checkbox.stateChanged.connect(self.load_orders)
        filters.addWidget(self.split_checkbox)
        
        filters.addStretch()
        
        # Wyszukiwarka po kupującym
        filters.addWidget(QLabel("Kupujący:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Szukaj po kupującym…")
        self.search_edit.textChanged.connect(self.load_orders)
        filters.addWidget(self.search_edit)
        
        root.addLayout(filters)
        
        # ── PRZYCISK „DODAJ" ───────────────────────────────────────────────
        add_btn = QPushButton("Dodaj zamówienie")
        add_btn.clicked.connect(self.open_new_order)
        root.addWidget(add_btn)
        
        # ── TABELA ─────────────────────────────────────────────────────────
        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "Lp", "Kupujący", "Perfumy", "Kwota", "Wysyłka", "Stan",
            "Data sprzedaży", "Gratis", "Uwagi", "Data potw.",
            "Edytuj", "Usuń",
        ])
        
        root.addWidget(self.table)
        self.setLayout(root)
        
        # Konfiguracja tabeli
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setFont(font)
        
        # BLOKADA EDYCJI
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.load_orders()
    
    # ─────────────────────────────────────────────────────────────────────
    # ŁADOWANIE
    # ─────────────────────────────────────────────────────────────────────
    
    def load_orders(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        orders = self.session.query(Order).all()
        
        # Filtr po rozbiórce (checkbox)
        if self.split_checkbox.isChecked():
            orders = [o for o in orders if getattr(o, "is_split", False)]
        
        # Filtr po stanie
        selected_status = self.status_combo.currentText()
        if selected_status != "Wszystkie":
            filtered_orders = []
            for order in orders:
                status_txt, _ = self._status(order)
                if status_txt == selected_status:
                    filtered_orders.append(order)
            orders = filtered_orders
        
        # Wyszukiwarka - ZMIANA: obsłuż zarówno nowe pole 'name' jak i stare 'buyer'
        buyer_q = self.search_edit.text().strip().lower()
        if buyer_q:
            def matches_buyer(order):
                # Sprawdź nowe pole 'name' (Facebook)
                name = getattr(order, 'name', None) or ""
                if buyer_q in name.lower():
                    return True
                
                # Sprawdź stare pole 'buyer' (kompatybilność wsteczna)
                buyer = getattr(order, 'buyer', None) or ""
                if buyer_q in buyer.lower():
                    return True
                
                # Sprawdź imię i nazwisko
                first_name = getattr(order, 'first_name', None) or ""
                last_name = getattr(order, 'last_name', None) or ""
                full_name = f"{first_name} {last_name}".strip()
                if buyer_q in full_name.lower():
                    return True
                
                return False
            
            orders = [o for o in orders if matches_buyer(o)]
        
        for lp, order in enumerate(orders, 1):
            items = self.session.query(OrderItem).filter_by(order_id=order.id).all()
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            paid = ", ".join(
                f"{self.session.get(Perfume, i.perfume_id).brand} "
                f"{self.session.get(Perfume, i.perfume_id).name} ({i.quantity_ml} ml)"
                for i in items if i.price_per_ml > 0 and self.session.get(Perfume, i.perfume_id)
            )
            
            gratis = ", ".join(
                f"{self.session.get(Perfume, i.perfume_id).brand} "
                f"{self.session.get(Perfume, i.perfume_id).name}"
                for i in items if i.price_per_ml == 0 and self.session.get(Perfume, i.perfume_id)
            )
            
            status_txt, status_col = self._status(order)
            
            # ZMIANA: wyświetl odpowiednie pole kupującego
            buyer_display = self._get_buyer_display_name(order)
            
            self.table.setItem(row, 0, IntItem(lp))
            self.table.setItem(row, 1, QTableWidgetItem(buyer_display))
            self.table.setItem(row, 2, QTableWidgetItem(paid))
            self.table.setItem(row, 3, FloatItem(order.total))
            self.table.setItem(row, 4, FloatItem(order.shipping))
            self.table.setItem(row, 5, self._colored_item(status_txt, status_col))
            self.table.setItem(row, 6, QTableWidgetItem(str(order.sale_date or "")))
            self.table.setItem(row, 7, QTableWidgetItem(gratis))
            self.table.setItem(row, 8, QTableWidgetItem(order.notes or ""))
            self.table.setItem(
                row, 9,
                QTableWidgetItem(order.confirmation_date.isoformat() if order.confirmation_date else "")
            )
            
            # przyciski
            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(partial(self.edit_order, order.id))
            self.table.setCellWidget(row, 10, edit_btn)
            
            del_btn = QPushButton("Usuń")
            del_btn.clicked.connect(partial(self.delete_order, order.id))
            self.table.setCellWidget(row, 11, del_btn)
            
            # podświetlenie rozbiórek
            if getattr(order, "is_split", False):
                bg = QColor(210, 234, 255)
                for c in range(self.table.columnCount()):
                    cell = self.table.item(row, c)
                    if cell:
                        cell.setBackground(bg)
        
        # Domyślne sortowanie numeryczne po Lp
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.AscendingOrder)
    
    # ─────────────────────────────────────────────────────────────────────
    # POMOCNICZE
    # ─────────────────────────────────────────────────────────────────────
    
    def _get_buyer_display_name(self, order):
        """NOWA METODA: Zwróć najlepszą dostępną nazwę kupującego"""
        # Priorytet: name (FB) > buyer (stare) > imię nazwisko > "Brak danych"
        name = getattr(order, 'name', None)
        if name and name.strip():
            return name.strip()
        
        buyer = getattr(order, 'buyer', None)
        if buyer and buyer.strip():
            return buyer.strip()
        
        first_name = getattr(order, 'first_name', None) or ""
        last_name = getattr(order, 'last_name', None) or ""
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            return full_name
        
        return "Brak danych"
    
    def _has_complete_buyer_data(self, order):
        """NOWA METODA: Sprawdź czy zamówienie ma kompletne dane kupującego"""
        # Sprawdź czy są wypełnione podstawowe dane kontaktowe
        name = getattr(order, 'name', None)
        first_name = getattr(order, 'first_name', None)
        last_name = getattr(order, 'last_name', None)
        email = getattr(order, 'email', None)
        phone = getattr(order, 'phone', None)
        
        # Musi być wypełniona przynajmniej nazwa FB lub imię+nazwisko
        has_name = (name and name.strip()) or (first_name and first_name.strip() and last_name and last_name.strip())
        
        # Musi być wypełniony email lub telefon
        has_contact = (email and email.strip()) or (phone and phone.strip())
        
        return has_name and has_contact
    
    @staticmethod
    def _colored_item(text, color: QColor):
        item = QTableWidgetItem(text)
        item.setForeground(color)
        return item
    
    def _status(self, o: Order):
        """ZAKTUALIZOWANA METODA: Dodano sprawdzanie danych kupującego"""
        if o.confirmation_obtained:
            # NOWA LOGIKA: Sprawdź dane kupującego po zakończeniu wszystkich kroków
            if not self._has_complete_buyer_data(o):
                return "Uzupełnij dane kupującego", QColor("darkviolet")
            return "Zakończone", QColor("gray")
        if o.sent:
            return "Pobierz potwierdzenie", QColor("purple")
        if o.generated_label:
            return "Wyślij paczkę", QColor("red")
        if o.received_money:
            return "Wygeneruj etykietę", QColor("red")
        if o.sent_message:
            return "Oczekiwanie na zapłatę", QColor("black")
        return "Wyślij wiadomość", QColor("red")
    
    # ─────────────────────────────────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────────────────────────────────
    
    def open_new_order(self):
        dlg = AddOrderDialog(self)
        if dlg.exec_():
            if self.perfumes_view:
                self.perfumes_view.reload()  # ZMIANA: użyj reload() zamiast load_perfumes()
            self.load_orders()
    
    def edit_order(self, order_id: int):
        order = self.session.get(Order, order_id)
        if not order:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono zamówienia.")
            return
        
        dlg = AddOrderDialog(self, order_to_edit=order)
        if dlg.exec_():
            if self.perfumes_view:
                self.perfumes_view.reload()  # ZMIANA: użyj reload() zamiast load_perfumes()
            self.load_orders()
    
    def delete_order(self, order_id: int):
        if QMessageBox.question(
            self, "Usuń zamówienie",
            "Czy na pewno chcesz usunąć to zamówienie?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        
        try:
            self.session.query(OrderItem).filter_by(order_id=order_id).delete()
            self.session.query(Order).filter_by(id=order_id).delete()
            self.session.commit()
            
            if self.perfumes_view:
                self.perfumes_view.reload()  # ZMIANA: użyj reload() zamiast load_perfumes()
            self.load_orders()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć: {e}")
