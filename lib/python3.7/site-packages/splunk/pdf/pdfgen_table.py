from __future__ import absolute_import
from __future__ import division
from builtins import object
from past.utils import old_div
__author__ = 'michael'

import math
import re
import xml.sax.saxutils as su

from splunk.util import toUnicode
from splunk.util import format_local_tzoffset
from reportlab.platypus import Flowable, Table, PageBreak, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import IdentStr
from reportlab.lib import colors, pagesizes
from reportlab.lib.enums import TA_LEFT

import splunk
import splunk.pdf.pdfgen_sparkline as ps
import splunk.pdf.pdfgen_utils as pu

logger = pu.getLogger()

_PERF_TEST = False
if _PERF_TEST:
    import time

TABLE_FONT_SIZE = 6

wrapTimes = []
stringWidthTimes = []
drawTimes = []

wrapCacheHits = []
wrapCacheMisses = []

# row number column used empty string '' as header
NOT_NUMBER_COLUMNS = ['', '_time', '_raw', 'earliest_time', 'latest_time']

TIME_COLUMNS = ["_time", "earliest_time", "latest_time"]

OVERLAY_HEATMAP = "heatmap"
OVERLAY_HIGHLOW = "highlow"


def createDataOverlay(mode, columnNames):
    if mode == OVERLAY_HEATMAP:
        return HeatMap(columnNames)
    elif mode == OVERLAY_HIGHLOW:
        return HighLow(columnNames)
    else:
        return None


# Base class of Table DataOverlay
# The algorithm is ported from ResultsTableMaster.js and NumberCellRenderer.js
class BaseOverlay(object):
    def __init__(self, columnNames=None):
        if columnNames is None:
            columnNames = []
        self.columnNames = columnNames
        # key:columnName, value:the count of NotNullCell
        self._notNullCellCount = dict()
        # key:columnName, value:list of tuple (rowId,columnId,value),
        # Please be aware that value will be convert into None for non number value
        self._numberCells = dict()

    def addValue(self, columnId, rowId, value):
        if len(self.columnNames) < columnId:
            return
        columnName = self.columnNames[columnId]
        if columnName not in NOT_NUMBER_COLUMNS:
            if columnName not in self._notNullCellCount:
                self._notNullCellCount[columnName] = 0
            if columnName not in self._numberCells:
                self._numberCells[columnName] = []
            if value:
                self._notNullCellCount[columnName] += 1

            # the value appended into this array will be None for not-number value
            self._numberCells[columnName].append((rowId, columnId, strictParseFloat(value)))

    # ready() should be call after all the values been added
    def ready(self):
        for columnName in self.columnNames:
            if columnName not in NOT_NUMBER_COLUMNS:
                numberCount = 0
                for (row, column, v) in self._numberCells[columnName]:
                    # the value will be None for not-number value
                    if v is not None:
                        numberCount += 1
                if numberCount < old_div(self._notNullCellCount[columnName], 2):
                    # remove column that not treated as number
                    logger.debug(
                        "BaseOverlay: removed column %s from Overlay Registry as it's not number column" % columnName)
                    del self._numberCells[columnName]

    # Return tuple (rowId, columnId, Color) iterator
    # Indicate that table should render cell (rowId,ColumnId) with (Color) as background color
    def getNumberCellsWithColor(self):
        return self._iter(list(self._numberCells.values()))

    def _getAllNumberValues(self):
        values = []
        for l in list(self._numberCells.values()):
            for (rowId, columnId, value) in l:
                if value is not None:
                    values.append(value)
        return values

    def _iter(self, values):
        for list in values:
            for (rowId, columnId, value) in list:
                if value:
                    logger.debug("BaseOverlay: render cell (%s, %s) with value %s" % (rowId, columnId, value))
                    yield rowId, columnId, self.getColor(value)

    def getColor(self, value):
        """should be override by sub class"""


class HeatMap(BaseOverlay):

    def __init__(self, columnNames=None):
        BaseOverlay.__init__(self, columnNames)
        self.heatRange = 0
        self.heatOffset = 0

    def ready(self):
        BaseOverlay.ready(self)
        numbers = sorted(self._getAllNumberValues())
        # be aware that there will be None values in the array
        lower, upper = self._getPercentiles(numbers, .05, .95)
        self.heatRange = upper - lower
        self.heatOffset = lower
        logger.debug('HeatMap: heatmap ready, heatRange %s heatOffset %s' % (self.heatRange, self.heatOffset))

    def _getPercentiles(self, orderedList, lowerPercentile, upperPercentile):
        '''
        This is an approximation method for obtaining a pair of lower and upper percentile values from a list
        '''

        if len(orderedList) == 0: return (0, 0)

        def f(p, ln):
            n = p * (ln - 1) + 1
            d, k = math.modf(n)
            return int(n), int(k), d

        def v(percentile, oList):
            n, k, d = f(percentile, len(oList))
            if k == 0 or len(oList) == 1:
                return oList[0] or 0
            elif k == len(oList) - 1:
                return oList[-1] or 0
            else:
                tempk = oList[k] or 0
                tempk1 = oList[k + 1] or 0
                return tempk + d * (tempk1 - tempk)

        return (v(lowerPercentile, orderedList), v(upperPercentile, orderedList))

    def getColor(self, value):
        heatValue = 0 if self.heatRange == 0 else min(
            max(math.ceil(((value - self.heatOffset) / self.heatRange) * 1000) / 1000, 0), 1)
        # color #dc4e41 with a alpha channel
        color = colors.Color(216 / 255.0, 93 / 255.0, 60 / 255.0, alpha=heatValue)
        logger.debug('HeatMap: generate heatValue %s for cellValue %s' % (heatValue, value))
        return color


class HighLow(BaseOverlay):

    MAX_COLOR = colors.toColor("#dc4e41")
    MIN_COLOR = colors.toColor("#6ab7c7")

    def __init__(self, columnNames=[]):
        BaseOverlay.__init__(self, columnNames)
        self.max = None
        self.min = None

    def ready(self):
        BaseOverlay.ready(self)
        # find min and max value
        numbers = self._getAllNumberValues()
        for value in numbers:
            if value is not None:
                if self.min is None and self.max is None:
                    self.min = self.max = value
                    continue

                self.min = min(self.min, value)
                self.max = max(self.max, value)

        logger.debug("HighLow: highlow ready, min %s, max %s" % (self.min, self.max))

    def _iter(self, values):
        for list in values:
            for (rowId, columnId, value) in list:
                if value is not None:
                    if value == self.min:
                        logger.debug("HighLow: render cell (%s, %s) with min value %s" % (rowId, columnId, value))
                        yield rowId, columnId, self.MIN_COLOR
                    elif value == self.max:
                        logger.debug("HighLow: render cell (%s, %s) with max value %s" % (rowId, columnId, value))
                        yield rowId, columnId, self.MAX_COLOR


