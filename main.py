from models.database import Base, engine
from models.perfume import Perfume
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

Base.metadata.create_all(engine)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
