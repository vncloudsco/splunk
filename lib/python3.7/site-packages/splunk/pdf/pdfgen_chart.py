from __future__ import absolute_import
from __future__ import print_function
from builtins import object

import sys
import logging

import time
import subprocess
import json
import os

import splunk.pdf.pdfgen_utils as pu
import splunk.util

logger = pu.getLogger()

class SvgBasedViz(object):
    _data = None
    _fields = None
    _props = None
    _width = None
    _height = None
    _svg = None
    _jsDirectory = None
    _pdfJsDirectory = None
    _genSvgScriptName = None
    _runningAsScript = False

    EXPOSED_JS_DIRECTORY = "share/splunk/search_mrsparkle/exposed/js"
    PDF_JS_DIRECTORY = "share/splunk/pdf"

    class ScriptNameUnspecified(Exception):
        def __str__(self):
            return "Must specify an SVG generation script name to SvgBasedViz constructor"

    def __init__(self, data, fields, props, width=None, height=None, genSvgScriptName=None, runningAsScript=False,
                 locale='en_US', server_zoneinfo=None):
        self._runningAsScript = runningAsScript
        self._data = data
        self._fields = fields
        self._props = props
        self._width = width
        self._height = height
        self._genSvgScriptName = genSvgScriptName

        self._jsDirectory = pu.getSplunkDirectory(self.EXPOSED_JS_DIRECTORY)
        self._pdfJsDirectory = pu.getSplunkDirectory(self.PDF_JS_DIRECTORY)
        self._locale = locale
        self._server_zoneinfo = server_zoneinfo
        if self._genSvgScriptName == None:
            raise SvgBasedViz.ScriptNameUnspecified()

    def _buildArgs(self):
        args = {}
        args['locale'] = self._locale
        args['SERVER_ZONEINFO'] = self._server_zoneinfo
        args['system'] = {'splunkdUri':splunk.getLocalServerInfo()}
        args['props'] = self._props
        args['series'] = {}
        args['series']['fields'] = self._fields
        args['series']['columns'] = self._data
        if self._width != None:
            args['width'] = self._width
        if self._height != None:
            args['height'] = self._height
        return json.dumps(args)

    def build(self):
        genSvgPath = os.path.join(self._pdfJsDirectory, self._genSvgScriptName)
        if 'NODE_PATH' not in os.environ:
            os.environ['NODE_PATH'] = os.path.join(os.environ['SPLUNK_HOME'], 'lib', 'node_modules')

        process = subprocess.Popen(['node', genSvgPath], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr = subprocess.PIPE)
        argsJSON = self._buildArgs()
        logger.debug("argsJSON: %s" % argsJSON)

        if (argsJSON is not None) and sys.version_info >= (3, 0): argsJSON = argsJSON.encode()
        out, err = process.communicate(input=argsJSON)
        if sys.version_info >= (3, 0):
            out = out.decode()
            err = err.decode()

        self._svg = out
        if len(err) > 0:
            self._log("svg viz error logging: " + err, logLevel='warning')
        if len(out) == 0:
            self._log("no svg viz output", logLevel='error')
        return len(out) > 0

    def getSvg(self):
        return self._svg

    def _log(self, msg, logLevel='debug'):
        if self._runningAsScript:
            print(logLevel + " : " + msg)
            return

        if logLevel=='debug':
            logger.debug(msg)
        elif logLevel=='info':
            logger.info(msg)
        elif logLevel=='warning':
            logger.warning(msg)
        elif logLevel=='error':
            logger.error(msg)

class Chart(SvgBasedViz):
    def __init__(self, data, fields, props, locale, runningAsScript=False, server_zoneinfo=None):
        SvgBasedViz.__init__(self, data, fields, props, width=600, height=350, genSvgScriptName="gensvg.js",
                             runningAsScript=runningAsScript, locale=locale, server_zoneinfo=server_zoneinfo)

class Map(SvgBasedViz):
    def __init__(self, data, fields, props, locale, runningAsScript=False, server_zoneinfo=None):
        SvgBasedViz.__init__(self, data, fields, props, width=600, height=350, genSvgScriptName="genmapsvg.js",
                             runningAsScript=runningAsScript, locale=locale, server_zoneinfo=server_zoneinfo)

class Single(SvgBasedViz):
    def __init__(self, data, fields, props, locale, runningAsScript=False, server_zoneinfo=None):
        SvgBasedViz.__init__(self, data, fields, props, width=600, height=100, genSvgScriptName="gensinglevalue.js",
                             runningAsScript=runningAsScript, locale=locale, server_zoneinfo=server_zoneinfo)

if __name__=="__main__":
    mode = "chart"
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    print("test mode = %s" % mode)

    if mode == "chart":
        data = [[1, 2, 3, 4, 5], [-5, -4, -3, -2, -1]]
        props = {"chart": "line"}
        fields = ["one", "two"]

        chart = Chart(data, fields, props, runningAsScript=True)
        chart.build()
        print(chart.getSvg())
    elif mode == "map":
        data = [[10, 20, 30], [-10, -20, -30], [1, 2, 3]]
        fields = ["latitude", "longitude", "size"]
        props = {"tileURL": "http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"}

        map = Map(data, fields, props, runningAsScript=True)
        map.build()
        print(map.getSvg())
