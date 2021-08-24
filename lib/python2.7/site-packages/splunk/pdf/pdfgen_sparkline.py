from __future__ import absolute_import
from __future__ import division
from past.utils import old_div
from builtins import range
from builtins import map
from builtins import object

__author__ = 'michael'

import sys

from reportlab.platypus import Flowable
from reportlab.lib.units import inch
from reportlab.lib import colors

import splunk.pdf.pdfgen_utils as pu

logger = pu.getLogger()

# factory that create Sparkline Flowable with given data and options.
# We only support 3 types of sparkline ['bar','line',''discrete] with limited options
def createSparkLine(data, options):
    type = options.get('type')
    targetclass = 'Empty'
    # fallback to display Line if it's not supported
    if type in [None, 'tristate', 'bullet', 'pie', 'box']:
        targetclass = 'Line'
    elif type in ['bar', 'line', 'discrete']:
        # SPL-96578, render a empty cell for illegal type
        targetclass = type.capitalize()
    logger.debug('create sparkline, data %s options %s' % (data, options))
    return globals()[targetclass](data, options)


# represent a sparkline color range
class Color(object):
    def __init__(self, range, colorString, defaultColor='black'):
        self._min = -sys.maxsize - 1
        self._max = sys.maxsize
        self._color = colors.toColor(defaultColor)
        colorRange = range.split(':')
        try:
            if len(colorRange) == 1:
                self._min = self._max = int(colorRange[0])
            elif len(colorRange) == 2:
                if colorRange[0]:
                    self._min = int(colorRange[0])
                if colorRange[1]:
                    self._max = int(colorRange[1])

            self._color = colors.toColor(colorString)
        except ValueError as e:
            logger.warning(
                "Sparkline::Color.__init__> toColor for %s raised %s fallback to use default color(black)" % (
                    colorString, e))

        logger.debug("Sparkline::Color.__init__> Register Color Range %s to %s color %s " % (
            str(self._min), str(self._max), colorString))

    def match(self, value):
        return self._min <= value <= self._max

    def getColor(self):
        return self._color

SPARK_LINE_HEIGHT = 0.2 * inch
# Base class of sparkline flowable
# subclass needs to override _doDraw function
class Base(Flowable):
    _options = {}
    _data = []
    _min = 0
    _max = 0
    _range = 0
    _dataCnt = 0
    _marginWidth = 0.1 * inch
    width = 0

    def __init__(self, data, options):
        self._parseData(data, options)

    def _parseData(self, data, options):
        """ strips out the ##__SPARKLINE__## item and calculates the bounds of the remaining data """
        splitData = [x if x!='' else '0' for x in data.split(',')]
        self._data = list(map(float, splitData[1:]))
        self._min = min(self._data)
        self._max = max(self._data)
        self._range = self._max - self._min
        self._dataCnt = len(self._data)
        self.width = max([min([float(self._dataCnt) / 50.0 * inch, 2.0 * inch]), inch])
        self.height = SPARK_LINE_HEIGHT
        self._options = options

        if self._dataCnt < 2:
            logger.warning("Sparkline::_parseData> dataCnt: " + str(self._dataCnt) + " for sparkline data: " + data)

    def wrap(self, availWidth, availHeight):
        """ force height to 0.2 inches TODO: calculate a better height
            set width to show 50 data points per inch, min 1 inch, max 2 inches """
        if self.width > availWidth:
            self.width = availWidth
        if self.height > availHeight:
            self.height = availHeight

        return self.width, self.height

    def draw(self):
        if self._dataCnt < 2:
            return

        totalWidth = self.width - 2.0 * self._marginWidth
        totalHeight = self.height
        self._doDraw(totalWidth, totalHeight)

    def _doDraw(self, width, height):
        """should be override by sub class"""

    def isNumeric(self):
        return False

