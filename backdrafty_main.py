"""
Flame Archive App

Author: Danny Yoon <twoyoon@gmail.com>
Version: 1.0.0

"""

__version__ = '1.0.0'

from PySide2.QtWidgets import *
from bd_globals import Globals as GB
import bd_MainWindow

if __name__ == '__main__':
	app = QApplication()
	GB.app = app
	main_window = bd_MainWindow.bd_MainWindow()
	main_window.show()

	# setup up Globals
	app.exec_()
