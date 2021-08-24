import os
import json
import configparser

"""
This module provides a util to read config files into nested dictionaries
Allows prevention of repetitive code of reading the same way from different files.
"""

class ConfigMapError(Exception): pass

class ConfigMap(dict):
	"""
	A util dictionary subclass that represents the mappings of
	sections to items in a config file.
	"""

	def __init__(self, path):
		parser = configparser.RawConfigParser(delimiters=('='), strict=False)
		if not os.path.isfile(path):
			raise ConfigMapError("File at {p} does not exist.".format(p=path))
		parser.read(path)
		for sect in parser.sections():
			self[sect] = {}
			for pair in parser.items(sect):
				self[sect][pair[0]] = pair[1]


	def validate(self, schema):
		for section in schema:
			if section not in self:
				raise ConfigMapError("Config file does not contain section '{sec}' ".format(sec=section))
			for option in schema[section]:
				if option not in self[section]:
					raise ConfigMapError("Config file does not contain option '{opt}' in section '{sec}' ".format(opt=option, sec=section))
		return True
