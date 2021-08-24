import unittest
import os

from splunk.conf_util import ConfigMap, ConfigMapError

# NOTE: Must be run as `python -m python-site.splunk.conf_util.test_conf_util`

class TestConfigMap(unittest.TestCase):

	def setUp(self):
		self.test_path = 'foo.conf'
		with open(self.test_path, 'a') as conf_w:
			conf_w.write("[info]\n")
			conf_w.write("time = 77\n")
			conf_w.write("count = 800\n")
			conf_w.write("mes = hello\n")


	def test_conf_reading(self):
		mapper = ConfigMap(self.test_path)
		self.assertTrue('info' in mapper)
		self.assertTrue('time' in mapper['info'])

	def test_conf_validate(self):
		mapper = ConfigMap(self.test_path)
		self.assertTrue(mapper.validate({'info':['mes', 'count', 'time']}))

	def tearDown(self):
		os.remove(self.test_path)


if __name__ == '__main__':
	unittest.main()
