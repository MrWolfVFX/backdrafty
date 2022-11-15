import os

class Globals(object):
	"""
		Global variables for the backdrafty application.
	"""
	app = None          # type: QApplication
	appname = 'backdrafty'
	appdir = os.path.dirname(os.path.realpath(__file__))
	hostname = os.uname()[1]
	sshdir = os.path.join(appdir, '.ssh')
	rsa_key_file = os.path.join(sshdir, '{appname}_{hostname}'.format(appname=appname, hostname=hostname))
	rsa_key_pub_file = rsa_key_file + '.pub'
	configdir = os.path.join(appdir, '.config')
	hosts_file = os.path.join(configdir, 'hosts.json')
	prefs_file = os.path.join(configdir, 'prefs.json')
	console = None      # type: yoonico.ui.console_widget
	timeout = 4.0
	last_host = ''
	last_user = ''
	last_basepath = ''
	host_dict = dict()

class Cmd(object):
	"""
		CLI Command templates.
	"""
	# todo: For the IO bin, change path to point to right Flame Version for the Flame project.
	# io_bin_path = '/opt/Autodesk/io/2021.1/bin/'
	io_bin_path = '/opt/Autodesk/io/bin/'
	list_project_db = 'cat /opt/Autodesk/project/project.db'
	list_workspaces = 'ls /opt/Autodesk/clip/{partition}/{project}.prj/ | grep .wksp'
	estimate_archive = io_bin_path + 'flame_archive --estimate --project {project} --entry "/{workspace}" --linked --omit sources,renders | grep -e MB -e GB'
	format_archive = io_bin_path + 'flame_archive --format --file "{file}"'
	archive = io_bin_path + 'flame_archive -v --archive --file "{file}" --project {project} --entry "/{workspace}" --linked --omit sources,renders'
	dir_exists = 'if [ -d {0} ]; then echo 1; else echo 0; fi'
	file_exists = 'if [ -f {0} ]; then echo 1; else echo 0; fi'
	create_dir = 'mkdir -p "{0}" && echo 1'
	launch_flame = '/opt/Autodesk/flame_2021.1/bin/startApplication -H {host} -J {project} -W "{workspace}" &'
	ssh_keygen = 'rm -f "{sshdir}/{appname}_{hostname}" && ssh-keygen -t rsa -f "{sshdir}/{appname}_{hostname}" -N ""'
	ssh_copy_id = 'chmod 600 "{pubfile}" && ssh-copy-id -f -i "{pubfile}" {user}@{host}'
