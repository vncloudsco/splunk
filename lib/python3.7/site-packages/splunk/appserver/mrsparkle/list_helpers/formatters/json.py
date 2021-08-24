from __future__ import absolute_import
import json
from splunk.appserver.mrsparkle.list_helpers.formatters import BaseFormatter

class JsonFormatter(BaseFormatter):

    formats = 'json'

    def format(self):
        try:
            return json.dumps(self.response)
        except Exception as e:
            return json.dumps({'error': e.args[0]})
