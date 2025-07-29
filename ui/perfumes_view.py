# ui/perfumes_view.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QAbstractItemView
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
from datetime import datetime
from xml.sax.saxutils import escape
import os
import base64
from PyQt5.QtGui import QPixmap

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem

DECANT_COST = 4.0
EXPORT_COLUMNS = [
    ("Marka", "brand"),
    ("Nazwa", "name"),
    ("Cena/ml [zł]", "price_per_ml"),
    ("Pozostało [ml]", "remaining_ml"),
    ("Link do Fragrantici", "fragrantica_url"),
]


class PerfumesView(QWidget):
    """Widok listy perfum z blokadą edycji komórek."""
    def __init__(self):
        super().__init__()
        self.session = Session()

        font = QFont()
        font.setPointSize(9)
        self.setFont(font)

        # Filtr statusu i wyszukiwarka nut
        self.filter_status = "Wszystkie"
        self.search_notes = ""

        root = QVBoxLayout(self)

        # Przyciski akcji
        top_row = QHBoxLayout()
        add_btn = QPushButton("Dodaj")
        add_btn.clicked.connect(self.add_perfume)
        top_row.addWidget(add_btn)

        pdf_btn = QPushButton("Zapisz do PDF")
        pdf_btn.clicked.connect(self.save_to_pdf)
        top_row.addWidget(pdf_btn)
        top_row.addStretch()
        root.addLayout(top_row)

        # Filtry i wyszukiwarka
        filt_row = QHBoxLayout()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Wszystkie", "Dostępny", "Niedostępny"])
        self.status_combo.currentTextChanged.connect(self.reload)
        filt_row.addWidget(QLabel("Status:"))
        filt_row.addWidget(self.status_combo)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Szukaj po nutach…")
        self.notes_edit.textChanged.connect(self.reload)
        filt_row.addWidget(QLabel("Nuty:"))
        filt_row.addWidget(self.notes_edit)

        filt_row.addStretch()
        root.addLayout(filt_row)

        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "Status", "Marka", "Nazwa", "Do odlania", "Pozostało",
            "Cena/ml", "Zamówień", "Sprzedaż", "Cena zakupu",
            "Opłaty", "Bilans", "Edytuj", "Usuń",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setSortingEnabled(True)

        # BLOKADA EDYCJI KOMÓREK
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        root.addWidget(self.table)
        self.setLayout(root)

        self.reload()

    def reload(self):
        """Filtruje i odświeża tabelę."""
        self.filter_status = self.status_combo.currentText()
        self.search_notes = self.notes_edit.text().strip().lower()

        q = self.session.query(Perfume)
        if self.filter_status == "Dostępny":
            q = q.filter(Perfume.status == "Dostępny")
        elif self.filter_status == "Niedostępny":
            q = q.filter(Perfume.status == "Niedostępny")
        perfumes = q.all()

        if self.search_notes:
            keywords = [w.strip() for w in self.search_notes.split(",") if w.strip()]
            def note_match(p: Perfume):
                text = " ".join([
                    p.top_notes or "", p.heart_notes or "", p.base_notes or ""
                ]).lower()
                return all(k in text for k in keywords)
            perfumes = list(filter(note_match, perfumes))

        self.table.setRowCount(len(perfumes))
        for row, p in enumerate(perfumes):
            # Obliczenia
            orders = self.session.query(OrderItem).filter_by(perfume_id=p.id).all()
            used_ml = sum(o.quantity_ml for o in orders)
            remaining = max((p.to_decant or 0) - used_ml, 0)

            orders_cnt = sum(1 for o in orders if o.price_per_ml > 0)
            sales_sum = sum(
                o.quantity_ml * o.price_per_ml for o in orders if o.price_per_ml > 0
            ) + orders_cnt * DECANT_COST
            extra = orders_cnt * 3  # koszty dodatkowe
            balance = sales_sum - (p.purchase_price or 0) - extra

            # Helper do kolorowania
            def colored_item(text, fg=None):
                item = QTableWidgetItem(str(text))
                if fg:
                    item.setForeground(QColor(fg))
                return item

            # Wypełnianie wiersza
            status_col = "green" if p.status == "Dostępny" else "red"
            self.table.setItem(row, 0, colored_item(p.status, status_col))
            self.table.setItem(row, 1, QTableWidgetItem(p.brand or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.to_decant or 0:.2f}"))

            rem_txt = str(int(remaining)) if float(remaining).is_integer() else f"{remaining:.2f}"
            rem_col = "green" if remaining > 50 else "gold" if remaining > 20 else "red"
            self.table.setItem(row, 4, colored_item(rem_txt, rem_col))

            self.table.setItem(row, 5, QTableWidgetItem(f"{p.price_per_ml or 0:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(str(orders_cnt)))
            self.table.setItem(row, 7, QTableWidgetItem(f"{sales_sum:.2f}"))
            self.table.setItem(row, 8, QTableWidgetItem(f"{p.purchase_price or 0:.2f}"))
            self.table.setItem(row, 9, QTableWidgetItem(f"{extra:.2f}"))
            bal_col = "green" if balance > 0 else "red" if balance < 0 else None
            self.table.setItem(row, 10, colored_item(f"{balance:.2f}", bal_col))

            # Przyciski Edytuj / Usuń
            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(lambda _, pid=p.id: self.edit_perfume(pid))
            self.table.setCellWidget(row, 11, edit_btn)

            del_btn = QPushButton("Usuń")
            del_btn.clicked.connect(lambda _, pid=p.id: self.delete_perfume(pid))
            self.table.setCellWidget(row, 12, del_btn)

            # Obrazek (jeśli istnieje)
            # (opcjonalnie można dodać kolumnę z miniaturą na początku)

            # Podświetlenie rozbiórek
            if getattr(p, "is_split", False):
                bg = QColor(210, 234, 255)
                for c in range(self.table.columnCount()):
                    cell = self.table.item(row, c)
                    if cell:
                        cell.setBackground(bg)

    def add_perfume(self):
        from ui.add_perfume_dialog import AddPerfumeDialog
        dlg = AddPerfumeDialog(self)
        if dlg.exec_():
            try:
                self.session.add(Perfume(**dlg.get_data()))
                self.session.commit()
                self.reload()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Błąd", str(e))

    def edit_perfume(self, pid: int):
        from ui.edit_perfume_dialog import EditPerfumeDialog
        p = self.session.get(Perfume, pid)
        if not p:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono perfum.")
            return
        dlg = EditPerfumeDialog(p, self)
        if dlg.exec_():
            for k, v in dlg.get_data().items():
                setattr(p, k, v)
            self.session.commit()
            self.reload()

    def delete_perfume(self, pid: int):
        if QMessageBox.question(
            self, "Usuń perfumy", "Czy na pewno chcesz usunąć te perfumy?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            self.session.query(Perfume).filter_by(id=pid).delete()
            self.session.commit()
            self.reload()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Błąd", str(e))

    def save_to_pdf(self):
        # Rejestracja fontu
        font_path = os.path.join(os.path.dirname(__file__), 'DejaVuSans.ttf')
        if not os.path.isfile(font_path):
            try:
                import matplotlib.font_manager as fm
                for f in fm.findSystemFonts():
                    if "DejaVuSans" in f:
                        font_path = f
                        break
            except Exception:
                pass
        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))

        today = datetime.now()
        filename = f"lista_perfum_{today:%Y_%m_%d}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz listę jako PDF", filename, "PDF Files (*.pdf)")
        if not path:
            return

        perfumes = self.session.query(Perfume).order_by(Perfume.brand.asc(), Perfume.name.asc()).all()
        headers = [col[0] for col in EXPORT_COLUMNS]
        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle('cell', parent=styles['Normal'], fontName='DejaVuSans', fontSize=10, leading=12)

        data = [headers]
        for p in perfumes:
            # obliczenia jak wyżej...
            used_ml = sum(o.quantity_ml for o in self.session.query(OrderItem).filter_by(perfume_id=p.id))
            remaining = max((p.to_decant or 0) - used_ml, 0)
            remaining_str = str(int(remaining)) if float(remaining).is_integer() else f"{remaining:.2f}"
            row = [
                Paragraph(escape(p.brand or ""), cell_style),
                Paragraph(escape(p.name or ""), cell_style),
                Paragraph(f"{p.price_per_ml or 0:.2f}", cell_style),
                Paragraph(remaining_str, cell_style),
                Paragraph(escape(p.fragrantica_url or ""), cell_style),
            ]
            data.append(row)

        col_widths = [90, 170, 85, 90, 210]
        table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ])

        doc = SimpleDocTemplate(path, pagesize=landscape(A4), title="Lista perfum")
        elements = [Paragraph("Lista perfum", styles["Title"]), Spacer(1, 12), Table(data, colWidths=col_widths, repeatRows=1, style=table_style)]
        doc.build(elements)

        QMessageBox.information(self, "Eksport zakończony", f"PDF zapisany do:\n{path}")
