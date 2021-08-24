from __future__ import absolute_import
from builtins import object

import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.pdfbase.cidfonts as cidfonts
from reportlab.pdfbase.cidfonts import UnicodeCIDFont, CIDEncoding

import splunk.pdf.pdfgen_utils as pu
import splunk.util as util

FILE_MANAGER_DIR = os.path.dirname(__file__)

logger = pu.getLogger()

class FontManager(object):
    _fonts = []
    _fontIdxByCodePoint = {}
    _cidFontList = ['gb', 'cns', 'jp', 'kor']

    def __init__(self, cidFontList=None):
        self._cidFontList = [cidFont.lower() for cidFont in (cidFontList or self._cidFontList)]

        # Helvetica is our default for latin script, always prioritize first
        from splunk.pdf import helvetica_codes
        self.addFontName("Helvetica", helvetica_codes.codes)

        # Allow administrator to provide fonts for all other scripts
        self._initTTFonts()

        # By default, add, with least priority, CID fonts for CJK
        self._initCIDFonts()

    def _initCIDFonts(self):
        from splunk.pdf import cns_codes
        from splunk.pdf import gb_codes
        from splunk.pdf import jpn_codes
        from splunk.pdf import kor_codes

        cidFontInfo = {
            'gb': {
                'fontName': 'STSong-Light',
                'codeArray': gb_codes.codes
                },
            'cns': {
                'fontName': 'MSung-Light',
                'codeArray': cns_codes.codes
                },
            'jp': {
                'fontName': 'HeiseiMin-W3',
                'codeArray': jpn_codes.codes
                },
            'kor': {
                'fontName': 'HYSMyeongJo-Medium',
                'codeArray': kor_codes.codes
                }}

        for cidFont in self._cidFontList:
            if cidFont in cidFontInfo:
                font = UnicodeCIDFont(cidFontInfo[cidFont]['fontName'])
                pdfmetrics.registerFont(font)
                self.addFont(font, cidFontInfo[cidFont]['codeArray'])

    def _initTTFonts(self):
        fontDir = os.path.join(os.environ['SPLUNK_HOME'], 'share', 'splunk', 'fonts')
        if not os.path.exists(fontDir):
            return

        fontFileList = sorted(os.listdir(fontDir))
        for fontFile in fontFileList:
            if fontFile.lower().endswith(".ttf"):
                logger.info("FontManager initializing the following TT font: " + str(fontFile))
                fontPath = os.path.join(fontDir, fontFile)
                self.addFontPath(fontFile, fontPath)

    def addFontPath(self, fontName, fontPath):
        font = TTFont(fontName, fontPath)
        pdfmetrics.registerFont(font)
        self.addFont(font)

    def addFontName(self, fontName, codes=None):
        font = pdfmetrics.getFont(fontName)
        self.addFont(font, codes)

    def addFont(self, font, codes=None):
        if font in self._fonts:
            return

        fontIdx = len(self._fonts)
        self._fonts.append(font.fontName)

        if isinstance(font, TTFont):
            logger.debug("FontManager::addFont> font=%s is TTFont" % font.fontName)
            codePoints = font.face.charWidths
            for codePoint in codePoints:
                self._addCodePoint(codePoint, fontIdx)

        elif isinstance(font, UnicodeCIDFont):
            assert(codes != None)
            logger.debug("FontManager::addFont> font=%s is UnicodeCIDFont" % font.fontName)
            for codePoint in codes:
                self._addCodePoint(codePoint, fontIdx)

        #TODO: probably need to handle more cases
        else:
            # handle standard fonts
            logger.debug("FontManager::addFont> font=%s ASSUMPTION is standard font" % font.fontName)
            for i, width in enumerate(font.widths):
                if width != 0:
                    codePoint = i
                    self._addCodePoint(codePoint, fontIdx)
            if codes:
                for codePoint in codes:
                    self._addCodePoint(codePoint, fontIdx)

    def _addCodePoint(self, codePoint, fontIdx):
        if codePoint not in self._fontIdxByCodePoint:
            self._fontIdxByCodePoint[codePoint] = fontIdx

    def addTextAndFontToTextObject(self, textObject, text, fontSize, textDataArray=None):
        """ given a ReportLab TextObject and a block of text,
            prepare the TextObject such that all the subsets of text that require a different font
            are rendered accordingly """
        if textDataArray == None:
            textDataArray = self.segmentTextByFont(text)

        for textData in textDataArray:
            textObject.setFont(self._fonts[textData["fontIdx"]], fontSize)
            textObject.textOut(textData["text"])

    def addLinesAndFontToTextObject(self, textObject, lines, fontSize, textDataArray=None):
        def writeLine(line, newLine=False):
            textDataArray = self.segmentTextByFont(line)
            for textData in textDataArray[:-1]:
                textObject.setFont(self._fonts[textData["fontIdx"]], fontSize)
                textObject.textOut(textData["text"])
            if len(textDataArray) > 0:
                textObject.setFont(self._fonts[textDataArray[-1]["fontIdx"]], fontSize)
                if newLine:
                    textObject.textLine(textDataArray[-1]["text"])
                else:
                    textObject.textOut(textDataArray[-1]["text"])

        for line in lines[:-1]:
            writeLine(line, True)
        if len(lines) > 0:
            writeLine(lines[-1], False)

    def encodeTextForParagraph(self, text, textDataArray=None):
        outputTextArray = []

        if textDataArray == None:
            textDataArray = self.segmentTextByFont(text)

        for textData in textDataArray:
            outputTextArray.append(u"<font face=%s>%s</font>" % (self._fonts[textData["fontIdx"]], textData["text"]))

        outputText = u''.join(outputTextArray)
        return outputText

    _textWidthCache = {}
    def textWidth(self, text, fontSize, textDataArray=None):
        """ return the width of the text, given the font manager's fonts at the given font size """

        cacheKey = '%s:%s' % (text, fontSize)
        if cacheKey in self._textWidthCache:
            return self._textWidthCache[cacheKey]

        if len(self._textWidthCache) > 20000:
            self._textWidthCache = {}

        if textDataArray == None:
            textDataArray = self.segmentTextByFont(text)

        textWidth = 0
        for textData in textDataArray:
            font = pdfmetrics.getFont(self._fonts[textData["fontIdx"]])
            textWidth = textWidth + font.stringWidth(textData["text"], fontSize)

        self._textWidthCache[cacheKey] = textWidth
        return textWidth

    #
    # segmentTextByFont is the workhorse of this class
    #
    def segmentTextByFont(self, text):
        """ given input text of "hello XXX" (where XXX is non-latin)
            build up an array of:
            [{font:0, text:"hello "}, {font:1, text:"XXX"}]
        """
        outputTextData = []

        characterOrds = []
        # convert to unicode if currently in utf-8 encoding
        text = util.toUnicode(text)

        #logger.debug("FontManager::segmentTextByFont> type(text)=%s type(textU)=%s" % (str(type(text)), str(type(textU))))
        for character in text:
            characterOrds.append(ord(character))
        #logger.debug("FontManager::segmentTextByFont> text=%s ords=%s " % (text, str(characterOrds)))

        currentFontIdx = -1
        charactersWithThisFontIdx = []
        for character in text:
            characterOrd = ord(character)
            #logger.debug("FontManager::segmentTextByFont> characterOrd in dict=%s" % str(characterOrd in self._fontIdxByCodePoint))
            if characterOrd in self._fontIdxByCodePoint:
                #logger.debug("FontManager::segmentTextByFont> character=%s ord=%s" % (character, str(characterOrd)))
                neededFontIdx = self._fontIdxByCodePoint[characterOrd]
                if currentFontIdx != neededFontIdx:
                    #logger.debug("FontManager::segmentTextByFont> currentIdx=%s neededFontIdx=%s charactersWithThisFontIdx=%s" % (str(currentFontIdx), str(neededFontIdx), str(charactersWithThisFontIdx)))

                    if len(charactersWithThisFontIdx) > 0:
                        textData = {"fontIdx": currentFontIdx, "text": u''.join(charactersWithThisFontIdx)}
                        outputTextData.append(textData)
                        charactersWithThisFontIdx = []

                    currentFontIdx = neededFontIdx

                charactersWithThisFontIdx.append(character)

        #logger.debug("FontManager::segmentTextByFont> currentIdx=%s charactersWithThisFontIdx=%s" % (str(currentFontIdx), str(charactersWithThisFontIdx)))
        if len(charactersWithThisFontIdx) > 0:
            textData = {"fontIdx": currentFontIdx, "text": u''.join(charactersWithThisFontIdx)}
            outputTextData.append(textData)

        return outputTextData


#
# _extractCharCodesFromCMapFile
# This is a utility function to be used by developers to generate character code files
# that will be read by the addFontWithCodes function
#
def _extractCharCodesFromCMapFile(encodingName, codesFileName):
    """ cmap file must be in ~/fonts/CMap/ """
    cidfonts.DISABLE_CMAP=False
    test = cidfonts.CIDEncoding(encodingName, useCache=0)
    logger.debug("FontManager::__init__> test.getData()=%s" % test.getData())
    f = open(os.path.join(FILE_MANAGER_DIR, codesFileName), 'w')
    for code in test.getData()['cmap']:
        f.write("%s\n" % str(code))
    f.close()
