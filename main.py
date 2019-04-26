__author__ = 'Nick Sarris (ngs5st)'

import os, sys, window
from PySide.QtGui import *

if __name__ == '__main__':

    app = QApplication(sys.argv)
    form = window.MainWindow()
    form.show()
    app.exec_()