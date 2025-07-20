from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QApplication

class MessagePopup(QDialog):
    def __init__(self, message, parent=None, checkbox_to_mark=None):
        super().__init__(parent)
        self.setWindowTitle("Podsumowanie dla kupującego")
        self.setMinimumWidth(420)
        self.checkbox_to_mark = checkbox_to_mark

        layout = QVBoxLayout(self)
        info = QLabel("Poniżej gotowa treść do przekazania kupującemu. Możesz ją skopiować:")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setText(message)
        layout.addWidget(self.editor)

        copy_btn = QPushButton("Kopiuj do schowka")
        copy_btn.clicked.connect(self.copy_and_close)
        layout.addWidget(copy_btn)

    def copy_and_close(self):
        clipboard = QApplication.instance().clipboard()
        clipboard.setText(self.editor.toPlainText())
        if self.checkbox_to_mark is not None:
            self.checkbox_to_mark.setChecked(True)
        self.accept()