TIME_RAW_FORMAT = '%Y-%m-%dT%H:%M:%S.%f' + format_local_tzoffset()
TIMESTAMP_FORMAT_MILLISECOND = "%Y-%m-%d %H:%M:%S.{msec}"
TIMESTAMP_FORMAT_SECOND = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_FORMAT_MINUTE = "%Y-%m-%d %H:%M:00"
TIMESTAMP_FORMAT_HOUR = "%Y-%m-%d %H:00"
TIMESTAMP_FORMAT_DAY = "%Y-%m-%d"
TIMESTAMP_FORMAT_MONTH = "%Y-%m"
TIMESTAMP_FORMAT_YEAR = "%Y"


class TableData(object):
    """
    This class is designed to hold all the table data and perform necessary transformation
    """

    def __init__(self, columnNames=None, data=None):
        self.columnNames = columnNames
        self.data = data or []

    def getData(self):
        return self.data

    def getColumnNames(self):
        return self.columnNames

    def addRow(self, values=None):
        if values:
            self.data.append(values)

    def addRowFromSearchResult(self, rowResult):
        # not every result row in the results list will contain a cell for every column in the table
        # fill in missing cells with the empty string
        values = []
        strippedRowResultFields = {k.strip(): v for k, v in list(rowResult.fields.items())}
        for field in self.columnNames:
            if field in strippedRowResultFields:
                fieldValues = strippedRowResultFields.get(field, None)
                logger.debug(
                    "type=%s fieldValues=%s len(fieldValues)=%s isinstance(fieldValues, splunk.search.RawEvent)=%s$" % (
                        type(fieldValues), fieldValues, len(fieldValues),
                        isinstance(fieldValues, splunk.search.RawEvent)))
                if isinstance(fieldValues, splunk.search.RawEvent):
                    fieldValuesStr = fieldValues
                elif len(fieldValues) > 1:
                    fieldValueStrings = [str(x) for x in fieldValues]
                    if "##__SPARKLINE__##".startswith(fieldValueStrings[0]):
                        fieldValuesStr = ','.join(fieldValueStrings)
                    else:
                        fieldValuesStr = '\n'.join(fieldValueStrings)
                    logger.debug("fieldValueStrings=%s fieldValuesStr=%s" % (fieldValueStrings, fieldValuesStr))
                else:
                    fieldValuesStr = fieldValues[0]
                values.append(str(fieldValuesStr))
            else:
                values.append("")

        self.addRow(values)

    def formatValues(self):
        self.updateTimeFormat()

    def updateTimeFormat(self):
        if self.columnNames is None:
            return
        """
        transform timestamp to user friendly string
        ported from time.js
        """

        def isTimeColumn(name):
            """
            ported from ResultsTableMaster.js isTimeField()
            """
            return name in TIME_COLUMNS

        def allInListMatch(array, matchValue):
            for v in array:
                if v != matchValue:
                    return False
            return True

        def determineTimestampFormat(timeStats):
            if not allInListMatch(timeStats["milliseconds"], 0):
                return TIMESTAMP_FORMAT_MILLISECOND
            if not allInListMatch(timeStats["seconds"], 0):
                return TIMESTAMP_FORMAT_SECOND
            if not allInListMatch(timeStats["minutes"], 0):
                return TIMESTAMP_FORMAT_MINUTE
            if not allInListMatch(timeStats["hours"], 0):
                return TIMESTAMP_FORMAT_HOUR
            if not allInListMatch(timeStats["days"], 1):
                return TIMESTAMP_FORMAT_DAY
            if not allInListMatch(timeStats["months"], 1):
                return TIMESTAMP_FORMAT_MONTH
            return TIMESTAMP_FORMAT_YEAR


        timeData = dict()
        timeStats = dict()
        timeFormat = dict()
        # initialize temp dict

        for columnName in self.columnNames:
            if isTimeColumn(columnName):
                timeStats[columnName] = {
                    "milliseconds": [],
                    "seconds": [],
                    "minutes": [],
                    "hours": [],
                    "days": [],
                    "months": []
                }
                timeData[columnName] = []

        for rowIdx, row in enumerate(self.data):
            for columnIdx, cell in enumerate(row):
                columnName = self.columnNames[columnIdx]
                if columnName in timeData:
                    if cell:
                        t = splunk.util.parseISO(cell)
                        timeData[columnName].append(t)
                        # update stats
                        timeStats[columnName]["milliseconds"].append(t.microsecond)
                        timeStats[columnName]["seconds"].append(t.second)
                        timeStats[columnName]["minutes"].append(t.minute)
                        timeStats[columnName]["hours"].append(t.hour)
                        timeStats[columnName]["days"].append(t.day)
                        timeStats[columnName]["months"].append(t.month)
                    else:
                        timeData[columnName].append('')

        # update time format for time column
        for columnName in timeStats:
            format = determineTimestampFormat(timeStats[columnName])
            timeFormat[columnName] = format
            logger.info('use timestamp format %s for column %s' % (format, columnName))

        # update display value
        for rowIdx, row in enumerate(self.data):
            for columnIdx, cell in enumerate(row):
                columnName = self.columnNames[columnIdx]
                if columnName in timeFormat:
                    datetime = timeData[columnName][rowIdx]
                    if datetime:
                        v = datetime.strftime(timeFormat[columnName])
                        if timeFormat[columnName] == TIMESTAMP_FORMAT_MILLISECOND:
                            v = v.replace('{msec}', '%03d' % int(datetime.microsecond / 1000.0))
                    else:
                        v = ''
                    self.data[rowIdx][columnIdx] = v


