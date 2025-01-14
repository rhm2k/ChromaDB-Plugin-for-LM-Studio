# Creates threads for gui functions

from PySide6.QtCore import QThread, Signal
import server_connector
import create_database

class CreateDatabaseThread(QThread):
    def run(self):
        create_database.main()

class SubmitButtonThread(QThread):
    responseSignal = Signal(str)

    def __init__(self, user_question, parent=None):
        super(SubmitButtonThread, self).__init__(parent)
        self.user_question = user_question

    def run(self):
        response = server_connector.ask_local_chatgpt(self.user_question)
        self.responseSignal.emit(response['answer'])
