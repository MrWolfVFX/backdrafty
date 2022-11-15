from PySide2.QtCore import Qt, QCoreApplication
from PySide2.QtWidgets import QTextEdit

import sys


class ConsoleWidget(QTextEdit):

	def __init__(self, parent=None, prompt='', textcolor=Qt.cyan, errorcolor=Qt.red):
		super(ConsoleWidget, self).__init__(parent)
		self.textcolor = textcolor
		self.errorcolor = errorcolor
		self.prompt = prompt
		self.setReadOnly(True)
		self.ensureCursorVisible()

	def out(self, text, color=None):
		if color is None:
			self.setTextColor(self.textcolor)
		else:
			self.setTextColor(color)
		if text == '\n':
			formatted_text = text
		else:
			formatted_text = '{}{}'.format(self.prompt, text)
		# print(text)
		self.append(formatted_text)
		qapp = QCoreApplication.instance()
		qapp.processEvents()

	def err(self, text, color=None):
		if color is None:
			self.setTextColor(self.errorcolor)
		else:
			self.setTextColor(color)
		if text == '\n':
			formatted_text = text
		else:
			formatted_text = '{}{}'.format(self.prompt, text)
		# print(text, file=sys.stderr)
		self.append(formatted_text)
		qapp = QCoreApplication.instance()
		qapp.processEvents()


if __name__ == '__main__':
	from PySide2.QtWidgets import QApplication

	app = QApplication(sys.argv)
	console = ConsoleWidget(prompt='#')
	console.show()
	console.out('Hello World!')
	console.err('Error message')
	console.err('EVERYONE PANIC!')
	console.out('Nothing is wrong\nMove along.')
	sys.exit(app.exec_())