#
# TableText
# This Flowable subclass wraps HARD at width boundaries
#
class TableText(Flowable):
    """ TableText
        I couldn't get ReportLab's Paragraph flowables to appropriately wrap text strings
        without whitespace. The entire point of this class is to allow the breaking
        of text in the middle of words when necessary. This entire class can use a good
        look for optimization and cleanup
    """

    _text = ""
    _prewrapLines = []
    _lines = []
    height = 0
    width = 0
    _fontSize = 0
    _lineHeight = 0
    _fontManager = None
    _maxCellHeight = 0
    _isNumber = None

    def __init__(self, text, fontManager=None, fontSize=TABLE_FONT_SIZE, maxCellHeight=100):
        assert (text != None)
        assert (fontManager != None)

        text = toUnicode(text)

        # setup private variables
        self._fontManager = fontManager
        self._fontSize = fontSize
        self._lineHeight = self._fontSize + 2
        self._maxCellHeight = maxCellHeight

        # store the text data in its individual lines
        self._prewrapLines = text.splitlines()
        self._maxWidth = None
        self.width = self.getMaxWidth()
        self.rawText = text
        self._wrapCache = {}
        self._wrapCacheHits = 0
        self._wrapCacheMisses = 0
        self._isWrapped = False

    def isNumeric(self):
        if self._isNumber != None:
            return self._isNumber

        self._isNumber = True
        for line in self._prewrapLines:
            if not isNumber(line):
                self._isNumber = False
                break

        return self._isNumber

    def getMaxWidth(self):
        if self._maxWidth != None:
            return self._maxWidth

        self._maxWidth = 0

        for prewrapLine in self._prewrapLines:
            self._maxWidth = max(self._maxWidth, self._fontManager.textWidth(prewrapLine, self._fontSize))

        return self._maxWidth

    def wrap(self, availWidth, availHeight):
        if not self._isWrapped:
            cacheKey = "%s" % availWidth
            # the wrapCache stores a dictionary of availWidth:(width, height, lines)
            if cacheKey in self._wrapCache:
                if _PERF_TEST:
                    self._wrapCacheHits = self._wrapCacheHits + 1
                self.width = self._wrapCache[cacheKey][0]
                self.height = self._wrapCache[cacheKey][1]
                self._lines = self._wrapCache[cacheKey][2]
            else:
                # self._wrap returns the width required for the text
                start = 0
                finish = 0
                if _PERF_TEST:
                    self._wrapCacheMisses = self._wrapCacheMisses + 1
                    start = time.time()

                self.width = self._wrap(availWidth)

                if _PERF_TEST:
                    finish = time.time()
                    wrapTimes.append(finish - start)
                self.height = self._lineHeight * len(self._lines)

                self._wrapCache[cacheKey] = (self.width, self.height, self._lines)

            self._isWrapped = True

        return self.width, self.height

    def draw(self):
        """ draw each line """
        start = 0
        finish = 0
        if _PERF_TEST:
            wrapCacheHits.append(self._wrapCacheHits)
            wrapCacheMisses.append(self._wrapCacheMisses)
            start = time.time()

        self.canv.saveState()
        for i, line in enumerate(self._lines):
            textObj = self.canv.beginText(x=0, y=self.height - (i + 1) * self._lineHeight)
            self._fontManager.addTextAndFontToTextObject(textObj, line, self._fontSize)
            self.canv.drawText(textObj)
        self.canv.restoreState()

        if _PERF_TEST:
            finish = time.time()
            drawTimes.append(finish - start)

    def _wrap(self, availWidth):
        """ fills the self._lines array with the actual text to output in self.draw()
            returns minWidthRequired

            this is a VERY VERY dumb word wrapping algorithm
            we first split the text based on line breaks, then for each original line:
                1) if the entire line fits in the availWidth, then output the line
                2) split the line into individual words, fill the output line with words that fit
                3) when we reach the point that the next word will overflow the availWidth, then
                    a) if the word will fit on the next line, put it on the next line, otherwise
                    b) split the word so that we fill the current line, then deal with the rest of the word on the next line
        """

        self._lines = []
        minWidthRequired = 0

        if len(self._prewrapLines) == 0:
            return minWidthRequired

        spaceWidth = self._fontManager.textWidth(" ", self._fontSize)

        tempLines = self._prewrapLines
        currentTempLine = 0
        #logger.debug("TableText::_wrap> availWidth: " + str(availWidth) + ", tempLines: " + str(tempLines))
        for currentTempLine, tempLine in enumerate(tempLines):
            tempLineWidth = self._fontManager.textWidth(tempLine, self._fontSize)
            #logger.debug("TableText::_wrap> tempLine: " + tempLine + ", tempLineWidth: " + str(tempLineWidth))

            if tempLineWidth <= availWidth:
                # easy case: the entire line fits within availWidth

                #logger.debug("TableText::_wrap> tempLineWidth <= availWidth")
                self._lines.append(tempLine)
                minWidthRequired = tempLineWidth
            else:
                # the line needs to be wrapped in order to fit in availWidth
                # break the line into tokens, each token is a word or number or a punctuation character

                tempWords = re.split("(\W)", tempLine)
                totalLinesHeight = len(self._lines) * self._lineHeight
                while len(tempWords) > 0 and totalLinesHeight < self._maxCellHeight:
                    #logger.debug("TableText::_wrap> starting new line. Words left: " + str(tempWords))
                    currentLineWords = []
                    remainingWidth = availWidth

                    fillingCurrentLine = True
                    # TODO: remove any leading spaces

                    while fillingCurrentLine:
                        tempWord = tempWords.pop(0)

                        # reportlab doesn't handle \t character. replace with space
                        if tempWord == '\t':
                            tempWord = ' '

                        start = 0
                        finish = 0
                        if _PERF_TEST:
                            start = time.time()

                        tempWordWidth = self._fontManager.textWidth(tempWord, self._fontSize)

                        if _PERF_TEST:
                            finish = time.time()
                            stringWidthTimes.append(finish-start)

                        #addSpace = False
                        #logger.debug("TableText::_wrap> word: " + tempWord + ", wordWidth: " + str(tempWordWidth) + ", remainingWidth: " + str(remainingWidth))
                        if len(currentLineWords) > 0:
                            tempWordWidth = tempWordWidth + spaceWidth
                            #addSpace = True

                        if tempWordWidth <= remainingWidth:
                            # temp word can fit in the remaining space
                            #logger.debug("TableText::_wrap> can fit within remaining space")

                            #if addSpace:
                            #	currentLineWords.append(" ")
                            currentLineWords.append(tempWord)
                            remainingWidth = remainingWidth - tempWordWidth
                        elif tempWordWidth <= availWidth:
                            # temp word cannot fit in the remaining space, but can fit on a new line
                            #logger.debug("TableText::_wrap> cannot fit within remaining space, but can fit on next line")

                            tempWords.insert(0, tempWord)
                            remainingWidth = 0
                            fillingCurrentLine = False
                        else:
                            # temp word cannot fit in the remaining space, nor can it fit on a new line
                            # hard-break a segment off the word that will fit in the remaining space
                            #logger.debug("TableText::_wrap> cannot fit within remaining space, and cannot fit on next line")

                            #if addSpace:
                            #	remainingWidth = remainingWidth - spaceWidth
                            firstSegment, restOfWord = self._wrapWord(tempWord, remainingWidth, wordWidth = tempWordWidth)
                            #logger.debug("TableText::_wrap> broke word " + tempWord + " into: " + firstSegment + " and " + restOfWord)
                            tempWords.insert(0, restOfWord)
                            #if addSpace:
                            #	currentLineWords.append(" ")
                            currentLineWords.append(firstSegment)
                            fillingCurrentLine = False

                        if len(tempWords) == 0:
                            # we're done filling the current line, given that there are no more words
                            fillingCurrentLine = False

                    currentLine = "".join(currentLineWords)
                    self._lines.append(currentLine)
                    totalLinesHeight = len(self._lines) * self._lineHeight
                    minWidthRequired = max(minWidthRequired, availWidth - remainingWidth)

            # check to see if we need to truncate the cell's contents
            if (len(self._lines) * self._lineHeight) >= self._maxCellHeight:
                break

        if (currentTempLine + 1) < len(tempLines):
            # we truncated
            percentageShown = (100.0 * float(currentTempLine) / float(len(tempLines)))
            logger.info("TableText::_wrap> truncated cell contents. %s%% shown." % percentageShown)
            # TODO: this needs to be internationalized
            self._lines.append("... Truncated. %s%% shown." % percentageShown)

        logger.debug("TableText::_wrap> minWidthRequired: " + str(minWidthRequired) + ", self._lines: " + str(self._lines))
        return minWidthRequired

    def _wrapWord(self, word, availWidth, wordWidth = 0):
        """ returns a tuple: firstSegment, restOfWord where firstSegment will fit in the availWidth """
        wordLen = len(word)

        if wordWidth == 0:
            wordWidth = self._fontManager.textWidth(word)

        # TODO: for a starting point, assume that we can break proportionally
        #breakIndex = int(float(wordLen) * float(availWidth) / float(wordWidth))

        breakIndex = 0
        segmentWidth = 0
        nextCharWidth = self._fontManager.textWidth(word[breakIndex], self._fontSize)

        while (segmentWidth + nextCharWidth) < availWidth:
            breakIndex = breakIndex + 1
            if breakIndex >= wordLen:
                # TODO: better exception handling
                raise ValueError("Cannot establish break in word: " + str(word))
            segmentWidth = segmentWidth + nextCharWidth
            nextCharWidth = self._fontManager.textWidth(word[breakIndex], self._fontSize)

        firstSegment = word[:breakIndex]
        restOfWord = word[breakIndex:]

        return firstSegment, restOfWord


