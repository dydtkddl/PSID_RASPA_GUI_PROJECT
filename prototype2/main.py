import os
os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"  # WebGL → CPU fallback

from PyQt5.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)  # CPU 기반 OpenGL 사용

import sys
from PyQt5.QtWidgets import QApplication
from src.RASPA_GUI import RaspaGUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = RaspaGUI()
    gui.show()
    sys.exit(app.exec_())
