import traceback
import subprocess
import paramiko
import os
from bd_globals import Globals as GB, Cmd


def get_ssh_connection(host, user, pw='', port=22, timeout=GB.timeout):
	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.load_system_host_keys()
		# ssh.connect(host, port, user, password, timeout=self.TIMEOUT)
		if pw != '':
			ssh.connect(host, port, user, password=pw, timeout=timeout)
		else:
			# paramiko private key example from: https://www.youtube.com/watch?v=vVWF75gcDTE
			key_file = paramiko.RSAKey.from_private_key_file(GB.rsa_key_file)
			ssh.connect(host, port, user, pkey=key_file, allow_agent=False, look_for_keys=False, timeout=timeout)
		return ssh
	except Exception as e:
		traceback.print_exc()
		errormsg = traceback.format_exc()
		GB.console.err('{}: CANNOT CONNECT!'.format(host))
		GB.console.err(errormsg)
		return None


def shell_cmd(cmd, input=''):
	proc = subprocess.Popen(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = proc.communicate(input=input)
	result = proc.returncode
	GB.console.out(out)
	GB.console.err(err)
	return out, err, result


def ssh_command_out_file(ssh, command):
	tran = ssh.get_transport()
	chan = tran.open_session()
	chan.get_pty()
	file = chan.makefile()
	chan.exec_command(command)
	return file


def deploy_key(ssh, pubkeyfile, host, user, pw):
	"""
		Deploy the public rsa public key to the remote host
		Emulates 'ssh-copy-id' linux command.
			From: https://stackoverflow.com/questions/170147/how-to-copy-a-file-to-a-remote-server-using-ssh-in-python
	:return: True if successful, False otherwise
	:rtype: Boolean
	"""
	try:
		key = open(pubkeyfile, 'r').read()
		if ssh is None:
			return False
		ssh.exec_command('mkdir -p ~/.ssh/')
		ssh.exec_command('echo "{}" >> ~/.ssh/authorized_keys'.format(key))
		ssh.exec_command('chmod 644 ~/.ssh/authorized_keys')
		ssh.exec_command('chmod 700 ~/.ssh/')
		return True
	except Exception as e:
		traceback.print_exc()
		errormsg = traceback.format_exc()
		GB.console.err('{}: CANNOT DEPLOY KEY!'.format(host))
		GB.console.err(errormsg)
		return False


def ssh_file_exists(ssh, path, error_msg='Remote archive file does not exist!'):
	try:
		cmd = Cmd.file_exists.format(path)
		stdin, stdout, stderr = ssh.exec_command(cmd)
		out = stdout.read().decode('utf-8').strip()
		if out == '1':
			return True
		else:
			GB.console.err(error_msg)
			return False
	except Exception as e:
		traceback.print_exc()
		tracestr = traceback.format_exc()
		GB.console.err(error_msg)
		GB.console.err(tracestr)
		return False


def ssh_dir_exists(ssh, path, error_msg='Remote archive folder does not exist!'):
	try:
		cmd = Cmd.dir_exists.format(path)
		stdin, stdout, stderr = ssh.exec_command(cmd)
		out = stdout.read().decode('utf-8').strip()
		if out == '1':
			return True
		else:
			GB.console.err(error_msg)
			return False
	except Exception as e:
		traceback.print_exc()
		tracestr = traceback.format_exc()
		GB.console.err(error_msg)
		GB.console.err(tracestr)
		return False


def ssh_create_dir(ssh, path, error_msg='Remote archive folder does not exist!'):
	try:
		# create the directory first
		cmd = Cmd.create_dir.format(path)
		stdin, stdout, stderr = ssh.exec_command(cmd)
		out = stdout.read().decode('utf-8').strip()
		# then check if it exists
		cmd = Cmd.dir_exists.format(path)
		stdin, stdout, stderr = ssh.exec_command(cmd)
		out = stdout.read().decode('utf-8').strip()
		if out == '1':
			return True
		else:
			GB.console.err(error_msg)
			return False
	except Exception as e:
		traceback.print_exc()
		tracestr = traceback.format_exc()
		GB.console.err(error_msg)
		GB.console.err(tracestr)
		return False