styles = getSampleStyleSheet()
ColTitleStyle = styles["BodyText"]
ColTitleStyle.alignment = TA_LEFT
ColTitleStyle.fontSize = 8
ColTitleStyle.leftIndent = 2


class DivisibleTable(Table):
    SUB_TITLE_HEIGHT = 15
    """
    Table that can be split by columns and rows
    """
    def __init__(self, data, colWidths=None, rowHeights=None, style=None, repeatRows=0, repeatCols=0, splitByRow=1,
                 emptyTableAction=None, ident=None, hAlign=None, vAlign=None, normalizedData=0, cellStyles=None, **kwargs):
        # track the global start index of column in this table instance
        self._startColIdx = 1
        # whether to display column split title
        self._enableColTitle = False
        Table.__init__(self, data, colWidths, rowHeights, style, repeatRows, repeatCols, splitByRow, emptyTableAction,
                       ident, hAlign, vAlign, normalizedData, cellStyles, **kwargs)
        # track the global end index of column in this table instance
        self._endColIdx = len(self._colWidths) - self.repeatCols
        # track the total column count
        self._totalCol = self._endColIdx
        # table title. We cannot change the signature of default constructor so it will be set after instantiate
        self.title = None
        self.fontManager = None

    def _copyProps(self, tables):
        for t in tables:
            if isinstance(t, DivisibleTable):
                t.fontManager = self.fontManager
                t.title = self.title
                t._totalCol = self._totalCol

    def split(self, availWidth, availHeight):
        """
        This split algorithm support both row split and column split.
        If the table is too large both in height and width, it will be split in row first, then columns.

        Let's say we have a table and the maximum row/column supported in one page is 2 x 2

            ---------------------------
             1 |  2 |  3 |  4 |  5 | 6
            ---------------------------
             7 |  8 |  9 | 10 | 11 | 12
            ---------------------------
            13 | 14 | 15 | 16 | 17 | 18
            ---------------------------
            19 | 20 | 21 | 22 | 23 | 24
            ---------------------------

        the splitting will be handled in following steps.

        STEP1: split the table by rows

            R1 =    ---------------------------
                     1 |  2 |  3 |  4 |  5 | 6
                    ---------------------------
                     7 |  8 |  9 | 10 | 11 | 12
                    ---------------------------

            R2 =    ---------------------------
                    13 | 14 | 15 | 16 | 17 | 18
                    ---------------------------
                    19 | 20 | 21 | 22 | 23 | 24
                    ---------------------------

        STEP2: split the first table (R1 in this case) by columns

            T0 =    --------        T1 =     -----------------
                     1 |  2                   3 |  4 |  5 |  6
                    --------                 -----------------
                     7 |  8                   9 | 10 | 11 | 12
                    --------                 -----------------

        STEP3: return Flowables array [T0, PageBreak, T1, R2]. They will be inserted into the head of Flowable queue.

        STEP4:
        Flowables will be retrieved from Flowable queue and handle one by one.
        Therefore, The split function will be called on T1 again as T1 has width exceed page size (2 x 2)
        Repeat Step 1 - 4 for all the oversize Flowables.


        The output of the table look like:

              Page1           Page2         Page3            Page4          Page5         Page6
            ---------       --------      ----------       ---------      --------      ----------
             1 |  2          3 |  4         5 |  6          13 | 14        15 | 16       17 | 18
            ---------       --------      ----------       ---------      --------      ----------
             7 |  8          9 | 10        11 | 12          19 | 20        21 | 22       23 | 24
            ---------       --------      ----------       ---------      --------      ----------

        """
        self._calc(availWidth, availHeight)
        # split by row first
        # give an offset for title column split title if necessary
        hOffset = self.SUB_TITLE_HEIGHT if self._getFirstPossibleSplitColumnPosition(availWidth)  else 0
        tables = self._splitRows(availHeight - hOffset)
        self._copyProps(tables)
        result = self._splitByColumns(tables, availWidth)
        logger.debug('Split table %s into %s flowables' % (self, len(result)))
        return result

    def _splitByColumns(self, tables, availWidth):
        """
        only split the first flowable by columns
        """
        if len(tables) is 0: return []
        f = tables[0]
        restTables = tables[1:]

        n = f._getFirstPossibleSplitColumnPosition(availWidth)
        logger.debug('Break table by column index %s' % n)
        # the table fits in , no need to split
        if n == 0: return tables

        repeatRows = f.repeatRows
        repeatCols = f.repeatCols
        splitByRow = f.splitByRow
        data, restData = self._splitDataByColumns(f._cellvalues, n)
        cellStyle, restStyles = self._splitDataByColumns(f._cellStyles, n)
        columnWidths = f._colWidths[:n]
        restColumnWidths = f._colWidths[n:]
        ident = f.ident
        if ident: ident = IdentStr(ident)

        T0 = DivisibleTable(data, colWidths=columnWidths, rowHeights=f._argH,
                            repeatRows=repeatRows, repeatCols=repeatCols,
                            splitByRow=splitByRow, normalizedData=1, cellStyles=cellStyle,
                            ident=ident)

        T0._enableColTitle = True
        T0._startColIdx = f._startColIdx
        T0._endColIdx = f._startColIdx + (n - self.repeatCols - 1)

        logger.debug('Create sub table T0 %s with col index %s to %s' % (T0, T0._startColIdx, T0._endColIdx))
        if repeatCols:
            # handle repeated columns, merge the data, styles in repeated column and the column widths array
            repeatColData = self._splitDataByColumns(data, repeatCols)[0]
            restData = self.mergeDataByColumns(repeatColData, restData)
            repeatColStyles = self._splitDataByColumns(cellStyle, repeatCols)[0]
            restStyles = self.mergeDataByColumns(repeatColStyles, restStyles)
            restColumnWidths = columnWidths[:repeatCols] + restColumnWidths

        T1 = DivisibleTable(restData, colWidths=restColumnWidths, rowHeights=f._argH,
                            repeatRows=repeatRows, repeatCols=repeatCols,
                            splitByRow=splitByRow, normalizedData=1, cellStyles=restStyles,
                            ident=ident)

        T1._enableColTitle= True
        T1._startColIdx = T0._endColIdx + 1
        T1._endColIdx = f._endColIdx
        self._copyProps([T0, T1])

        logger.debug('Create sub table T1 %s with col index %s to %s' % (T1, T1._startColIdx, T1._endColIdx))
        lineCmds = self._genLineCommandsInColumnSplit(n)
        T0._appendCommandsBeforeCol(n, lineCmds)
        T0._appendCommandsBeforeCol(n, f._bkgrndcmds)
        T0._appendCommandsBeforeCol(n, f._spanCmds)
        T0._appendCommandsBeforeCol(n, f._nosplitCmds)

        if repeatCols:
            T1._appendCommandsAfterColWithRepeatColumns(n, repeatCols, lineCmds)
            T1._appendCommandsAfterColWithRepeatColumns(n, repeatCols, f._bkgrndcmds)
            T1._appendCommandsAfterColWithRepeatColumns(n, repeatCols, f._spanCmds)
            T1._appendCommandsAfterColWithRepeatColumns(n, repeatCols, f._nosplitCmds)
        else:
            T1._appendCommandsAfterCol(n, lineCmds)
            T1._appendCommandsAfterCol(n, f._bkgrndcmds)
            T1._appendCommandsAfterCol(n, f._spanCmds)
            T1._appendCommandsAfterCol(n, f._nosplitCmds)

        T0.hAlign = T1.hAlign = self.hAlign
        T0.vAlign = T1.vAlign = self.vAlign
        result = [T0._getColumnSplitTitle(), T0, PageBreak()]
        if T1._getFirstPossibleSplitColumnPosition(availWidth):
            # if T1 can NOT be fit in, we don't need to generated the title flowable
            result += [T1] + restTables
        else:
            # if T1 can be fit in, generate the title as it should be last flowable in columns
            result += [T1._getColumnSplitTitle(), T1] + restTables
        return result

    def _getColumnSplitTitle(self):
        if self._startColIdx == self._endColIdx:
            text = "%s (Column %s of %s)" % (self.title or "", self._startColIdx, self._totalCol)
        else:
            text = "%s (Columns %s-%s of %s)" % (self.title or "", self._startColIdx, self._endColIdx, self._totalCol)
        readyText = su.escape(text)
        return Paragraph(self.fontManager.encodeTextForParagraph(readyText), ColTitleStyle)

    def _genLineCommandsInColumnSplit(self, n):
        A = []
        # Touch with cautious
        # hack up the line commands.
        # sc,sr = start column,row, ec,er = end column,row
        for op, (sc, sr), (ec, er), weight, color, cap, dash, join, count, space in self._linecmds:
            if sc < 0: sc = sc + self._ncols
            if ec < 0: ec = ec + self._ncols
            if sr < 0: sr = sr + self._nrows
            if er < 0: er = er + self._nrows

            if op in ('BOX', 'OUTLINE', 'GRID'):
                if sc < n and ec >= n:
                    """
                        Split the box when necessary.
                        For example, if we need to split the following table by column at cell c,
                        then we have to manually draw each borders as BOX command is no longer applicable
                            -------------              -------        ---
                          a | b   c   d | e   ==>    a | b   c  and   d | e
                            -------------              -------        ---
                    """
                    # draw the left border at start column
                    A.append(('LINEBEFORE', (sc, sr), (sc, er), weight, color, cap, dash, join, count, space))
                    # draw the right border at end column
                    A.append(('LINEAFTER', (ec, sr), (ec, er), weight, color, cap, dash, join, count, space))
                    # draw the top border at start row
                    A.append(('LINEABOVE', (sc, sr), (ec, sr), weight, color, cap, dash, join, count, space))
                    # draw the bottom border at end row
                    A.append(('LINEBELOW', (sc, er), (ec, er), weight, color, cap, dash, join, count, space))

                    if op == 'GRID':
                        # draw extra line at split column and right after split column
                        A.append(('LINEBEFORE', (n, sr), (n, er), weight, color, cap, dash, join, count, space))
                        A.append(('LINEAFTER', (n - 1, sr), (n - 1, er), weight, color, cap, dash, join, count, space))
                        A.append(('INNERGRID', (sc, sr), (ec, er), weight, color, cap, dash, join, count, space))
                else:
                    A.append((op, (sc, sr), (ec, er), weight, color, cap, dash, join, count, space))
            elif op in ('INNERGRID', 'LINEBEFORE'):
                if sc < n and ec >= n:
                    # draw extra left border at split column and right border after split column
                    A.append(('LINEAFTER', (n - 1, sr), (n - 1, er), weight, color, cap, dash, join, count, space))
                    A.append(('LINEBEFORE', (n, sr), (n, er), weight, color, cap, dash, join, count, space))
                A.append((op, (sc, sr), (ec, er), weight, color, cap, dash, join, count, space))
            elif op == 'LINEAFTER':
                if sc < n and ec >= (n - 1):
                    # append a extra left border
                    A.append(('LINEBEFORE', (n, sr), (n, er), weight, color, cap, dash, join, count, space))
                A.append((op, (sc, sr), (ec, er), weight, color))
            elif op == 'LINEBEFORE':
                if sc <= n and ec >= n:
                    # append extra right border at split column
                    A.append(('LINEAFTER', (n - 1, sr), (n - 1, er), weight, color, cap, dash, join, count, space))
                A.append((op, (sc, sr), (ec, er), weight, color, cap, dash, join, count, space))
            else:
                A.append((op, (sc, sr), (ec, er), weight, color, cap, dash, join, count, space))
        return A

    def _appendCommandsBeforeCol(self, n, cmds):
        """
        Apply command for column index < n
        """
        for c in cmds:
            c = tuple(c)
            (sc, sr), (ec, er) = c[1:3]
            if sc >= n: continue
            # set the end col index to n-1
            if ec >= n: ec = n - 1
            self._addCommand((c[0],) + ((sc, sr), (ec, er)) + c[3:])

    def _appendCommandsAfterCol(self, n, cmds):
        """
        Apply command for cells column index >= n
        """
        for c in cmds:
            c = tuple(c)
            (sc, sr), (ec, er) = c[1:3]
            if ec >= 0 and ec < n: continue
            if sc >= 0 and sc < n: sc = 0
            if sc >= n: sc = sc - n
            if ec >= n: ec = ec - n
            self._addCommand((c[0],) + ((sc, sr), (ec, er)) + c[3:])

    def _appendCommandsAfterColWithRepeatColumns(self, n, repeatColumns, cmds):
        """
        Apply command for cells column index >= n with repeat columns
        """
        for c in cmds:
            c = tuple(c)
            (sc, sr), (ec, er) = c[1:3]
            if sc >= 0 and sc >= repeatColumns and sc < n and ec >= 0 and ec < n: continue
            if sc >= repeatColumns and sc < n:
                sc = repeatColumns
            elif sc >= repeatColumns and sc >= n:
                sc = sc + repeatColumns - n
            if ec >= repeatColumns and ec < n:
                ec = repeatColumns
            elif ec >= repeatColumns and ec >= n:
                ec = ec + repeatColumns - n
            self._addCommand((c[0],) + ((sc, sr), (ec, er)) + c[3:])

    def _splitDataByColumns(self, data, index):
        """
        break 2 dimension data set by column
        """
        left = []
        right = []
        for rowIdx, row in enumerate(data):
            leftRow = []
            rightRow = []
            for columnIdx, value in enumerate(row):
                if columnIdx < index:
                    leftRow.append(value)
                else:
                    rightRow.append(value)
            left.append(leftRow)
            right.append(rightRow)
        return left, right

    def mergeDataByColumns(self, d1, d2):
        """
        merge 2 dimension data set
        """
        newData = []
        for rowIdx, row in enumerate(d1):
            newData.append(row + d2[rowIdx])
        return newData

    def _getFirstPossibleSplitColumnPosition(self, availWidth):
        """
        calculate the column idx at which table will be split
        return 0 if table can fit in
        """
        h = 0
        n = 1
        split_at = 0  # from this point of view 0 is the first position where the table may *always* be splitted
        for rh in self._colWidths:
            # break when width > or = available width.
            if h + rh >= availWidth:
                break
            split_at = n
            h = h + rh
            n = n + 1

        lim = len(self._colWidths)
        # the table fits in , no need to split
        if split_at == lim:
            split_at = 0

        return split_at


