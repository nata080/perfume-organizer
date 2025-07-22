# ui/edit_perfume_dialog.py
import base64
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QMessageBox, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QFileDialog
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
from models.perfume import Perfume

class EditPerfumeDialog(QDialog):
    def __init__(self, perfume: Perfume, parent=None):
        super().__init__(parent)
        self.perfume = perfume
        self.setWindowTitle("Edytuj perfumy")
        self.resize(900, 500)
        # global font
        base_font = QFont()
        base_font.setPointSize(9)
        self.setFont(base_font)
        self.image_data = perfume.image_data or ""

        main_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        # LEWA KOLUMNA – dane podstawowe
        left_col = QVBoxLayout()
        content_layout.addLayout(left_col, 1)

        # Link do Fragrantica
        left_col.addWidget(QLabel("Link do Fragrantica:"))
        self.link_input = QLineEdit(perfume.fragrantica_url or "")
        left_col.addWidget(self.link_input)

        # Status
        left_col.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Dostępny", "Niedostępny"])
        idx = self.status_combo.findText(perfume.status or "Dostępny")
        self.status_combo.setCurrentIndex(idx if idx >= 0 else 0)
        left_col.addWidget(self.status_combo)

        # Marka, Nazwa
        self.brand_input = QLineEdit(perfume.brand or "")
        left_col.addWidget(self.brand_input)
        self.name_input = QLineEdit(perfume.name or "")
        left_col.addWidget(self.name_input)

        # Do odlania, Cena/ml, Cena zakupu
        self.to_decant_input = QSpinBox()
        self.to_decant_input.setRange(1, 10000)
        self.to_decant_input.setSuffix(" ml")
        self.to_decant_input.setValue(int(perfume.to_decant or 0))
        left_col.addWidget(self.to_decant_input)

        self.price_ml_input = QDoubleSpinBox()
        self.price_ml_input.setRange(0, 1000)
        self.price_ml_input.setDecimals(2)
        self.price_ml_input.setSuffix(" zł")
        self.price_ml_input.setValue(perfume.price_per_ml or 0.0)
        left_col.addWidget(self.price_ml_input)

        self.purchase_price_input = QDoubleSpinBox()
        self.purchase_price_input.setRange(0, 10000)
        self.purchase_price_input.setDecimals(2)
        self.purchase_price_input.setSuffix(" zł")
        self.purchase_price_input.setValue(perfume.purchase_price or 0.0)
        left_col.addWidget(self.purchase_price_input)

        # Checkboxy płci
        gender_row = QHBoxLayout()
        self.cb_feminine = QCheckBox("Damski")
        self.cb_masculine = QCheckBox("Męski")
        self.cb_unisex = QCheckBox("Uniseks")
        self.cb_feminine.setChecked(bool(perfume.is_feminine))
        self.cb_masculine.setChecked(bool(perfume.is_masculine))
        self.cb_unisex.setChecked(bool(perfume.is_unisex))
        gender_row.addWidget(self.cb_feminine)
        gender_row.addWidget(self.cb_masculine)
        gender_row.addWidget(self.cb_unisex)
        left_col.addLayout(gender_row)

        season_row = QHBoxLayout()
        season_row.addWidget(QLabel("Pora roku:"))
        self.cb_spring = QCheckBox("Wiosna")
        self.cb_summer = QCheckBox("Lato")
        self.cb_autumn = QCheckBox("Jesień")
        self.cb_winter = QCheckBox("Zima")
        self.cb_spring.setChecked(bool(perfume.season_spring))
        self.cb_summer.setChecked(bool(perfume.season_summer))
        self.cb_autumn.setChecked(bool(perfume.season_autumn))
        self.cb_winter.setChecked(bool(perfume.season_winter))
        season_row.addWidget(self.cb_spring)
        season_row.addWidget(self.cb_summer)
        season_row.addWidget(self.cb_autumn)
        season_row.addWidget(self.cb_winter)
        left_col.addLayout(season_row)

        # Obraz
        img_row = QHBoxLayout()
        self.img_label = QLabel()
        self.img_label.setFixedSize(100, 130)
        self.img_label.setStyleSheet("border:1px solid #888;")
        self.img_label.setAlignment(Qt.AlignCenter)
        img_row.addWidget(self.img_label)
        load_btn = QPushButton("Wczytaj obraz")
        load_btn.clicked.connect(self.choose_image)
        img_row.addWidget(load_btn)
        left_col.addLayout(img_row)
        left_col.addStretch()

        # PRAWA KOLUMNA – nuty zapachowe
        right_col = QVBoxLayout()
        content_layout.addLayout(right_col, 1)
        self.top_notes_list = self._build_notes_group(right_col, "Nuty głowy", perfume.top_notes)
        self.heart_notes_list = self._build_notes_group(right_col, "Nuty serca", perfume.heart_notes)
        self.base_notes_list = self._build_notes_group(right_col, "Nuty bazy", perfume.base_notes)
        right_col.addStretch()

        # Przyciski akcji
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Zapisz zmiany")
        save_btn.clicked.connect(self._validate_and_accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        main_layout.addLayout(btn_row)

        # Załaduj istniejący obraz
        if self.image_data:
            self._set_image_from_bytes(base64.b64decode(self.image_data))

    def _build_notes_group(self, parent, title, csv_notes=""):
        parent.addWidget(QLabel(f"<b>{title}</b>"))
        row = QHBoxLayout()
        note_input = QLineEdit()
        note_input.setPlaceholderText("Dodaj nutę…")
        add_btn = QPushButton("+")
        row.addWidget(note_input)
        row.addWidget(add_btn)
        parent.addLayout(row)
        notes_list = QListWidget()
        parent.addWidget(notes_list)
        for n in (csv_notes or "").split(","):
            t = n.strip()
            if t:
                notes_list.addItem(QListWidgetItem(t))
        def add_note():
            t = note_input.text().strip()
            if t:
                notes_list.addItem(QListWidgetItem(t))
                note_input.clear()
        add_btn.clicked.connect(add_note)
        note_input.returnPressed.connect(add_note)
        return notes_list

    def _validate_and_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Błąd", "Nazwa perfum jest wymagana.")
            return
        self.accept()

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz", "", "Obrazy (*.png *.jpg)")
        if path:
            data = open(path, "rb").read()
            self._set_image_from_bytes(data)

    def _set_image_from_bytes(self, data: bytes):
        pix = QPixmap()
        pix.loadFromData(data)
        thumb = pix.scaled(100, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_label.setPixmap(thumb)
        self.image_data = base64.b64encode(data).decode()

    def get_data(self):
        def list_to_str(lw):
            return ", ".join(lw.item(i).text() for i in range(lw.count()))
        return {
            "fragrantica_url": self.link_input.text().strip(),
            "status": self.status_combo.currentText(),
            "brand": self.brand_input.text().strip(),
            "name": self.name_input.text().strip(),
            "to_decant": float(self.to_decant_input.value()),
            "price_per_ml": float(self.price_ml_input.value()),
            "purchase_price": float(self.purchase_price_input.value()),
            "is_feminine": self.cb_feminine.isChecked(),
            "is_masculine": self.cb_masculine.isChecked(),
            "is_unisex": self.cb_unisex.isChecked(),
            "top_notes": list_to_str(self.top_notes_list),
            "heart_notes": list_to_str(self.heart_notes_list),
            "base_notes": list_to_str(self.base_notes_list),
            "image_data": self.image_data,
            "season_spring": self.cb_spring.isChecked(),
            "season_summer": self.cb_summer.isChecked(),
            "season_autumn": self.cb_autumn.isChecked(),
            "season_winter": self.cb_winter.isChecked(),
        }
