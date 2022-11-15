import datetime
import json
# Paramiko example from: https://stackoverflow.com/questions/10745138/python-paramiko-ssh


from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

from bd_globals import Cmd
from bd_globals import Globals as GB
from bd_utils import *
from yoonico.ui import autoloadUi
import yoonico.ui.console_widget as yConsole
import yoonico.flame as yFlame
from bd_AddHostDialog import AddHostDialog

__version__ = '1.0.0'


class bd_MainWindow(QMainWindow):
	# UI Placeholders
	statusbar = None  # type: QStatusBar
	tableWidget = None  # type: QTableWidget
	console = None  # type: yConsole.ConsoleWidget
	pushButtonFlame = None  # type: QPushButton
	pushButtonList = None  # type: QPushButton
	pushButtonArchive = None  # type: QPushButton
	pushButtonCalcSize = None  # type: QPushButton
	tableWidgetHosts = None  # type: QTableWidget
	splitter = None  # type: QSplitter

	# Table columns
	PROJ_HOST, PROJ_NAME, PROJ_WORKSPACE, PROJ_SIZE, PROJ_DEST, PROJ_STATUS, PROJ_COMMENT, = range(7)

	HOST_ENABLED, HOST_NAME, HOST_USER, HOST_BASEPATH = range(4)

	def __init__(self, parent=None):
		super(bd_MainWindow, self).__init__(parent)
		autoloadUi(self)
		self.pushButtonArchive.setEnabled(False)
		self.pushButtonCalcSize.setEnabled(False)
		self.splitter.setSizes([450, 1650])
		self.tableWidget.setColumnWidth(self.PROJ_DEST, 400)
		GB.console = self.console
		self._load_hosts()
		self.tableWidgetHosts.itemDoubleClicked.connect(self.tableWidgetHosts_itemDoubleClicked)

	def closeEvent(self, event):

		result = QMessageBox.question(self,"Confirm Exit...","Are you sure you want to exit ?", QMessageBox.Yes | QMessageBox.No)
		event.ignore()

		if result == QMessageBox.Yes:
			self._save_hosts()
			event.accept()


	# UI Slots (automatically connected)


	@Slot()
	def on_actionListProjects_triggered(self):

		self.console.clear()
		# delete all rows in table
		self.tableWidget.setRowCount(0)
		self._buttons_enabled(False)

		for row in range(self.tableWidgetHosts.rowCount()):
			enabled = self.tableWidgetHosts.item(row, self.HOST_ENABLED).checkState()
			if enabled != Qt.Checked:
				continue
			host = self.tableWidgetHosts.item(row, self.HOST_NAME).text()
			user = self.tableWidgetHosts.item(row, self.HOST_USER).text()

			self.console.out('**************** {} ****************'.format(host))

			try:
				ssh = get_ssh_connection(host, user)
				if ssh is None:
					continue
				# Parse the ProjectGroup line from Autodesk project.db for project list
				stdin, stdout, stderr = ssh.exec_command(Cmd.list_project_db, timeout=GB.timeout)
				out = stdout.read().decode('utf-8')
				projects = yFlame.get_project_info_from_str(out)
				for project in projects:
					workspace_cmd = Cmd.list_workspaces.format(partition=project.get('HardPtn'), project=project.get('Name'))
					stdin, stdout, stderr = ssh.exec_command(workspace_cmd, )
					out = stdout.read().decode('utf-8').strip()
					if out:
						for line in out.splitlines():
							row = self.tableWidget.rowCount()
							projname = project.get('Name')
							workspace = line.replace('.wksp', '').strip()
							self.tableWidget.insertRow(row)
							self.tableWidget.setItem(row, self.PROJ_HOST, QTableWidgetItem(host))
							self.tableWidget.setItem(row, self.PROJ_NAME, QTableWidgetItem(projname))
							self.tableWidget.setItem(row, self.PROJ_WORKSPACE, QTableWidgetItem(workspace))
							# todo: set DEST path here
							self.console.out(projname)

			except Exception as e:
				traceback.print_exc()
				errormsg = traceback.format_exc()
				self.console.err('{}: PROJECT LISTING FAILED!'.format(host))
				self.console.err(errormsg)
				continue
			ssh.close()
		self._banner('Project Listing Complete')
		self.console.out(' ')
		self.tableWidget.resizeColumnToContents(self.PROJ_HOST)
		self.tableWidget.resizeColumnToContents(self.PROJ_NAME)
		self.tableWidget.resizeColumnToContents(self.PROJ_WORKSPACE)
		self._buttons_enabled(True)

	@Slot()
	def on_actionArchiveSelected_triggered(self):

		self._buttons_enabled(False)

		# get selected rows self.tableWidget
		selected_rows = self.tableWidget.selectionModel().selectedRows()
		for row in selected_rows:
			host = self.tableWidget.item(row.row(), self.PROJ_HOST).text()
			proj = self.tableWidget.item(row.row(), self.PROJ_NAME).text()
			job = self._job_name_from_project(proj)
			workspace = self.tableWidget.item(row.row(), self.PROJ_WORKSPACE).text()

			enabled, user, basepath = GB.host_dict[host]
			self.console.out('**************** {} ****************'.format(host))

			self._set_status(row, 'ARCHIVING')
			cur_time = datetime.datetime.now().strftime('%Y/%m/%d %I:%M:%S %p')
			self._set_status_note(row, '[{}] Archiving Started'.format(cur_time))

			ssh = get_ssh_connection(host, user)
			if ssh is None:
				continue

			if not ssh_dir_exists(ssh, basepath, 'Base Path not found: {}'.format(basepath)):
				continue

			# Create the archive directory if it doesn't exist
			archivedir = os.path.join(basepath, job, host, proj)
			if not ssh_dir_exists(ssh, archivedir, 'Archive Directory not found: {}'.format(archivedir)):
				if not ssh_create_dir(ssh, archivedir, 'Archive Directory Creation failed: {}'.format(archivedir)):
					continue

			# FORMAT the archive file if it doesn't exist
			archive_file = os.path.join(archivedir, proj)
			if not ssh_file_exists(ssh, archive_file, 'Archive File not found: {}'.format(archive_file)):
				format_cmd = Cmd.format_archive.format(file=archive_file)
				try:
					self.console.out('{}: {}'.format(host, format_cmd))
					stdin, stdout, stderr = ssh.exec_command(format_cmd, timeout=GB.timeout)
					out = stdout.read().decode('utf-8')
					self.console.out(out, color='green')
					err = stderr.read().decode('utf-8')
					self.console.err(err)
				except Exception as e:
					self.console.err('{}: ERROR FORMATTING: {}'.format(host, archive_file))
					traceback.print_exc()
					errormsg = traceback.format_exc()
					self.console.err(errormsg)
					self._set_status(row, 'ERROR')
					self._set_status_note(row, 'ERROR FORMATTING ARCHIVE')
					continue

			# ARCHIVE the project and workspace
			try:
				# For the archive command, use PTY(pseudo tty) to combine stdout and stderr and keep messages in order as they would in terminal.
				# https://stackoverflow.com/questions/3823862/paramiko-combine-stdout-and-stderr
				# todo: This needs to be a QThread, really bogs down the GUI.
				archive_cmd = Cmd.archive.format(file=archive_file, project=proj, workspace=workspace)
				self.console.out('{}: {}'.format(host, archive_cmd))
				file = ssh_command_out_file(ssh, archive_cmd)
				for line in file:
					# if line starts with 'Registered' or 'Connected' then ignore
					if line.startswith('Registered') or line.startswith('Connected') or line == '\n':
						continue
					self.console.out(line.strip(), color='green')
			except Exception as e:
				self.console.err('{}: ERROR ARCHIVING: {}'.format(host, archive_file))
				traceback.print_exc()
				errormsg = traceback.format_exc()
				self.console.err(errormsg)
				self._set_status(row, 'ERROR')
				self._set_status_note(row, 'ERROR FORMATTING ARCHIVE')
				continue
			ssh.close()
			self._banner('Archiving Complete')
			self.console.out(' ')
			self._set_status(row, 'DONE')
			cur_time = datetime.datetime.now().strftime('%Y/%m/%d %I:%M:%S %p')
			self._set_status_note(row, '[{}] Archiving Finished'.format(cur_time))
		self._buttons_enabled(True)


	@Slot()
	def on_actionCalculateSelectedSize_triggered(self):
		self._buttons_enabled(False)

		self._banner('Calculating Size...')
		# get selected rows self.tableWidget
		selected_rows = self.tableWidget.selectionModel().selectedRows()
		for row in selected_rows:
			self.tableWidget.setItem(row.row(), self.PROJ_SIZE, QTableWidgetItem('??????'))
			QCoreApplication.processEvents()

			host = self.tableWidget.item(row.row(), self.PROJ_HOST).text()
			proj = self.tableWidget.item(row.row(), self.PROJ_NAME).text()
			job = self._job_name_from_project(proj)
			workspace = self.tableWidget.item(row.row(), self.PROJ_WORKSPACE).text()
			enabled, user, dest = GB.host_dict[host]

			ssh = get_ssh_connection(host, user)
			if ssh is None:
				continue

			try:
				estimate_cmd = Cmd.estimate_archive.format(project=proj, workspace=workspace)
				self.console.out('{}: {}'.format(host, estimate_cmd))
				stdin, stdout, stderr = ssh.exec_command(estimate_cmd)
				out = stdout.read().decode('utf-8').strip()
				if out == '':
					out = '0 GB'
				self.console.out(out, color='green')
				# todo: need to format the size to be GB and also so it can be sorted.  Need to see if you sort by number
				# todo: here's the solution: https://stackoverflow.com/questions/12673598/python-numerical-sorting-in-qtablewidget
				self.tableWidget.setItem(row.row(), self.PROJ_SIZE, QTableWidgetItem(out))

			except Exception as e:
				self.console.err('{}: ERROR ESTIMATING: {}'.format(host, proj))
				traceback.print_exc()
				errormsg = traceback.format_exc()
				self.console.err(errormsg)
				continue
			ssh.close()
		self._banner('Size Estimate Complete')
		self.console.out(' ')
		self._buttons_enabled(True)

	@Slot()
	def on_actionLaunchFlame_triggered(self):
		rows = self.tableWidget.selectionModel().selectedRows()
		if len(rows) == 0:
			self.console.err("Can't launch Flame...No row selected.")
			return
		row = rows[0].row()
		self._banner('Launching Flame...')
		host = self.tableWidget.item(row, self.PROJ_HOST).text()
		project = self.tableWidget.item(row, self.PROJ_NAME).text()
		workspace = self.tableWidget.item(row, self.PROJ_WORKSPACE).text()
		self.console.out('{}: Project = {}, Workspace = {}'.format(host, project, workspace))

		cmd = Cmd.launch_flame.format(host=host, project=project, workspace=workspace)
		process = subprocess.Popen(cmd, shell=True)

	@Slot()
	def on_actionAddHost_triggered(self):

		# If there's a selection, copy into to dialog
		rows = self.tableWidgetHosts.selectionModel().selectedRows()
		if len(rows) != 0:
			GB.last_host = self.tableWidgetHosts.item(rows[0].row(), self.HOST_NAME).text()
			GB.last_user = self.tableWidgetHosts.item(rows[0].row(), self.HOST_USER).text()
			GB.last_basepath = self.tableWidgetHosts.item(rows[0].row(), self.HOST_BASEPATH).text()
			self.tableWidgetHosts.selectionModel().clearSelection()

		dialog = AddHostDialog(self, GB.last_host, GB.last_user, GB.last_basepath)
		dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
		dialog.show()
		dialog.exec_()
		if dialog.result() == QDialog.Accepted:
			# Get the data from the dialog
			host = dialog.lineEditHost.text()
			user = dialog.lineEditUser.text()
			basepath = dialog.lineEditBasePath.text()
			row = self.tableWidgetHosts.rowCount()
			self.tableWidgetHosts.insertRow(row)
			# Add the data to the table
			item = QTableWidgetItem()
			item.setCheckState(Qt.Checked)
			self.tableWidgetHosts.setItem(row, self.HOST_ENABLED, item)
			self.tableWidgetHosts.setItem(row, self.HOST_NAME, QTableWidgetItem(host))
			self.tableWidgetHosts.setItem(row, self.HOST_USER, QTableWidgetItem(user))
			self.tableWidgetHosts.setItem(row, self.HOST_BASEPATH, QTableWidgetItem(basepath))

			self.console.out('Added host {}'.format(host))
			self.console.out('User = {}, Basepath = {}'.format(user, basepath))
			# Loop until user cancels
			GB.last_host = host
			GB.last_user = user
			GB.last_basepath = basepath
			self.on_actionAddHost_triggered()

		# Save the host list to json config file
		self._save_hosts()

	@Slot()
	def on_actionDeleteHost_triggered(self):
		print('on_actionDeleteHost_triggered')
		selection = self.tableWidgetHosts.selectionModel().selectedRows()
		#delete the selected rows
		for index in sorted(selection, reverse=True):
			self.tableWidgetHosts.removeRow(index.row())

		# Save the host list to json config file
		self._save_hosts()

	@Slot()
	def tableWidgetHosts_itemDoubleClicked(self, item):
		row = item.row()
		host = self.tableWidgetHosts.item(row, self.HOST_NAME).text()
		user = self.tableWidgetHosts.item(row, self.HOST_USER).text()
		basepath = self.tableWidgetHosts.item(row, self.HOST_BASEPATH).text()
		dialog = AddHostDialog(self, host, user, basepath)
		dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
		dialog.labelTitle.setText('Edit Host')
		dialog.windowTitle = 'Edit Host'
		dialog.pushButtonAddHost.setText('Save')
		dialog.show()
		dialog.exec_()
		if dialog.result() == QDialog.Accepted:
			# Get the data from the dialog
			host = dialog.lineEditHost.text()
			user = dialog.lineEditUser.text()
			basepath = dialog.lineEditBasePath.text()
			# Add the data to the table
			self.tableWidgetHosts.item(row, self.HOST_NAME).setText(host)
			self.tableWidgetHosts.item(row, self.HOST_USER).setText(user)
			self.tableWidgetHosts.item(row, self.HOST_BASEPATH).setText(basepath)

	@Slot()
	def on_actionEnableHost_triggered(self):
		selection = self.tableWidgetHosts.selectionModel().selectedRows()
		for index in selection:
			self.tableWidgetHosts.item(index.row(), self.HOST_ENABLED).setCheckState(Qt.Checked)

	@Slot()
	def on_actionDisableHost_triggered(self):
		selection = self.tableWidgetHosts.selectionModel().selectedRows()
		for index in selection:
			self.tableWidgetHosts.item(index.row(), self.HOST_ENABLED).setCheckState(Qt.Unchecked)


	# PRIVATE METHODS

	def _set_status_note(self, row, text):
		self.tableWidget.setItem(row.row(), self.PROJ_COMMENT, QTableWidgetItem(text))

	def _save_hosts(self):
		with open(GB.hosts_file, 'w') as f:
			# get rows for host table
			rows = self.tableWidgetHosts.rowCount()
			for row in range(rows):
				enabled = self.tableWidgetHosts.item(row, self.HOST_ENABLED).checkState() == Qt.Checked
				host = self.tableWidgetHosts.item(row, self.HOST_NAME).text()
				user = self.tableWidgetHosts.item(row, self.HOST_USER).text()
				basepath = self.tableWidgetHosts.item(row, self.HOST_BASEPATH).text()
				GB.host_dict[host] = (enabled, user, basepath)
			json.dump(GB.host_dict, f)
		self.console.out('Saved hosts to {}'.format(GB.hosts_file))

	def _load_hosts(self):
		self.console.out('Loading hosts from {}'.format(GB.hosts_file))
		try:
			with open(GB.hosts_file, 'r') as f:
				GB.host_dict = json.load(f)
				# Add the data to the table
				for host in GB.host_dict:
					enabled, user, basepath = GB.host_dict[host]
					row = self.tableWidgetHosts.rowCount()
					self.tableWidgetHosts.insertRow(row)
					# Add the data to the table
					item = QTableWidgetItem()
					item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
					self.tableWidgetHosts.setItem(row, self.HOST_ENABLED, item)
					self.tableWidgetHosts.setItem(row, self.HOST_NAME, QTableWidgetItem(host))
					self.tableWidgetHosts.setItem(row, self.HOST_USER, QTableWidgetItem(user))
					self.tableWidgetHosts.setItem(row, self.HOST_BASEPATH, QTableWidgetItem(basepath))

				# for (enabled, host, user, basepath) in GB.hosts_file:
				# 	row = self.tableWidgetHosts.rowCount()
				# 	self.tableWidgetHosts.insertRow(row)
				# 	item = QTableWidgetItem()
				# 	item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
				# 	self.tableWidgetHosts.setItem(row, self.HOST_ENABLED, item)
				# 	self.tableWidgetHosts.setItem(row, self.HOST_NAME, QTableWidgetItem(host))
				# 	self.tableWidgetHosts.setItem(row, self.HOST_USER, QTableWidgetItem(user))
				# 	self.tableWidgetHosts.setItem(row, self.HOST_BASEPATH, QTableWidgetItem(basepath))


		except Exception as e:
			GB.console.err('Error reading hosts config.')
			return

	def _set_status(self, row, state):
		self.tableWidget.setItem(row.row(), self.PROJ_STATUS, QTableWidgetItem(state))

	def _job_name_from_project(self, project):
		return project.split('_')[0]

	def _banner(self, text):
		length = len(text)
		toplen = length + 8
		self.console.out('*' * toplen)
		self.console.out('* {}'.format(text))
		self.console.out('*' * toplen)

	def _disable_buttons(self):
		self.pushButtonFlame.setEnabled(False)
		self.pushButtonList.setEnabled(False)
		self.pushButtonArchive.setEnabled(False)
		self.pushButtonCalcSize.setEnabled(False)

	def _buttons_enabled(self, state):
		self.pushButtonFlame.setEnabled(state)
		self.pushButtonList.setEnabled(state)
		self.pushButtonArchive.setEnabled(state)
		self.pushButtonCalcSize.setEnabled(state)