class TableBuilder(object):
    """
    This class encapsulates all the algorithms that transform raw data into table cell flowables and generate table styles
    """
    _DEFAULT_SPARKLINE_STYLE = {"type": "line", "lineColor": "#5cc05c"}
    _TABLE_COL_LEFT_PADDING = 2
    _TABLE_COL_RIGHT_PADDING = 2
    _TABLE_COL_TOP_PADDING = 2
    _TABLE_COL_BOTTOM_PADDING = 2
    _TABLE_H_PADDING = _TABLE_COL_LEFT_PADDING + _TABLE_COL_RIGHT_PADDING
    _TABLE_V_PADDING = _TABLE_COL_TOP_PADDING + _TABLE_COL_BOTTOM_PADDING
    _ROW_NUMBER_COL_WIDTH = 20

    def __init__(self, tableData, fontManager, title=None, columnVAlignments=None, displayLineNumbers=False,
                 fieldFormats=None, overlayMode=None, tableSize=None):
        # internal data structure
        self._tableCells = []  # Cell flowables
        self._numberCells = []  # Tuple (columnIdx,rowIdx) of number cells

        self._maxColWidths = []  # Use to calculate column size
        self._requiredColWidths = []  # Use to calculate column size

        self._rowHeights = []  # Optimized heights array of table rows
        self._colWidths = []  # Optimized widths array of table column
        self._tableStyle = None  # Table style
        self._tableData = tableData  # Raw Table data with headers

        self._title = title  # Table title
        self._columnVAlignments = columnVAlignments or []
        self._fieldFormats = fieldFormats or {}
        self._displayLineNumbers = displayLineNumbers  # Whether display line number
        self._tableSize = tableSize or pagesizes.A4  # Table size , tuple (width, height)
        # max column width is half of the paper width with offset
        self._maxColWidth = old_div((self._tableSize[0] - self._ROW_NUMBER_COL_WIDTH), 2) - 5
        self._fontManager = fontManager
        # Max cell height = table height - header height - offset
        # in most of the case header can be display in one line,
        # but we would like to give a bigger(safer) value here so that it won't go out of the page
        self._maxCellHeight = self._tableSize[1] - (self._TABLE_V_PADDING + 60)
        self._overlayMode = overlayMode
        logger.debug('max cell height %s' % self._maxCellHeight)

    def build(self):
        """
        Build the Table Flowable instance
        """
        # format the raw values
        self._tableData.formatValues()
        self._prepareCells()
        self._optimizeCellSize()
        self._appendRowNumber()
        self._prepareTableStyle()
        repeatRows = 1 if self._hasHeader() else 0
        repeatCols = 1 if self._displayLineNumbers else 0

        table = DivisibleTable(data=self._tableCells, colWidths=self._colWidths, rowHeights=self._rowHeights,
                          style=self._tableStyle, repeatRows=repeatRows, repeatCols=repeatCols, hAlign="LEFT")
        table.fontManager = self._fontManager
        table.title = self._title
        return table

    def _prepareCells(self):
        columnNames = self._tableData.getColumnNames()
        rawData = self._tableData.getData()

        # append table header
        if columnNames != None:
            rawData.insert(0, columnNames)
            logger.info("renderTable> headerRow: " + str(columnNames))

        # create cell Flowables
        for rowIdx, row in enumerate(rawData):
            styledRow = []
            for cellNum, cell in enumerate(row):
                cellValue = str(cell)
                if "##__SPARKLINE__##" in cellValue:
                    # build sparkline and insert into row
                    # cellNumber = cellNum - 1 if displayLineNumbers else cellNum
                    # default sparkline format
                    options = self._DEFAULT_SPARKLINE_STYLE
                    if columnNames is not None:
                        cellName = columnNames[cellNum]
                        if self._fieldFormats and cellName in self._fieldFormats and self._fieldFormats[cellName][0] and \
                                        self._fieldFormats[cellName][0]['type'] == 'sparkline':
                            options = self._fieldFormats[cellName][0]['options']

                    logger.debug("renderTable> create sparkline with cellValue %s options %s" % (cellValue, options))
                    cellFlowable = ps.createSparkLine(cellValue, options)
                    styledRow.append(cellFlowable)
                else:
                    cellFlowable = TableText(cellValue, fontManager=self._fontManager,
                                             maxCellHeight=self._maxCellHeight)
                    styledRow.append(cellFlowable)

                self._trackCellSize(rowIdx, cellNum, cellFlowable)

            self._tableCells.append(styledRow)

    def _appendRowNumber(self):
        if self._displayLineNumbers:
            # append line number cell
            for index, row in enumerate(self._tableCells):
                if index == 0 and self._hasHeader():
                    cell = TableText("#", fontManager=self._fontManager, maxCellHeight=self._maxCellHeight)
                    self._tableData.getColumnNames().insert(0, "#")
                else:
                    rowNumber = index
                    if not self._hasHeader():
                        rowNumber = rowNumber + 1
                    cell = TableText(str(rowNumber), fontManager=self._fontManager, maxCellHeight=self._maxCellHeight)
                row.insert(0, cell)

            self._colWidths.insert(0, self._ROW_NUMBER_COL_WIDTH)

    def _trackCellSize(self, rowIdx, colIdx, flowable):
        if rowIdx == 0:
            # initialize value with header width
            self._requiredColWidths.append(min(flowable.width + self._TABLE_H_PADDING, self._maxColWidth))
            self._maxColWidths.append(flowable.width + self._TABLE_H_PADDING)

        # update max column widths
        self._maxColWidths[colIdx] = max(self._maxColWidths[colIdx], flowable.width + self._TABLE_H_PADDING)
        # update require column widths
        # require column width will be the width of longest number or timestamp in that column
        if flowable.isNumeric() or (self._hasHeader() and self._tableData.getColumnNames()[colIdx] in TIME_COLUMNS):
            self._requiredColWidths[colIdx] = min(max(self._requiredColWidths[colIdx],
                                                      flowable.width + self._TABLE_H_PADDING), self._maxColWidth)

    def _optimizeCellSize(self):
        """
        Manually calculate the table row heights and column widths to achieve better performance
        """
        # Calculate the column widths
        tableSize = self._tableSize[0] - self._ROW_NUMBER_COL_WIDTH if self._displayLineNumbers else self._tableSize[0]

        # In PDFFrame._add(), if the tableWidth is exactly same as page width, this table will be considered NOT able to fit into the current Frame
        # The condition of checking this is w > aW - _FUZZ, true will be returned if w == aW and split() will be called on table unexpectedly
        # Reportlab apply _FUZZ value when checking table height, so we'd better keep it for width. Therefore, apply a small offset to the tableWidth
        columnSizer = ColumnSizer(self._requiredColWidths, self._maxColWidths, tableWidth=tableSize - 2,
                                  columnPadding=self._TABLE_COL_LEFT_PADDING + self._TABLE_COL_RIGHT_PADDING)
        self._colWidths = columnSizer.getWidths()
        logger.debug('optimized table size,  width %s table columns sizes %s' % (self._tableSize[0], self._colWidths))
        # display row numbers if the table is going to be split by columns
        if sum(self._colWidths) > tableSize:
            self._displayLineNumbers = True
        # Given the column widths, calculate row heights
        for rowIdx, row in enumerate(self._tableCells):
            rowHeight = 0
            for cellNum, cellFlowable in enumerate(row):
                columnWidth = self._colWidths[cellNum]
                # set default height to Sparkline height
                cellHeight = ps.SPARK_LINE_HEIGHT
                if isinstance(cellFlowable, TableText):
                    # the availHeight is not used in wrap, so simply pass in 0
                    # fixme, the wrapped cell height may bigger than _maxCellHeight
                    cellWidth, cellHeight = cellFlowable.wrap(columnWidth, 0)
                    # we don't care the cellWidth here because the columnWidth is already been calculated.
                rowHeight = max(rowHeight, cellHeight + self._TABLE_V_PADDING)
            self._rowHeights.append(rowHeight)
        logger.debug('optimized table size, height %s table row heights %s' % (self._tableSize[1], self._rowHeights))

    def _prepareTableStyle(self):
        dataOverlayManager = createDataOverlay(self._overlayMode, self._tableData.getColumnNames())
        # track the position of number cell and add data into data overlay manager
        for rowIdx, row in enumerate(self._tableCells):
            for colIdx, flowable in enumerate(row):
                if flowable.isNumeric():
                    self._numberCells.append((colIdx, rowIdx))
                if isinstance(flowable, TableText) and dataOverlayManager:
                    dataOverlayManager.addValue(colIdx, rowIdx, str(flowable.rawText))

        # create the necessary table style commands to handle vertical alignment setting
        tableStyleCommands = []
        if self._columnVAlignments is not None:
            for i, valign in enumerate(self._columnVAlignments):
                tableStyleCommands.append(('VALIGN', (i, 0), (i, -1), valign))

        # line to the right of all columns
        tableStyleCommands.append(('LINEAFTER', (0, 0), (-2, -1), 0.25, colors.lightgrey))

        # SPL-100337, left align number if row count == 1
        rowCount = len(self._tableCells) - 1 if self._hasHeader() else len(self._tableCells)
        numberAlign = 'LEFT' if rowCount == 1 else 'RIGHT'
        for numberCell in self._numberCells:
            tableStyleCommands.append(('ALIGN', numberCell, numberCell, numberAlign))

        if self._displayLineNumbers:
            tableStyleCommands.append(('ALIGN', (0, 0), (0, 0), 'RIGHT'))

        firstDataRow = 0
        if self._hasHeader():
            tableStyleCommands.append(('LINEBELOW', (0, 0), (-1, 0), 1, colors.black))
            firstDataRow = 1
        # lines to the bottom and to the right of each cell
        tableStyleCommands.append(('LINEBELOW', (0, firstDataRow), (-1, -2), 0.25, colors.lightgrey))

        # tighten up the columns
        tableStyleCommands.append(('LEFTPADDING', (0, 0), (-1, -1), self._TABLE_COL_LEFT_PADDING))
        tableStyleCommands.append(('RIGHTPADDING', (0, 0), (-1, -1), self._TABLE_COL_RIGHT_PADDING))
        tableStyleCommands.append(('TOPPADDING', (0, 0), (-1, -1), self._TABLE_COL_TOP_PADDING))
        tableStyleCommands.append(('BOTTOMPADDING', (0, 0), (-1, -1), self._TABLE_COL_BOTTOM_PADDING))

        # compute dataOverlay
        if dataOverlayManager:
            dataOverlayManager.ready()
            for (rowIdx, columnIdx, color) in dataOverlayManager.getNumberCellsWithColor():
                if not self._displayLineNumbers or columnIdx != 0:
                    tableStyleCommands.append(
                        ('BACKGROUND', (columnIdx, rowIdx), (columnIdx, rowIdx), color))
                    logger.debug('append overlay style %s %s %s ' % (columnIdx, rowIdx, color))

        self._tableStyle = TableStyle(tableStyleCommands)

    def _hasHeader(self):
        return self._tableData.getColumnNames() is not None


