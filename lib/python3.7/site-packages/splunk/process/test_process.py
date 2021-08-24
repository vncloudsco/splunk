import os
import struct
import time
import unittest

from splunk.process import process_exists, ProcessIDTracker, BackgroundPythonProcess

# NOTE: Must be run as `python -m python-site.splunk.process.test`


class TestProcessExists(unittest.TestCase):
	
	def test_imaginary_process(self):
		self.assertFalse(process_exists(58923849))

class TestProcessTrack(unittest.TestCase):

	def setUp(self):
		self.path = 'foo.archive'
		self.pid = 72406
		self.time_val = int(time.time())
		with open(self.path, 'wb') as proc_file:
			proc_file.write(struct.pack('ii', self.time_val, self.pid))

	def test_load_track(self):
		tracker = ProcessIDTracker.from_path(self.path)
		self.assertEqual(tracker.pid, self.pid)
		self.assertEqual(tracker.time_val, self.time_val)

	def tearDown(self):
		os.remove(self.path)


class TestProcessCall(unittest.TestCase):

	def setUp(self):
		# Creates sample python file to put in process
		self.py_file = 'splunk_proc_test.py'
		with open(self.py_file, 'a') as py_writer:
			py_writer.write("import time \n")
			py_writer.write("time.sleep(50)")
		self.track_file = 'foo.archive'
		self.proc_child = BackgroundPythonProcess(self.py_file, 'python')
		self.proc_child.start(self.track_file)
		self.pid = self.proc_child.pid

	def test_start(self):
		self.assertTrue(self.proc_child.is_started())

	def test_save_proc(self):
		tracker = ProcessIDTracker.from_path(self.track_file)
		self.assertEqual(tracker.pid, self.pid)

	def test_update_time(self):
		tracker = ProcessIDTracker.from_path(self.track_file)
		timer = tracker.time_val
		tracker.save()
		# time stamp in seconds, need to wait
		time.sleep(1)
		ProcessIDTracker.update_time(self.track_file)
		tracker = ProcessIDTracker.from_path(self.track_file)
		self.assertNotEqual(timer, tracker.time_val)

	def test_is_running(self):
		self.assertTrue(ProcessIDTracker.is_on(self.track_file))

	def tearDown(self):
		os.remove(self.py_file)
		self.proc_child.stop()
		os.remove(self.track_file)



if __name__ == '__main__':
	unittest.main()