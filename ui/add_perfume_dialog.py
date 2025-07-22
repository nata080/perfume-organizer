# ui/add_perfume_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QMessageBox, QFormLayout, QToolButton, QTextEdit
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

import requests
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
import undetected_chromedriver as uc


class AddPerfumeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj nowe perfumy")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("https://www.fragrantica.com/perfume/...")
        link_layout = QHBoxLayout()
        link_layout.addWidget(self.link_input)
        self.fetch_btn = QToolButton(text="🔄")
        self.fetch_btn.setToolTip("Pobierz dane z Fragrantica")
        self.fetch_btn.clicked.connect(self.fetch_from_fragrantica)
        link_layout.addWidget(self.fetch_btn)
        form.addRow("Link z Fragrantica:", link_layout)

        self.brand_input = QLineEdit()
        form.addRow("Marka:", self.brand_input)

        self.name_input = QLineEdit()
        form.addRow("Nazwa:", self.name_input)

        self.to_decant_input = QSpinBox()
        self.to_decant_input.setRange(1, 1000)
        form.addRow("Do odlania (ml):", self.to_decant_input)

        self.price_per_ml_input = QDoubleSpinBox()
        self.price_per_ml_input.setRange(0, 500)
        self.price_per_ml_input.setDecimals(2)
        self.price_per_ml_input.setSuffix(" zł")
        form.addRow("Cena za ml:", self.price_per_ml_input)

        self.buy_price_input = QDoubleSpinBox()
        self.buy_price_input.setRange(0, 5000)
        self.buy_price_input.setDecimals(2)
        self.buy_price_input.setSuffix(" zł")
        form.addRow("Cena zakupu:", self.buy_price_input)

        self.img_preview = QLabel()
        self.img_preview.setFixedSize(120, 150)
        self.img_preview.setStyleSheet("border:1px solid #aaa;")
        form.addRow("Podgląd:", self.img_preview)

        self.error_output = QTextEdit()
        self.error_output.setReadOnly(True)
        self.error_output.setPlaceholderText("Tutaj pojawią się szczegóły błędu do skopiowania...")
        form.addRow("Log błędu:", self.error_output)

        layout.addLayout(form)

        btns = QHBoxLayout()
        save_btn = QPushButton("Dodaj perfumy")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def fetch_from_fragrantica(self):
        self.error_output.clear()
        url = self.link_input.text().strip()
        
        if not url or "fragrantica." not in url:
            QMessageBox.warning(self, "Błąd", "Podaj poprawny link do Fragrantica.")
            return
        
        chrome_options = Options()
        # Podstawowe opcje headless
        chrome_options.add_argument("--headless=new")  # Nowy headless mode
        
        # Opcje bezpieczeństwa i stabilności
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        
        # Opcje dla stabilności w headless mode
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        
        # Opcje dla pamięci i wydajności
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        # Wyłączenie logowania dla czystszego outputu
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--log-level=3")
        
        # Ustawienia User-Agent (opcjonalne)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Inicjalizacja service z pełnym wyciszeniem logów
        service = Service(
            ChromeDriverManager().install(),
            log_output=subprocess.DEVNULL,
            service_args=['--silent']
        )
        
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(60)  # Timeout dla ładowania strony
            
            driver.get(url)
            
            # Czekaj na załadowanie elementów
            wait = WebDriverWait(driver, 15)
            
            # Pobierz tytuł (brand i name)
            h1_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            h1_text = h1_element.text.strip().split()
            
            if len(h1_text) > 1:
                self.brand_input.setText(h1_text[-1])
                self.name_input.setText(" ".join(h1_text[:-1]))
            
            # Pobierz obrazek
            img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.cloud-zoom")))
            img_url = img_element.get_attribute("src")
            
            if img_url:
                response = requests.get(
                    img_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                    timeout=10
                )
                response.raise_for_status()
                
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                scaled_pixmap = pixmap.scaled(120, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_preview.setPixmap(scaled_pixmap)
                
        except TimeoutException:
            error_msg = "Timeout: Nie można załadować strony w określonym czasie."
            self.error_output.setPlainText(error_msg)
            QMessageBox.critical(self, "Błąd", error_msg)
            
        except WebDriverException as e:
            error_msg = f"WebDriver Error: {str(e)}"
            self.error_output.setPlainText(error_msg)
            QMessageBox.critical(self, "Błąd WebDriver", "Problem z przeglądarką Chrome.\nSprawdź szczegóły błędu poniżej.")
            
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self.error_output.setPlainText(error_msg)
            QMessageBox.critical(self, "Nieoczekiwany błąd", "Wystąpił nieoczekiwany błąd.\nSzczegóły dostępne poniżej.")
            
        finally:
            try:
                if 'driver' in locals():
                    driver.quit()
            except:
                pass
    
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        driver = uc.Chrome(options=options)


    def get_data(self):
        return {
            "fragrantica_url": self.link_input.text().strip(),
            "brand": self.brand_input.text().strip(),
            "name": self.name_input.text().strip(),
            "to_decant": self.to_decant_input.value(),
            "price_per_ml": self.price_per_ml_input.value(),
            "purchase_price": self.buy_price_input.value(),
        }