class ColumnSizer(object):
    """ This class encapsulates the algorithms used to determine the width of table columns
        To use, initialize with necessary parameters and then call getWidths() to get column widths  """
    _tableWidth = 0
    _columnPadding = 0
    _numCols = 0
    _colWidths = None
    _maxWidths = None

    def __init__(self, minWidths, maxWidths, tableWidth=100, columnPadding=10):
        """ cellWidthsByCol is a 2d array of the widths of the table's cells, organized by column """
        self._tableWidth = tableWidth
        self._columnPadding = columnPadding
        self._numCols = len(minWidths)
        self._minWidths = minWidths
        self._maxWidths = maxWidths

    def getWidths(self):
        """ Run through a series of allocation methods with the intent of sizing our tables' columns in a reasonable manner
            This function is memoized """
        if self._colWidths != None:
            return self._colWidths

        self._initColWidths()

        # first try setting all columns using the 'simple proportional' allocation method
        # this method tries to allocate space to all unfixed columns that is proportional to their max widths
        # and provides for the max widths. This method will do nothing if it cannot fit all unfixed columns
        numUnfixedCols = self._getNumUnfixedCols()
        if numUnfixedCols > 1:
            self._allocateSimpleProportional()

        # if any columns are still unfixed, go through and set all columns that are smaller than the 'fair' width
        # to their max size -- this should free up space for future 'fair' and 'proportional' calculations
        numUnfixedCols = self._getNumUnfixedCols()
        if numUnfixedCols > 1:
            self._allocateByMax()

        # use the simpleProportional allocation method and allow it to set column widths that are smaller than
        # the columns' desired max widths
        numUnfixedCols = self._getNumUnfixedCols()
        if numUnfixedCols > 1:
            self._allocateSimpleProportional(allowLessThanMax=True)

        # if any columns remain unfixed, allocate all remaining space by the 'fair' width
        numUnfixedCols = self._getNumUnfixedCols()
        if numUnfixedCols > 0:
            self._allocateRemainingSpace()

        return self._colWidths

    def _initColWidths(self):
        # the convention here is that any column with 0 width has not yet been set
        self._colWidths = [0] * self._numCols

    def _getNumUnfixedCols(self):
        """ return the count of unfixed columns. This is based on the convention that an unfixed column as 0 width """
        return self._colWidths.count(0)

    def _allocateSimpleProportional(self, allowLessThanMax=False):
        """ for all unfixed columns, try to set their widths such that they are proportional to their max widths and
            greater than their max widths (unless allowLessThanMax=True). Only actualy fix any columns widths if we can fix all unfixed columns at this
            time """
        availableSpace = self._getAvailableSpace()
        totalColWidths = float(self._getSumUnfixedColMaxWidths())

        # determine the proportional column widths: max/total * availableSpace
        # the colProportions for any already fixed columns will be INVALID
        colProportions = [(float(x) / totalColWidths) * availableSpace for x in self._maxWidths]

        # this is all or nothing -- if a single column's max width is bigger than the proportional space alotted, return without
        # any side effects
        newWidths = self._colWidths[:]
        for index, colWidth in enumerate(self._colWidths):
            if colWidth == 0:
                if not allowLessThanMax and self._maxWidths[index] > colProportions[index]:
                    return
                newWidths[index] = max(colProportions[index], self._minWidths[index])

        # all the columns will fit! set the column widths to the proportional widths
        self._colWidths = newWidths[:]

    def _getSumUnfixedColMaxWidths(self):
        """ return the sum of the max widths of all unfixed columns """
        sumMaxWidths = 0

        for index, colWidth in enumerate(self._colWidths):
            if colWidth == 0:
                sumMaxWidths = sumMaxWidths + self._maxWidths[index]

        return sumMaxWidths

    def _allocateRemainingSpace(self):
        """ assign every unfixed column to use the fair width """
        numUnfixedCols = self._colWidths.count(0)
        if numUnfixedCols == 0:
            return self

        fairWidth = self._getFairWidth()
        for index, colWidth in enumerate(self._colWidths):
            if colWidth == 0:
                self._colWidths[index] = max(fairWidth, self._minWidths[index])

    def _allocateByMax(self):
        """ for any column whose max width is smaller than the fair width, fix that column to use its max width """
        # preset fixedAtLeastOneWidth to true to allow first iteration
        fixedAtLeastOneWidth = True
        while fixedAtLeastOneWidth and self._colWidths.count(0) > 0:
            # step one, find all columns that fit in less than 'fair width'
            fairWidth = self._getFairWidth()

            # find any columns whose maxWidth < fairWidth, and fix those columns' width at maxWidth
            fixedAtLeastOneWidth = False
            for index, maxWidth in enumerate(self._maxWidths):
                if self._colWidths[index] == 0:
                    if maxWidth <= fairWidth:
                        self._colWidths[index] = max(maxWidth, self._minWidths[index])
                        fixedAtLeastOneWidth = True

    def _getFairWidth(self):
        """ return the amount of space available to each unfixed column if we allocate the available space without any proportions """
        unsetNumCols = self._colWidths.count(0)
        if unsetNumCols == 0:
            return 0

        return old_div(self._getAvailableSpace(), unsetNumCols)

    def _getAvailableSpace(self):
        """ return the amount of space that is left after taking account of padding and columns whose width is already fixed """
        availableWidth = self._tableWidth - self._numCols * self._columnPadding # columnPadding is combo of left/right padding, therefore not just in between columns
        for fixedColWidth in self._colWidths:
            availableWidth = availableWidth - fixedColWidth

        return max(availableWidth, 0)


def isNumber(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


DECIMAL_OR_SCIENTIFIC_REGEX = re.compile("(^[-+]?[0-9]*[.]?[0-9]*$)|(^[-+]?[0-9][.]?[0-9]*e[-+]?[1-9][0-9]*$)")


def strictParseFloat(text):
    result = None
    if DECIMAL_OR_SCIENTIFIC_REGEX.match(text):
        try:
            # Fix SPL-98330, return 0 for "0"
            result = float(text)
        except ValueError:
            result = None
    return result
