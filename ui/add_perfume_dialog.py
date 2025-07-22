# ui/add_perfume_dialog.py

import base64
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QPushButton, QMessageBox, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QFileDialog
)
from PyQt5.QtGui import QPixmap, QFont, QDoubleValidator
from PyQt5.QtCore import Qt

class AddPerfumeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj nowe perfumy")
        self.resize(900, 500)

        base_font = QFont()
        base_font.setPointSize(9)
        self.setFont(base_font)

        self.image_data: str = ""

        main_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        # LEWA KOLUMNA – dane podstawowe
        left_col = QVBoxLayout()
        content_layout.addLayout(left_col, 1)

        # Link do Fragrantica
        left_col.addWidget(QLabel("Link do Fragrantica:"))
        self.link_input = QLineEdit()
        left_col.addWidget(self.link_input)

        # Status
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Dostępny", "Niedostępny"])
        status_row.addWidget(self.status_combo)
        left_col.addLayout(status_row)

        # Marka
        brand_row = QHBoxLayout()
        brand_row.addWidget(QLabel("Marka:"))
        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Marka")
        brand_row.addWidget(self.brand_input)
        left_col.addLayout(brand_row)

        # Nazwa
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Nazwa:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nazwa")
        name_row.addWidget(self.name_input)
        left_col.addLayout(name_row)

        # Do odlania (ml)
        decant_row = QHBoxLayout()
        decant_row.addWidget(QLabel("Do odlania (ml):"))
        self.to_decant_input = QLineEdit()
        validator = QDoubleValidator(0.0, 10000.0, 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.to_decant_input.setValidator(validator)
        decant_row.addWidget(self.to_decant_input)
        left_col.addLayout(decant_row)

        # Cena za ml (zł)
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Cena za ml (zł):"))
        self.price_ml_input = QDoubleSpinBox()
        self.price_ml_input.setRange(0.00, 1000.00)
        self.price_ml_input.setDecimals(2)
        self.price_ml_input.setSuffix(" zł")
        price_row.addWidget(self.price_ml_input)
        left_col.addLayout(price_row)

        # Cena zakupu (zł)
        purchase_row = QHBoxLayout()
        purchase_row.addWidget(QLabel("Cena zakupu (zł):"))
        self.purchase_price_input = QDoubleSpinBox()
        self.purchase_price_input.setRange(0.00, 10000.00)
        self.purchase_price_input.setDecimals(2)
        self.purchase_price_input.setSuffix(" zł")
        purchase_row.addWidget(self.purchase_price_input)
        left_col.addLayout(purchase_row)

        # Checkboxy płci
        gender_row = QHBoxLayout()
        gender_row.addWidget(QLabel("Płeć:"))
        self.cb_feminine = QCheckBox("Damski")
        self.cb_masculine = QCheckBox("Męski")
        self.cb_unisex = QCheckBox("Uniseks")
        gender_row.addWidget(self.cb_feminine)
        gender_row.addWidget(self.cb_masculine)
        gender_row.addWidget(self.cb_unisex)
        left_col.addLayout(gender_row)

        # Checkboxy pór roku pod płcią
        season_row = QHBoxLayout()
        season_row.addWidget(QLabel("Pora roku:"))
        self.cb_spring = QCheckBox("Wiosna")
        self.cb_summer = QCheckBox("Lato")
        self.cb_autumn = QCheckBox("Jesień")
        self.cb_winter = QCheckBox("Zima")
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
        load_img_btn = QPushButton("Wczytaj obraz")
        load_img_btn.clicked.connect(self.choose_image)
        load_img_btn.setFocusPolicy(Qt.NoFocus)
        img_row.addWidget(load_img_btn)
        left_col.addLayout(img_row)
        left_col.addStretch()

        # PRAWA KOLUMNA – nuty zapachowe
        right_col = QVBoxLayout()
        content_layout.addLayout(right_col, 1)
        self.top_notes_list   = self._build_notes_group(right_col, "Nuty głowy")
        self.heart_notes_list = self._build_notes_group(right_col, "Nuty serca")
        self.base_notes_list  = self._build_notes_group(right_col, "Nuty bazy")
        right_col.addStretch()

        # Przyciski akcji
        btn_row = QHBoxLayout()
        save_btn   = QPushButton("Dodaj perfumy")
        save_btn.clicked.connect(self._validate_and_accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        main_layout.addLayout(btn_row)

    def _build_notes_group(self, parent, title):
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

        def add_note():
            text = note_input.text().strip()
            if text:
                notes_list.addItem(QListWidgetItem(text))
                note_input.clear()

        add_btn.clicked.connect(add_note)
        # tylko jedno połączenie: Enter → add_note
        note_input.returnPressed.connect(add_note)

        return notes_list

    def _validate_and_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Błąd", "Nazwa perfum jest wymagana.")
            return
        self.accept()

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz obraz", "", "Obrazy (*.png *.jpg *.jpeg)"
        )
        if path:
            with open(path, "rb") as f:
                data = f.read()
            pix = QPixmap()
            pix.loadFromData(data)
            thumb = pix.scaled(100, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_label.setPixmap(thumb)
            self.image_data = base64.b64encode(data).decode()

    def get_data(self) -> dict:
        def list_to_str(lw):
            return ", ".join(lw.item(i).text() for i in range(lw.count()))

        decant_text = self.to_decant_input.text().strip().replace(",", ".")
        to_decant = float(decant_text) if decant_text else 0.0

        return {
            "fragrantica_url": self.link_input.text().strip(),
            "status":          self.status_combo.currentText(),
            "brand":           self.brand_input.text().strip(),
            "name":            self.name_input.text().strip(),
            "to_decant":       to_decant,
            "price_per_ml":    float(self.price_ml_input.value()),
            "purchase_price":  float(self.purchase_price_input.value()),
            "is_feminine":     self.cb_feminine.isChecked(),
            "is_masculine":    self.cb_masculine.isChecked(),
            "is_unisex":       self.cb_unisex.isChecked(),
            "season_spring": self.cb_spring.isChecked(),
            "season_summer": self.cb_summer.isChecked(),
            "season_autumn": self.cb_autumn.isChecked(),
            "season_winter": self.cb_winter.isChecked(),
            "top_notes":       list_to_str(self.top_notes_list),
            "heart_notes":     list_to_str(self.heart_notes_list),
            "base_notes":      list_to_str(self.base_notes_list),
            "image_data":      getattr(self, "image_data", "")
        }
