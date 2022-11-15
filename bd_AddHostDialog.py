import os
import subprocess

from bd_globals import Globals as GB
from bd_globals import Cmd
from bd_utils import shell_cmd, deploy_key, ssh_dir_exists, get_ssh_connection
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from yoonico.ui import autoloadUi
import paramiko
import bd_utils


class AddHostDialog(QDialog):
	lineEditHost = None  # type: QLineEdit
	lineEditUser = None  # type: QLineEdit
	lineEditPassword = None  # type: QLineEdit
	lineEditBasePath = None  # type: QLineEdit
	pushButtonAddHost = None  # type: QPushButton
	pushButtonCancel = None  # type: QPushButton
	labelTitle = None  # type: QLabel

	def __init__(self, parent=None, host=None, user=None, basePath=None):
		super(AddHostDialog, self).__init__(parent)
		autoloadUi(self)
		self.console = parent.console
		self.lineEditHost.setText(host)
		self.lineEditUser.setText(user)
		self.lineEditBasePath.setText(basePath)

	def _check_required_fields(self):
		# check if all required fields are filled
		if self.lineEditHost.text() and self.lineEditUser.text() and self.lineEditPassword.text() and self.lineEditBasePath.text():
			self.pushButtonAddHost.setEnabled(True)
			return True
		else:
			self.pushButtonAddHost.setEnabled(False)
			return False

	@Slot(str)
	def on_lineEditPassword_textChanged(self, text):
		self._check_required_fields()

	@Slot(str)
	def on_lineEditHost_textChanged(self, text):
		self._check_required_fields()

	@Slot(str)
	def on_lineEditUser_textChanged(self, text):
		self._check_required_fields()

	@Slot(str)
	def on_lineEditBasePath_textChanged(self, text):
		self._check_required_fields()

	@Slot()
	def on_pushButtonCancel_clicked(self):
		self.reject()

	@Slot()
	def on_pushButtonAddHost_clicked(self):
		user = self.lineEditUser.text()
		host = self.lineEditHost.text()
		pw = self.lineEditPassword.text()
		basePath = self.lineEditBasePath.text()

		self.console.out('Seting up SSH connection for {}@{}...'.format(user, host))

		# Generate rsa key file if it doesn't exist
		if not os.path.exists(GB.rsa_key_file):
			self.console.out('RSA key file not found: {}'.format(GB.rsa_key_file))
			self.console.out('Generating RSA key file...')
			out, err, result = shell_cmd(Cmd.ssh_keygen.format(sshdir=GB.sshdir, appname=GB.appname, hostname=GB.hostname))
			if result != 0:
				QMessageBox(QMessageBox.Critical, 'Error', 'Failed to generate RSA key file:\n\n{}'.format(err)).exec_()
				return
		else:
			self.console.out('RSA key file found: {} \nSkipping ssh-keygen...'.format(GB.rsa_key_file))

		# Get SSH connection
		ssh = get_ssh_connection(host, user, pw)
		if not ssh:
			QMessageBox(QMessageBox.Critical, 'Error', 'Failed to connect to {}@{}'.format(user, host)).exec_()
			return
		# Check to see if basepath exists on the server
		self.console.out('Checking if {} exists on {}@{}'.format(basePath, user, host))
		if not ssh_dir_exists(ssh, basePath):
			QMessageBox(QMessageBox.Critical, 'Error', '{} does not exist on {}@{}'.format(basePath, user, host)).exec_()
			ssh.close()
			return
		# Now copy the .pub file to the remote host
		if os.path.exists(GB.rsa_key_pub_file):
			self.console.out('Copying {} to {}@{}'.format(GB.rsa_key_file, user, host))
			result = deploy_key(ssh, GB.rsa_key_pub_file, user, host, pw)
			if not result:
				QMessageBox(QMessageBox.Critical, 'Error', 'Failed to copy:\n\n{}\n\nto {}@{}'.format(GB.rsa_key_pub_file, user, host)).exec_()
				ssh.close()
				return
		else:
			QMessageBox(QMessageBox.Critical, 'Error', '{} not found'.format(GB.rsa_key_pub_file)).exec_()
			ssh.close()
			return

		self.accept()
