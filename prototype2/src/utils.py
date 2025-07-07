import os
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QThread
import sys
def resource_path(relative_path):
    """PyInstaller에서 빌드된 실행 파일과 개발 환경 모두에서 작동하는 경로 반환 함수"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class LogReaderThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, process):
        super().__init__()
        self.process = process

    def run(self):
        for line in iter(self.process.stdout.readline, ''):
            if line:
                self.log_signal.emit(line.rstrip('\n'))
        self.process.stdout.close()
        return_code = self.process.wait()
        self.finished_signal.emit(return_code)