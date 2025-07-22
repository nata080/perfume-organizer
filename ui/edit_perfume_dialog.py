from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QLabel, QHBoxLayout,
    QToolButton, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class EditPerfumeDialog(QDialog):
    def __init__(self, perfume, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edytuj perfumy")
        self.perfume = perfume

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Link + przycisk pobierania
        self.link_input = QLineEdit(perfume.fragrantica_url or "")
        link_box = QHBoxLayout()
        link_box.addWidget(self.link_input)
        self.fetch_btn = QToolButton(text="🔄")
        self.fetch_btn.setToolTip("Pobierz dane z Fragrantica")
        self.fetch_btn.clicked.connect(self.fetch_from_fragrantica)
        link_box.addWidget(self.fetch_btn)
        form.addRow("Link z Fragrantica:", link_box)

        # Pola edycji
        self.brand_input = QLineEdit(perfume.brand or "")
        form.addRow("Marka:", self.brand_input)
        self.name_input = QLineEdit(perfume.name or "")
        form.addRow("Nazwa:", self.name_input)

        self.to_decant_input = QSpinBox()
        self.to_decant_input.setRange(1, 1000)
        self.to_decant_input.setValue(int(perfume.to_decant or 0))
        form.addRow("Do odlania (ml):", self.to_decant_input)

        self.price_per_ml_input = QDoubleSpinBox()
        self.price_per_ml_input.setRange(0, 500)
        self.price_per_ml_input.setDecimals(2)
        self.price_per_ml_input.setSuffix(" zł")
        self.price_per_ml_input.setValue(float(perfume.price_per_ml or 0))
        form.addRow("Cena za ml:", self.price_per_ml_input)

        self.buy_price_input = QDoubleSpinBox()
        self.buy_price_input.setRange(0, 5000)
        self.buy_price_input.setDecimals(2)
        self.buy_price_input.setSuffix(" zł")
        self.buy_price_input.setValue(float(perfume.purchase_price or 0))
        form.addRow("Cena zakupu:", self.buy_price_input)

        self.img_preview = QLabel()
        self.img_preview.setFixedSize(120, 150)
        self.img_preview.setStyleSheet("border:1px solid #aaa;")
        form.addRow("Podgląd:", self.img_preview)

        layout.addLayout(form)

        btns = QHBoxLayout()
        save_btn = QPushButton("Zapisz zmiany")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        if perfume.fragrantica_url:
            self.fetch_from_fragrantica()

    def fetch_from_fragrantica(self):
        url = self.link_input.text().strip()
        if not url or "fragrantica." not in url:
            QMessageBox.warning(self, "Błąd", "Podaj poprawny link do Fragrantica.")
            return

        service = Service(ChromeDriverManager().install(), log_path=None)
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--enable-unsafe-swiftshader")
        options.add_argument("--disable-features=VoiceTranscriptionCapability")
        options.add_argument("--disable-features=RendererCodeIntegrity")
        options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        options.add_argument("--log-level=3")

        driver = webdriver.Chrome(service=service, options=options)
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 10)

            toks = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text.strip().split()
            if len(toks) > 1:
                self.brand_input.setText(toks[-1])
                self.name_input.setText(" ".join(toks[:-1]))

            img_url = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.cloud-zoom"))).get_attribute("src")
            resp = requests.get(img_url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
            resp.raise_for_status()
            pix = QPixmap()
            pix.loadFromData(resp.content)
            self.img_preview.setPixmap(pix.scaled(120, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się pobrać danych:\n{e}")
        finally:
            driver.quit()

    def get_data(self):
        return {
            "fragrantica_url": self.link_input.text().strip(),
            "brand": self.brand_input.text().strip(),
            "name": self.name_input.text().strip(),
            "to_decant": self.to_decant_input.value(),
            "price_per_ml": self.price_per_ml_input.value(),
            "purchase_price": self.buy_price_input.value(),
        }
