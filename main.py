import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# WYMUSZENIE OBSŁUGI HiDPI – ustaw PRZED utworzeniem QApplication!
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