# Line chart
# This Flowable subclass will draw a simple sparkline for the given data
# The only support options are [lineColor,fillColor]
class Line(Base):
    _DEFAULT_COLOR = "#5cc05c"

    def __init__(self, data, options):
        Base.__init__(self, data, options)
        self._lineColor = colors.toColor(self._options.get('lineColor', self._DEFAULT_COLOR))
        self._fillColor = colors.toColor(self._options['fillColor']) if 'fillColor' in self._options else None

    def _doDraw(self, width, height):
        deltaWidth = old_div(width, (self._dataCnt - 1))
        # in order to support fillColor, we need to draw a line along with a path with fill=1
        self.canv.setStrokeColor(self._lineColor)
        p = self.canv.beginPath()
        for i in range(self._dataCnt):
            if self._range > 0.0:
                y = old_div((self._data[i] - self._min), self._range) * height
            else:
                y = old_div(height, 2)

            x = i * deltaWidth + self._marginWidth
            if i == 0:
                p.moveTo(x, 0)
                p.lineTo(x, y)
                lastx = x
                lasty = y
                pass

            p.lineTo(x, y)
            self.canv.line(lastx, lasty, x, y)
            lastx = x
            lasty = y

        # finish the path
        p.lineTo(width + self._marginWidth, 0)
        if self._fillColor:
            self.canv.setFillColor(self._fillColor)
            self.canv.drawPath(p, stroke=0, fill=1)


# Bar chart, the only support options are [colorMap,barColor]
class Bar(Base):
    _barSpacing = 0.4
    _DEFAULT_COLOR = colors.toColor("#006d9c")
    _MAX_BAR_WIDTH = 3

    def __init__(self, data, options):
        Base.__init__(self, data, options)
        self._colorMap = []
        self._barColor = self._DEFAULT_COLOR
        self._buildColorMap()

    def _doDraw(self, width, height):
        deltaWidth = min(old_div(width, (self._dataCnt - 1)), self._MAX_BAR_WIDTH)
        for i in range(self._dataCnt):
            if self._range > 0.0:
                y = old_div((self._data[i] - self._min), self._range) * height
            else:
                y = old_div(height, 2)

            # fix SPL-96728, y can no less than 0.4
            y = max(y, 0.4)
            x = i * deltaWidth + self._marginWidth
            self.canv.setFillColor(self._findColor(self._data[i]))
            self.canv.rect(x + self._barSpacing, 1, deltaWidth - self._barSpacing * 2, y, stroke=0, fill=1)

    def _buildColorMap(self):
        if 'colorMap' in self._options and not isinstance(self._options['colorMap'], str):
            for k, v in list(self._options['colorMap'].items()):
                self._colorMap.append(Color(k, v))
        if 'barColor' in self._options:
            self._barColor = colors.toColor(self._options['barColor'])
            logger.debug("Sparkline::Bar._buildColorMap> set bar color to %s" % self._options['barColor'])

    def _findColor(self, value):
        for colorRange in self._colorMap:
            if colorRange.match(value):
                self._barColor = colorRange.getColor()
                logger.debug("Sparkline::Bar._findColor> find color %r for value %s" % (self._barColor, value))
                break
        return self._barColor


# Discrete chart, the only support options are [lineColor]
class Discrete(Base):
    _LINE_HEIGHT = 2.5
    _LINE_WIDTH = 0.6
    _MAX_WIDTH = 3
    _DEFAULT_COLOR = colors.toColor("#5cc05c")

    def __init__(self, data, options):
        Base.__init__(self, data, options)
        if 'lineColor' in self._options:
            self._lineColor = colors.toColor(self._options['lineColor'])
        else:
            self._lineColor = self._DEFAULT_COLOR

    def _doDraw(self, width, height):
        deltaWidth = min(old_div(width, (self._dataCnt - 1)), self._MAX_WIDTH)
        for i in range(self._dataCnt):
            if self._range > 0.0:
                y = old_div((self._data[i] - self._min), self._range) * height
            else:
                y = old_div(height, 2)
            x = i * deltaWidth + self._marginWidth
            self.canv.setLineWidth(self._LINE_WIDTH)
            self.canv.setStrokeColor(self._lineColor)
            self.canv.line(x, y - old_div(self._LINE_HEIGHT, 2), x, y + old_div(self._LINE_HEIGHT, 2))


# Empty flowable for illegal sparkline type
class Empty(Base):
    def __init__(self, data, options):
        Base.__init__(self, data, options)

    def _doDraw(self, width, height):
        return
