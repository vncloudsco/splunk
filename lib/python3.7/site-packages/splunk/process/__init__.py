from builtins import object
import subprocess
import struct
import os
import errno
import signal
import time


"""
The following package contains utilities to track and restart child processes in Python
"""


def get_splunk_py_path():
	return os.path.join(os.environ.get('SPKUNK_HOME', '/opt/splunk'), 'bin', 'python')

def process_exists(pid):
	# Checks if process id exists by sending a 0 signal to it.
	try:
		os.kill(pid, 0)
	except OSError as e:
		return e.errno == errno.EPERM
	else:
		return True

class ProcessIDTracker(object):
	"""
	This class is used to save a process id and time it was last checked
	It packs itself as a binary sequence of <TIME, PID>
	Where both TIME and PID are signed 32-bit integers
	"""

	@staticmethod
	def from_path(path):
		with open(path, 'rb') as proc_file:
			bin_data = struct.unpack('ii', proc_file.read())
			return ProcessIDTracker(path, bin_data[1], bin_data[0])

	@staticmethod
	def is_on(path):
		if not os.path.isfile(path):
			return False
		track = ProcessIDTracker.from_path(path)
		if track.is_running():
			return True
		else:
			return False


	@staticmethod
	def update_time(path):
		# Convenience method for updating the time stamp on file, works like heart beat
		track = ProcessIDTracker.from_path(path)
		track.save()

	def __init__(self, path, pid, time_val=int(time.time())):
		self.path = path
		self.pid = pid
		self.time_val = time_val

	def __repr__(self):
		return "(path={p}, pid={id}, time={t})".format(p=self.path, id=self.pid, t=self.time_val)

	def __len__(self):
		return len(self.binary())

	def tuple(self):
		return (self.time_val, self.pid)

	def last_time(self):
		return self.time_val

	def time_since_last_update(self):
		return int(time.time()) - self.time_val

	def binary(self):
		# Uses new time stamp for updating the last time checked.
		return struct.pack('ii', int(time.time()), self.pid)

	def is_running(self):
		return process_exists(self.pid)

	def save(self):
		with open(self.path, 'wb') as proc_file:
			proc_file.write(self.binary())


class BackgroundPythonProcess(object):
	"""
	Util class for running python process in the background
	Also formats splunk's python exec path, as option
	"""

	def __init__(self, python_file, python_exec_path, *cmd_args):
		self.python_exec_path = python_exec_path
		self.python_file = python_file
		self.proc_args = [self.python_exec_path, self.python_file] + list(cmd_args) + ['&']
		self.child_process = None
		self.pid = None
		self.track_path = None

	def __repr__(self):
		return ', '.join('%s="%s"' % (k, v) for k, v in self.__dict__.items())

	def start(self, track_path):
		"""
		Creates and starts the process, and saves the pid to a tracking file.
		"""
		if self.is_started():
			return
		self.track_path = track_path
		FNULL = open(os.devnull, 'wb')
		self.child_process = subprocess.Popen(self.proc_args, stdout=FNULL, stderr=FNULL)
		self.pid = self.child_process.pid
		with open(track_path, 'wb') as proc_file:
			tracking = ProcessIDTracker(self.track_path, self.pid)
			proc_file.write(tracking.binary())

	def is_started(self):
		return self.child_process is not None

	def stop(self):
		# Cannot stop non-existant process.
		if self.child_process is None:
			return
		self.child_process.kill()
		self.child_process.terminate()
		self.child_process = None
