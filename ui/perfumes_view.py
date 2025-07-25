# ui/perfumes_view.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QFileDialog, QComboBox, QLineEdit, QLabel, QHeaderView
)
from PyQt5.QtGui import QColor, QFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import os
from xml.sax.saxutils import escape

from models.database import Session
from models.perfume import Perfume
from models.order_item import OrderItem

EXPORT_COLUMNS = [
    ("Marka", "brand"),
    ("Nazwa", "name"),
    ("Cena/ml [zł]", "price_per_ml"),
    ("Pozostało [ml]", "remaining_ml"),
    ("Link do Fragrantici", "fragrantica_url"),
]

DECANT_COST = 4.0

class PerfumesView(QWidget):
    def __init__(self):
        super().__init__()
        self.session = Session()

        base_font = QFont()
        base_font.setPointSize(9)
        self.setFont(base_font)

        self.filter_status = "Wszystkie"  # domyślny filtr statusu
        self.search_notes = ""  # domyślna wyszukiwarka nut

        layout = QVBoxLayout(self)

        # GÓRA – przyciski akcji
        top_row = QHBoxLayout()
        self.add_button = QPushButton("Dodaj")
        self.add_button.clicked.connect(self.add_perfume)
        top_row.addWidget(self.add_button)

        self.pdf_button = QPushButton("Zapisz do PDF")
        self.pdf_button.clicked.connect(self.save_to_pdf)
        top_row.addWidget(self.pdf_button)

        top_row.addStretch()
        layout.addLayout(top_row)

        # FILTRY I WYSZUKIWARKA
        filter_row = QHBoxLayout()
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["Wszystkie", "Dostępny", "Niedostępny"])
        self.status_filter_combo.currentTextChanged.connect(self.on_filter_change)
        filter_row.addWidget(QLabel("Status:"))
        filter_row.addWidget(self.status_filter_combo)

        self.notes_search_edit = QLineEdit()
        self.notes_search_edit.setPlaceholderText("Szukaj po nutach (np. wanilia, cytrusy)…")
        self.notes_search_edit.textChanged.connect(self.on_filter_change)
        filter_row.addWidget(QLabel("Nuty:"))
        filter_row.addWidget(self.notes_search_edit)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        # TABELA
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        headers = [
            "Status", "Marka", "Nazwa", "Do odlania", "Pozostało",
            "Cena/ml", "Zamówień", "Sprzedaż", "Cena zakupu",
            "Opłaty", "Bilans", "Edytuj", "Usuń"
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSortingEnabled(True)  # sortowanie
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_perfumes()

    def on_filter_change(self, *args):
        self.filter_status = self.status_filter_combo.currentText()
        self.search_notes = self.notes_search_edit.text()
        self.load_perfumes()

    def load_perfumes(self):
        query = self.session.query(Perfume)

        # FILTR statusu
        if self.filter_status == "Dostępny":
            query = query.filter(Perfume.status == "Dostępny")
        elif self.filter_status == "Niedostępny":
            query = query.filter(Perfume.status == "Niedostępny")

        perfumes = query.all()

        # FILTR nut zapachowych
        if self.search_notes.strip():
            keywords = [s.strip().lower() for s in self.search_notes.split(",") if s.strip()]
            def nuty_match(p):
                notes_strs = [p.top_notes or "", p.heart_notes or "", p.base_notes or ""]
                whole = " ".join(notes_strs).lower()
                return all(k in whole for k in keywords)
            perfumes = list(filter(nuty_match, perfumes))

        self.table.setRowCount(len(perfumes))

        for row, p in enumerate(perfumes):
            used_ml = sum(
                oi.quantity_ml
                for oi in self.session.query(OrderItem).filter_by(perfume_id=p.id)
            )
            remaining = max((p.to_decant or 0) - used_ml, 0)
            orders_count = self.session.query(OrderItem) \
                .filter_by(perfume_id=p.id) \
                .filter(OrderItem.price_per_ml > 0) \
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
                if fg:
                    itm.setForeground(QColor(fg))
                return itm

            color = "green" if p.status == "Dostępny" else "red"
            self.table.setItem(row, 0, colored_item(p.status, color))
            self.table.setItem(row, 1, QTableWidgetItem(p.brand or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.to_decant or 0:.2f}"))

            # Pozostało
            if float(remaining).is_integer():
                remaining_str = str(int(remaining))
            else:
                remaining_str = f"{remaining:.2f}"

            rem_col = "green" if remaining > 50 else "gold" if remaining > 20 else "red"
            self.table.setItem(row, 4, colored_item(remaining_str, rem_col))

            self.table.setItem(row, 5, QTableWidgetItem(f"{p.price_per_ml or 0:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(str(orders_count)))
            self.table.setItem(row, 7, QTableWidgetItem(f"{sales_sum:.2f}"))
            self.table.setItem(row, 8, QTableWidgetItem(f"{p.purchase_price or 0:.2f}"))
            self.table.setItem(row, 9, QTableWidgetItem(str(extra_costs)))

            bal_col = "green" if balance > 0 else "red" if balance < 0 else None
            self.table.setItem(row, 10, colored_item(f"{balance:.2f}", bal_col))

            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(lambda _, pid=p.id: self.edit_perfume(pid))
            self.table.setCellWidget(row, 11, edit_btn)

            del_btn = QPushButton("Usuń")
            del_btn.clicked.connect(lambda _, pid=p.id: self.delete_perfume(pid))
            self.table.setCellWidget(row, 12, del_btn)

            # Jeśli perfumy to rozbiórka, podbarwiamy wiersz
            if getattr(p, "is_split", False):
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(210, 234, 255))  # bardzo jasny błękit (RGB)

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

    def save_to_pdf(self):
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
        filename = f"lista_perfum_{today.year}_{today.month:02d}_{today.day:02d}.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz listę jako PDF", filename, "PDF Files (*.pdf)"
        )
        if not path:
            return

        perfumes = self.session.query(Perfume).order_by(Perfume.brand.asc(), Perfume.name.asc()).all()

        headers = [col[0] for col in EXPORT_COLUMNS]
        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle(
            'cell_style',
            parent=styles['Normal'],
            fontName='DejaVuSans',
            fontSize=10,
            leading=12,
        )

        data = [headers]

        for p in perfumes:
            brand = p.brand or ""
            name = p.name or ""
            price = f"{p.price_per_ml or 0:.2f}"

            used_ml = sum(
                oi.quantity_ml for oi in self.session.query(OrderItem).filter_by(perfume_id=p.id)
            )
            remaining = max((p.to_decant or 0) - used_ml, 0)

            if float(remaining).is_integer():
                remaining_str = str(int(remaining))
            else:
                remaining_str = f"{remaining:.2f}"

            url = p.fragrantica_url or ""
            display_text = f"fragrantica - {brand} - {name}"
            if url.strip().lower().startswith(("http://", "https://")):
                link_cell = Paragraph(
                    f'<link href="{escape(url)}">{escape(display_text)}</link>',
                    cell_style
                )
            else:
                link_cell = Paragraph(escape(display_text), cell_style)

            row = [
                Paragraph(escape(brand), cell_style),
                Paragraph(escape(name), cell_style),
                Paragraph(escape(price), cell_style),
                Paragraph(escape(remaining_str), cell_style),
                link_cell,
            ]
            data.append(row)

        col_widths = [90, 170, 85, 90, 210]  # kolumna „Pozostało” poszerzona
        table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ])

        doc = SimpleDocTemplate(
            path,
            pagesize=landscape(A4),
            title="Lista perfum",
            leftMargin=14,
            rightMargin=14,
            topMargin=20,
            bottomMargin=20,
        )

        elements = [
            Paragraph("Lista perfum", styles["Title"]),
            Spacer(1, 12),
            Table(data, colWidths=col_widths, repeatRows=1, style=table_style)
        ]

        doc.build(elements)
        QMessageBox.information(self, "Eksport zakończony", f"PDF zapisany do:\n{path}")
