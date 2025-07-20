import sys
from PyQt5.QtWidgets import QApplication
from models.database import Base, engine
from ui.main_window import MainWindow

# Tworzy tabele w bazie danych (tylko za pierwszym razem)
Base.metadata.create_all(engine)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
