from past.utils import old_div
from builtins import object
import copy
from lxml import etree
import math
import re
import textwrap
import xml.sax.saxutils as su

import reportlab
import reportlab.pdfgen
import reportlab.pdfgen.canvas
from reportlab.platypus import Paragraph, CondPageBreak, Flowable, FrameBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics import renderPDF
import reportlab.lib.enums

from reportlab.lib import pagesizes
from splunk.util import toDefaultStrings
from splunk.pdf import pdfgen_base as pb
from splunk.pdf import pdfgen_svg
from splunk.pdf import pdfgen_table as pt
from splunk.pdf import pdfgen_utils as pu

from splunk.pdf.font_manager import FontManager
from splunk.pdf import image_utils as imageUtils
from splunk.pdf.html_image import HtmlImage
from splunk.pdf.pdf_html_parser import PdfHtmlParser

logger = pu.getLogger()

PAPERSIZES = {
    "letter":
        {
            'reportLabPaperSize': pagesizes.LETTER,
            'logoTransformSize': 0.33
        },
    "letter-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.LETTER),
            'logoTransformSize': 0.33
        },
    "legal":
        {
            'reportLabPaperSize': pagesizes.LEGAL,
            'logoTransformSize': 0.33
        },
    "legal-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.LEGAL),
            'logoTransformSize': 0.33
        },
    "eleven-seventeen":
        {
            'reportLabPaperSize': pagesizes.ELEVENSEVENTEEN,
            'logoTransformSize': 0.33
        },
    "eleven-seventeen-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.ELEVENSEVENTEEN),
            'logoTransformSize': 0.33
        },
    "tabloid":
        {
            'reportLabPaperSize': pagesizes.ELEVENSEVENTEEN,
            'logoTransformSize': 0.33
        },
    "ledger":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.ELEVENSEVENTEEN),
            'logoTransformSize': 0.33
        },
    "a5":
        {
            'reportLabPaperSize': pagesizes.A5,
            'ellipsizedTitleCount': 30,
            'logoTransformSize': 0.20
        },
    "a5-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.A5),
            'logoTransformSize': 0.33
        },
    "a4":
        {
            'reportLabPaperSize': pagesizes.A4,
            'logoTransformSize': 0.33
        },
    "a4-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.A4),
            'logoTransformSize': 0.33
        },
    "a3":
        {
            'reportLabPaperSize': pagesizes.A3,
            'logoTransformSize': 0.33
        },
    "a3-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.A3),
            'logoTransformSize': 0.33
        },
    "a2":
        {
            'reportLabPaperSize': pagesizes.A2,
            'logoTransformSize': 0.33
        },
    "a2-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.A2),
            'logoTransformSize': 0.33
        },
    "a1":
        {
            'reportLabPaperSize': pagesizes.A1,
            'logoTransformSize': 0.33
        },
    "a1-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.A1),
            'logoTransformSize': 0.33
        },
    "a0":
        {
            'reportLabPaperSize': pagesizes.A0,
            'logoTransformSize': 0.33
        },
    "a0-landscape":
        {
            'reportLabPaperSize': pagesizes.landscape(pagesizes.A0),
            'logoTransformSize': 0.33
        }
}

TABLE_FONT_NAME = "Helvetica"
STYLES = getSampleStyleSheet()
setattr(STYLES['Normal'], "autoLeading", "max")

class PDFRenderer(object):

    ONE_INCH = 1.0 * inch
    MIN_HEIGHT_TABLE_AND_CHART = 4 * inch
    # It is a little hard coded, 2 * inch = 144px ~= (14+7.2)*2+100
    MIN_HEIGHT_SINGLE_VALUE = 2 * inch

    _fontManager = None

    outputFile = None
    reportLabPaperSize = (0, 0)
    _includeSplunkLogo = True
    _title = ""
    _description = ""
    _story = []
    _runningAsScript = False

    _style = STYLES["Normal"]
    CENTER_STYLE = copy.deepcopy(STYLES['Normal'])
    TITLE_STYLE = copy.deepcopy(STYLES["Normal"])
    TITLE_STYLE.wordWrap = 'CJK'
    SUBTITLE_STYLE = copy.deepcopy(STYLES["Normal"])
    SUBTITLE_STYLE.wordWrap = 'CJK'
    BULLET_STYLE = STYLES["Bullet"]
    _bulletStyle = STYLES["Bullet"]
    _tableTitleStyle = STYLES["Title"]
    _listTitleStyle = STYLES["Bullet"]
    _hardWrapStyle = copy.deepcopy(STYLES["Normal"])
    _hardWrapStyle.wordWrap = "CJK"
    _TABLE_COL_LEFT_PADDING = 2
    _TABLE_COL_RIGHT_PADDING = 2
    _TABLE_COL_TOP_PADDING = 2
    _TABLE_COL_BOTTOM_PADDING = 2
    _MARGINS = [inch, inch, inch, inch]
    _CUSTOM_LOGO_HEIGHT = 45
    _pageElements = {}
    _DEFAULT_SPARKLINE_STYLE = {"type": "line", "lineColor": "#5cc05c"}
    _requestSettings = {}

    def __init__(self, namespace, title, description, outputFile, paperSize, timestamp="", includeSplunkLogo=None,
                 cidFontList=None, pdfSettings=None, requestSettings=None):
        """ outputFile can either be a filename or a file-like object """
        self.namespace = namespace
        self.outputFile = outputFile
        self.paperSize = paperSize
        self.settings = pdfSettings
        self._requestSettings = requestSettings
        self.reportLabPaperSize = PAPERSIZES[self.paperSize]['reportLabPaperSize']
        # if pager size is too small, update min height to paper height - margins - offset(5)
        self.MIN_HEIGHT_TABLE_AND_CHART = min(self.MIN_HEIGHT_TABLE_AND_CHART,
                                              self.reportLabPaperSize[1] - 2 * inch - 5)
        self.logoTransformSize = PAPERSIZES[self.paperSize]['logoTransformSize']
        self._log("outputFile: " + str(self.outputFile))
        self._log("reportLabPaperSize: " + str(self.reportLabPaperSize))
        self._title = title
        self._description = description
        self._timestamp = timestamp
        if includeSplunkLogo != None:
            self._includeSplunkLogo = includeSplunkLogo
        logger.debug("pdf-init pdfrenderer include-splunk-logo=%s" % self._includeSplunkLogo)

        self._fontManager = FontManager(cidFontList=cidFontList)

        self.TITLE_STYLE.fontSize = 14
        self.TITLE_STYLE.leading = 16
        self.SUBTITLE_STYLE.fontSize = 12
        self.SUBTITLE_STYLE.leading = 16
        self.CENTER_STYLE.alignment=reportlab.lib.enums.TA_CENTER

        # TODO: need a better way to determine max cell height
        #       225 ~= margins + footer height + a few lines for header row
        self.maxTableCellHeight = self.reportLabPaperSize[1] - 225
        self.normalizePageSettings()
        return

    def conditionalPageBreak(self, types):
        if 'single' in types:
            self._story.append(CondPageBreak(self.MIN_HEIGHT_SINGLE_VALUE))
        else:
            self._story.append(CondPageBreak(self.MIN_HEIGHT_TABLE_AND_CHART))

    def spaceBetween(self, space = 0.5 * inch):
        self._story.append(EnsureSpaceBetween(space))

    def renderText(self, text, style = None, escapeText = True):
        if style is None:
            style = self._style

        if escapeText:
            readyText = su.escape(text)
        else:
            readyText = text

        logger.debug("renderText readyText='%s'" % readyText)
        self._story.append(Paragraph(self._fontManager.encodeTextForParagraph(readyText), style))

    def renderBulletText(self, text, bullet = '-', style = None):
        if style is None:
            style = self._bulletStyle
        self._story.append(Paragraph(self._fontManager.encodeTextForParagraph(su.escape(text)), style, bulletText = bullet))

    def getLocalPathFromUrl(self, uri, relative=None):
        pattern = r".*/static/app/([^/]*)/(.*)"
        m = re.match(pattern, uri)
        if m != None:
            appName = m.group(1)
            filePath = m.group(2)
            self._log("event=get_link_local_path app=%s file_path=%s" % (appName, filePath))
            path = pu.getAppStaticResource(appName, filePath)
        else:
            path = uri
        self._log("event=image_local_path image_path=%s" % (path))
        return path

    def renderImage(self, imagePath, width=None, height=None, hAlign='CENTER'):
        def safeCast(val, toType, default=None):
            try:
                return toType(val)
            except (ValueError, TypeError) as e:
                return default

        if imagePath:
            try:
                self._story.append(HtmlImage(imagePath,
                    safeCast(width, int), safeCast(height, int), hAlign.upper(),
                    requestSettings=self._requestSettings))
            except:
                self._log("event=render_non_existing_image image_path=%s" % (imagePath), "warning")

    def renderHtml(self, text):
        htmlImageRendering = self.settings.get(SETTING_HTML_IMAGE_RENDERING)
        logger.debug("event=render_html html=%s" % (text))

        if htmlImageRendering:
            self.renderHtmlWithImage(text)
        else:
            self.renderHtmlWithoutImage(text)

    def renderHtmlWithImage(self, text):
        if text is None:
            return

        parser = PdfHtmlParser()
        fragments = parser.parse(text)
        for frag in fragments:
            if frag.tag != 'img':
                self.renderHtmlWithoutImage(toDefaultStrings(etree.tostring(frag, encoding='UTF-8')))
            else:
                self.spaceBetween(0.15 * inch)
                src = frag.attrib.get('src')
                width = frag.attrib.get('width', None)
                height = frag.attrib.get('height', None)
                align = frag.attrib.get('align', 'CENTER')
                localPath = self.getLocalPathFromUrl(src)
                self.renderImage(localPath, width, height, align)


    def renderHtmlWithoutImage(self, text):
        if text is None:
            return

        def multiple_replacer(*key_values):
            replace_dict = dict(key_values)
            replacement_function = lambda match: replace_dict[match.group(0)]
            pattern = re.compile("|".join([re.escape(k) for k, v in key_values]), re.M)
            return lambda string: pattern.sub(replacement_function, string)

        def multiple_replace(string, *key_values):
            return multiple_replacer(*key_values)(string)

        self._log("event=render_html_without_image html=%s" % (text))

        # reportlab supports a set of text manipulation tags
        #  transform those HTML tags that aren't supported into reportlab
        #  supported tags
        lineBreakingTagReplacements = (
            u"<li>", u"<li><br/>"), (
            u"<h1>", u"<h1><font size='24'><br/><br/>"), (
            u"</h1>", u"</font><br/></h1>"), (
            u"<h2>", u"<h2><font size='20'><br/><br/>"), (
            u"</h2>", u"</font><br/></h2>"), (
            u"<h3>", u"<h3><font size='18'><br/><br/>"), (
            u"</h3>", u"</font><br/></h3>"), (
            u"<h4>", u"<h4><font size='14'><br/>"), (
            u"</h4>", u"</font><br/></h4>"), (
            u"<h5>", u"<h5><font size='12'><br/>"), (
            u"</h5>", u"</font><br/></h5>"), (
            u"<h6>", u"<h6><br/>"), (
            u"</h6>", u"<br/></h6>"), (
            u"<h7>", u"<h7><br/>"), (
            u"</h7>", u"<br/></h7>"), (
            u"<h8>", u"<h8><br/>"), (
            u"</h8>", u"<br/></h8>"), (
            u"<h9>", u"<h9><br/>"), (
            u"</h9>", u"<br/></h9>"), (
            u"<h10>", u"<h10><br/>"), (
            u"</h10>", u"<br/></h10>"), (
            u"<br>", u"<br/>"), (
            u"<p>", u"<p><br/>")

        repText = multiple_replace(text, *lineBreakingTagReplacements)

        # need to remove some elements
        #  any elements that make references to external things -- don't want reportlab to try to resolve links
        #  reportlab doesn't like the title attribute
        removeElements = [
            '(<img[^>]*>)', '(</img>)',
            '(title="[^"]*")',
            '(<a[^>]*>)', '(</a>)',
            '(<style(.*?\n*)*?/style>)'
            ]

        repText = re.sub('|'.join(removeElements), '', repText)
        logger.debug("renderHtml text='%s' repText='%s'" % (text, repText))

        self.renderText(repText, escapeText=False)


    def renderTextNoFormatting(self, text):
        self._story.append(pt.TableText(text, fontManager=self._fontManager))

    def renderListItem(self, text, sequencerNum = None, style = None):
        if style is None:
            style = self._listTitleStyle
        if sequencerNum != None:
            text = "<seq id="+str(sequencerNum)+"/>" + text
        self._story.append(Paragraph(self._fontManager.encodeTextForParagraph(su.escape(text)), style))

    def renderTable(self, tableData=None, title=None, columnVAlignments=None,
                    displayLineNumbers=False, fieldFormats=None, overlayMode=None):
        tableSize = (self.reportLabPaperSize[0] - self._MARGINS[0] - self._MARGINS[2],
                     self.reportLabPaperSize[1] - self._MARGINS[1] - self._MARGINS[3])
        # create the Table flowable and insert into story
        tb = pt.TableBuilder(tableData, self._fontManager, title=title, columnVAlignments=columnVAlignments,
                             displayLineNumbers=displayLineNumbers, fieldFormats=fieldFormats, overlayMode=overlayMode,
                             tableSize=tableSize)
        self._story.append(tb.build())

    def renderSvgString(self, svgString, title = None):
        svgImageFlowable = pdfgen_svg.getSvgImageFromString(svgString, self._fontManager)
        if svgImageFlowable is None:
            self._log("renderSvg> svgImageFlowable for " + svgString + " is invalid")
        else:
            if title != None:
                self.renderText(title, style = self._tableTitleStyle)
            self._story.append(svgImageFlowable)

    def save(self):
        doc = pb.PDFDocTemplate(self.outputFile, pagesize=self.reportLabPaperSize)
        doc.setTitle(self._title)
        doc.setDesc(self._description)
        doc.splunkPaperSize = self.paperSize
        doc.setTimestamp(self._timestamp)
        doc.setFontManager(self._fontManager)
        doc.setPageSettings(self._showHeader, self._showFooter, self._pageElements)
        doc.setRequestSettings(self._requestSettings)

        if self._includeSplunkLogo:
            logoPath = self.settings.get(SETTING_LOGO_PATH)
            self._log("logo path = %s" % logoPath)
            if logoPath:
                # retrieve customize logo if it's not a empty string
                try:
                    image = self.getCustomLogo(logoPath)
                except Exception as e:
                    self._log("Failed to retrieve customize logo error %s" % e, logLevel='error')
                else:
                    doc.setLogoImage(image)
            else:
                # fallback to use splunk logo by default
                logo = _splunkLogoSvg.replace("***logoTransformSize***", str(self.logoTransformSize))
                doc.setLogoSvgString(logo)
        self._log("Doc pageSize: " + str(getattr(doc, "pagesize")))

        for flowable in self._story:
            if not hasattr(flowable, 'hAlign'):
                flowable.hAlign = 'CENTER'

        doc.build(self._story, onFirstPage=_footerAndHeader, onLaterPages=_footerAndHeader)

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

    def getCustomLogo(self, path):
        # syntax <app>:<path>
        # myapp:mylogo.png -> etc/apps/myapp/appserver/static/mylogo.png
        # myapp:images/mylogo.png -> etc/apps/myapp/appserver/static/images/mylogo.png
        # mylogo.png -> etc/apps/<current app>/appserver/static/mylogo.png
        segments = path.split(":", 1)
        if len(segments) >= 2:
            app = segments[0]
            file = segments[1]
        elif len(segments) == 1:
            app = self.namespace
            file = segments[0]
        logoPath = pu.getAppStaticResource(app, file)
        imageReader = imageUtils.PngImageReader(logoPath)
        self._log("customize logo; path=%s, width=%s, height=%s" % (
            path, imageReader._width, imageReader._height),
                  logLevel='info')
        return imageReader

    def normalizePageSettings(self):
        self._pageElements.clear()
        self._log("normalize page settings; settings=%s" % self.settings, logLevel='info')
        self._showHeader = self.settings.get(SETTING_HEADER_ENABLED, False)
        self._showFooter = self.settings.get(SETTING_FOOTER_ENABLED, True)
        self._log("show header %s" % self._showHeader)
        self._log("show footer %s" % self._showFooter)
        for position in HEADER + FOOTER:
            elements = self.settings.get(position, None)
            if elements and elements != ELEMENT_NONE:
                for e in elements.split(","):
                    if (self._showHeader and position in HEADER) or (self._showFooter and position in FOOTER):
                        if e not in self._pageElements:
                            self._pageElements[e] = [position]
                        else:
                            self._pageElements[e].append(position)

        # validate couple corner cases
        # 1. not allow to have multiple title or desc in one section
        if ELEMENT_TITLE in self._pageElements:
            if set(self._pageElements[ELEMENT_TITLE]) < set(HEADER) or set(self._pageElements[ELEMENT_TITLE]) < set(
                    FOOTER):
                # use the first definition
                self._pageElements[ELEMENT_TITLE] = self._pageElements[ELEMENT_TITLE][:1]

        if ELEMENT_DESC in self._pageElements:
            if set(self._pageElements[ELEMENT_DESC]) < set(HEADER) or set(self._pageElements[ELEMENT_DESC]) < set(
                    FOOTER):
                # use the first definition
                self._pageElements[ELEMENT_DESC] = self._pageElements[ELEMENT_DESC][:1]

        # 2. description and title cannot in the same section because they all have dynamic width
        if ELEMENT_DESC in self._pageElements and ELEMENT_TITLE in self._pageElements:
            if len(set(self._pageElements[ELEMENT_TITLE] + self._pageElements[ELEMENT_DESC]) & set(HEADER)) > 1 or len(set(
                            self._pageElements[ELEMENT_TITLE] + self._pageElements[ELEMENT_DESC]) & set(FOOTER)) > 1:
                # title is more important, hide description
                del self._pageElements[ELEMENT_DESC]

        self._log("normalize page settings; elements=%s" % self._pageElements, logLevel='info')


class EnsureSpaceBetween(Flowable):
    """ Make sure that there is either height space or a frame break inserted into the document """
    # most of this code copied from CondPageBreak
    def __init__(self, height):
        self.height = height

    def __repr__(self):
        return "EnsureSpaceBetween(%s)" % (self.height)

    def wrap(self, availWidth, availHeight):
        f = self._doctemplateAttr('frame')
        if not f:
            return availWidth, availHeight

        # if we're at the top of the page, we don't need a spacer
        if f._atTop == 1:
            return 0, 0

        # if we don't have enough space left on the page for the full space, we don't need a spacer
        if availHeight < self.height:
            f.add_generated_content(FrameBreak)
            return 0, 0

        # the spacer fits on the page
        return 0, self.height

    def draw(self):
        pass


#
# _ellipsize
# ellipsize the given text so that only maxCharLength characters are left
# position the ellipsis according to the ellipsisPlacement argument
# RETURNS: the ellipsized text string
#
_ELLIPSIS_PLACEMENT_LEFT = 0
_ELLIPSIS_PLACEMENT_CENTER = 1
_ELLIPSIS_PLACEMENT_RIGHT = 2
_ELLIPSIS = "..."
def _ellipsize(text, maxCharLength, ellipsisPlacement = _ELLIPSIS_PLACEMENT_RIGHT):
    if text == None or len(text) == 0:
        return ""

    if maxCharLength <= 0:
        return _ELLIPSIS

    textLen = len(text)
    numCharsToEllipsize = textLen - maxCharLength
    if numCharsToEllipsize > 0:
        if ellipsisPlacement == _ELLIPSIS_PLACEMENT_LEFT:
            text = _ELLIPSIS + text[numCharsToEllipsize:]
        elif ellipsisPlacement == _ELLIPSIS_PLACEMENT_CENTER:
            text = text[:textLen//2 - numCharsToEllipsize//2] + _ELLIPSIS + text[textLen//2 + numCharsToEllipsize//2:]
        elif ellipsisPlacement == _ELLIPSIS_PLACEMENT_RIGHT:
            text = text[:textLen - numCharsToEllipsize] + _ELLIPSIS
        else:
            text = text[:textLen - numCharsToEllipsize] + _ELLIPSIS

    return text

#
# _footerAndHeader
_LOGO_OFFSET = 14

# default font size
_TITLE_SIZE = 11
_DATE_SIZE = 9
_PAGER_SIZE = 12
_MIN_TEXT_SIZE = 8

_TEXT_OFFSET = 14

SETTING_PREFIX = 'pdf.'
# settings for customize footer & header
SETTING_FOOTER_ENABLED = 'pdf.footer_enabled'
SETTING_HEADER_ENABLED = 'pdf.header_enabled'

SETTING_HTML_IMAGE_RENDERING = 'pdf.html_image_rendering'
SETTING_HEADER_LEFT = 'pdf.header_left'
SETTING_HEADER_CENTER = 'pdf.header_center'
SETTING_HEADER_RIGHT = 'pdf.header_right'
SETTING_FOOTER_LEFT = 'pdf.footer_left'
SETTING_FOOTER_CENTER = 'pdf.footer_center'
SETTING_FOOTER_RIGHT = 'pdf.footer_right'

# customize logo
SETTING_LOGO_PATH = 'pdf.logo_path'

ELEMENT_NONE = 'none'
ELEMENT_TITLE = 'title'
ELEMENT_DESC = 'description'
ELEMENT_LOGO = 'logo'
ELEMENT_PAGINATION = 'pagination'
ELEMENT_TIMESTAMP = 'timestamp'

ALL_PDF_SETTINGS = [SETTING_FOOTER_ENABLED,
                SETTING_HEADER_ENABLED,
                SETTING_HEADER_LEFT,
                SETTING_HEADER_CENTER,
                SETTING_HEADER_RIGHT,
                SETTING_FOOTER_LEFT,
                SETTING_FOOTER_CENTER,
                SETTING_FOOTER_RIGHT,
                SETTING_LOGO_PATH,
                SETTING_HTML_IMAGE_RENDERING]

PDF_BOOLEAN_SETTINGS = [SETTING_FOOTER_ENABLED,
                        SETTING_HEADER_ENABLED,
                        SETTING_HTML_IMAGE_RENDERING]

HEADER = [SETTING_HEADER_LEFT, SETTING_HEADER_CENTER, SETTING_HEADER_RIGHT]
FOOTER = [SETTING_FOOTER_LEFT, SETTING_FOOTER_CENTER, SETTING_FOOTER_RIGHT]

def _footerAndHeader(canvas, doc):
    showHeader, showFooter, pageElements = doc.getPageSettings()
    canvas.saveState()
    if showFooter:
        canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
        canvas.setLineWidth(1)  # hairline
        canvas.line(inch, inch, doc.width + inch, inch)
    if showHeader:
        canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
        canvas.setLineWidth(1)  # hairline
        canvas.line(inch, inch + doc.height, doc.width + inch, inch + doc.height)

    # variables that track the remaining width of footer and header
    headerWidth = doc.width
    footerWidth = doc.width
    headerOffset = 0
    footerOffset = 0
    logger.debug("Footer&Header::_page> document width %s" % doc.width)
    for name in [ELEMENT_LOGO, ELEMENT_PAGINATION, ELEMENT_TIMESTAMP, ELEMENT_TITLE, ELEMENT_DESC]:
        positions = pageElements.get(name, None)
        if positions:
            for position in positions:
                element = None
                if name == ELEMENT_LOGO:
                    element = Logo(canvas, doc, position)
                elif name == ELEMENT_PAGINATION:
                    element = Text(canvas, doc, position, None, "Page %d" % (doc.page), _PAGER_SIZE)
                elif name == ELEMENT_TIMESTAMP:
                    element = TimeStamp(canvas, doc, position, None, doc.getTimestamp(), _DATE_SIZE)
                elif name == ELEMENT_TITLE:
                    maxWidth = headerWidth if position in HEADER else footerWidth
                    maxWidth -= 20  # offset
                    element = Text(canvas, doc, position, max(0, maxWidth), doc.getTitle(), _TITLE_SIZE)
                elif name == ELEMENT_DESC:
                    # get the remaining width
                    maxWidth = headerWidth if position in HEADER else footerWidth
                    maxWidth -= 20  # offset
                    logger.debug("Footer&Header::_page> description %s" % doc.getDesc())
                    logger.debug("Footer&Header::_page> description maxWidth %s" % maxWidth)
                    element = Text(canvas, doc, position, max(0, maxWidth), doc.getDesc(), _TITLE_SIZE, max_line=2)

                element.draw()

                elementWidth = element.getElementWidth() if name != ELEMENT_TIMESTAMP else 0

                if position in [SETTING_HEADER_LEFT, SETTING_HEADER_RIGHT]:
                    headerOffset = max(headerOffset, elementWidth)
                    headerWidth = doc.width - 2 * headerOffset
                elif position in [SETTING_HEADER_CENTER]:
                    headerWidth = old_div((doc.width - elementWidth), 2)

                if position in [SETTING_FOOTER_LEFT, SETTING_FOOTER_RIGHT]:
                    footerOffset = max(footerOffset, elementWidth)
                    footerWidth = doc.width - 2 * footerOffset
                elif position in [SETTING_FOOTER_CENTER]:
                    footerWidth = old_div((doc.width - elementWidth), 2)

                logger.debug("Test::_element> element name %s postion %s width %s" % (name, position, elementWidth))

    canvas.restoreState()


class PageElement(object):
    def __init__(self, canvas, doc, position=None, max_width=None):
        self._canvas = canvas
        self._doc = doc
        self._max_width = max_width
        self._pos = position
        self._heightOffset = 0

    def getElementWidth(self):
        """return element width"""
        return

    def getElementHeight(self):
        """return element height"""
        return

    def _getYInPage(self):
        y = inch - self.getElementHeight() - self._heightOffset
        if self._pos in HEADER:
            y = inch + self._doc.height + self._heightOffset
        return y

    def getPositionInPage(self):
        x = inch
        if self._pos in [SETTING_FOOTER_LEFT, SETTING_HEADER_LEFT]:
            x = inch
        elif self._pos in [SETTING_FOOTER_CENTER, SETTING_HEADER_CENTER]:
            x = inch + old_div(self._doc.width, 2) - old_div(self.getElementWidth(), 2)
        elif self._pos in [SETTING_FOOTER_RIGHT, SETTING_HEADER_RIGHT]:
            x = inch + self._doc.width - self.getElementWidth()

        y = self._getYInPage()
        return x, y

    def draw(self):
        """draw the element"""
        return


class Logo(PageElement):
    _logoDrawing = None
    _image = None
    _CUSTOM_LOGO_HEIGHT = 45

    def __init__(self, canvas, doc, position=None, max_width=None):
        super(Logo, self).__init__(canvas, doc, position, max_width)
        self._image = doc.getLogoImage()
        self._logoDrawing = doc.getLogoDrawing()
        self._image_height = 0
        self._image_width = 0
        if self._image:
            actualWidth = self._image._width
            actualHeight = self._image._height
            ratio = float(self._CUSTOM_LOGO_HEIGHT) / actualHeight if self._CUSTOM_LOGO_HEIGHT < actualHeight else 1
            self._image_height = ratio * actualHeight
            self._image_width = ratio * actualWidth
        elif self._logoDrawing:
            self._image_height = self._logoDrawing.height or 0
            self._image_width = self._logoDrawing.width or 0
        self._heightOffset = _LOGO_OFFSET

    def getElementWidth(self):
        return self._image_width

    def getElementHeight(self):
        return self._image_height

    def draw(self):
        self._canvas.restoreState()
        self._canvas.saveState()
        x, y = self.getPositionInPage()
        if self._image:
            self._canvas.drawImage(self._image, x, y, width=self._image_width,
                                   height=self._image_height, mask=None)
        elif self._logoDrawing:
            renderPDF.draw(self._logoDrawing, self._canvas, x, y, showBoundary=False)


# Text element will render text with given max width and max lines
class Text(PageElement):
    def __init__(self, canvas, doc, position=None, max_width=None, text=None, text_size=12, max_line=1):
        super(Text, self).__init__(canvas, doc, position, max_width)
        self._text = text
        self._textSize = text_size
        self._heightOffset = _TEXT_OFFSET
        self._maxLine = max_line
        self._width = 0
        self._lines = []
        self.adjust()

    def _getYInPage(self):
        y = 0.75 * inch - self.getElementHeight() - self._heightOffset
        if self._pos in HEADER:
            y = 1.25 * inch + self._doc.height + self._heightOffset
        return y

    def getElementWidth(self):
        return self._width

    # Adjust the text according to the max width and max lines.
    def adjust(self):
        if self._text:
            # text width on given font size
            width = self._doc.getFontManager().textWidth(self._text, self._textSize)
            if self._max_width and self._maxLine:
                maxWidth = self._max_width * self._maxLine
                # check whether text can fit in the area
                while width >= maxWidth:
                    if self._textSize == _MIN_TEXT_SIZE:
                        # reach minimal text size, ellipse the text,
                        self._text = _ellipsize(self._text, max(0, len(self._text) - 4))
                        width = self._doc.getFontManager().textWidth(self._text, self._textSize)
                    else:
                        # adjust font size
                        self._textSize -= 1
                        width = self._doc.getFontManager().textWidth(self._text, self._textSize)
                # average width per character
                widthPerCharacters = float(width) / len(self._text)
                logger.debug("Page::_element_text> widthPerCharacters. %s ." % widthPerCharacters)
                charactersPerLine = int(math.ceil(float(self._max_width) / widthPerCharacters))
                logger.debug("Page::_element_text> charactersPerLine. %s ." % charactersPerLine)
                # it's possible that textwrap return more lines, simply slice it
                self._lines = textwrap.wrap(self._text, charactersPerLine)[:self._maxLine]
            else:
                self._lines = [self._text]

            logger.debug("Page::_element_text> _lines. %s ." % self._lines)

        # if there's only one line, return the content width. otherwise, return the max width
        self._width = width if len(self._lines) == 1 else self._max_width

    def getElementHeight(self):
        return 0

    def setColor(self):
        # override this if you wan to change the color
        self._canvas.setStrokeColorRGB(0.5, 0.5, 0.5)
        self._canvas.setFillColorRGB(0.586, 0.586, 0.586)

    def draw(self):
        if self._text:
            self.setColor()
            logger.debug("Page::_elements> draw text. %s ." % self._text)
            x, y = self.getPositionInPage()
            textObject = self._canvas.beginText()
            textObject.setTextOrigin(x, y)
            logger.debug("Page::_elements> text origin. %s %s " % (x, y))
            self._doc.getFontManager().addLinesAndFontToTextObject(textObject, self._lines, self._textSize)
            self._canvas.drawText(textObject)


class TimeStamp(Text):
    def __init__(self, canvas, doc, position=None, max_width=None, text=None, text_size=15):
        super(TimeStamp, self).__init__(canvas, doc, position, max_width, text, text_size)

    def _getYInPage(self):
        y = inch - self.getElementHeight() - self._heightOffset
        if self._pos in HEADER:
            y = inch + self._doc.height + self._heightOffset
        return y

#
# _splunkLogoSvg
# this is the hard-coded splunk logo
_splunkLogoSvg = """
<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0" y="0"
 width="87" height="26" viewBox="0 0 263 78" enable-background="new 0 0 263 78" xml:space="preserve">
    <g transform="scale(***logoTransformSize***)">
        <g>
            <g>
                <path fill="#010101" stroke-width="0" stroke-opacity="0" stroke="#010101" d="M29.613,46.603c0,1.725-0.381,3.272-1.09,4.723c-0.738,1.453-1.741,2.679-3.024,3.679
                    c-1.279,1.018-2.82,1.807-4.602,2.368c-1.793,0.57-3.739,0.853-5.856,0.853c-2.531,0-4.782-0.342-6.813-1.022
                    c-2.011-0.695-4.019-1.856-6.029-3.435l3.342-5.418c1.577,1.34,3.02,2.302,4.321,2.932c1.28,0.621,2.603,0.933,3.951,0.933
                    c1.651,0,2.979-0.422,3.97-1.28c1.024-0.845,1.523-2.014,1.523-3.443c0-0.628-0.09-1.205-0.264-1.738
                    c-0.192-0.533-0.533-1.103-1.022-1.666c-0.478-0.585-1.139-1.209-2.002-1.876c-0.84-0.662-1.95-1.487-3.286-2.465
                    c-1.044-0.729-2.042-1.483-3.023-2.253c-0.965-0.77-1.849-1.6-2.678-2.487c-0.777-0.877-1.421-1.85-1.907-2.931
                    c-0.503-1.081-0.729-2.339-0.729-3.738c0-1.591,0.328-3.049,0.993-4.367c0.675-1.321,1.581-2.443,2.74-3.36
                    c1.156-0.947,2.545-1.669,4.171-2.169c1.625-0.525,3.383-0.77,5.271-0.77c2.041,0,3.991,0.271,5.858,0.8
                    c1.885,0.54,3.627,1.31,5.229,2.339l-3.027,4.862c-2.066-1.443-4.219-2.169-6.486-2.169c-1.395,0-2.537,0.363-3.462,1.088
                    c-0.898,0.734-1.346,1.621-1.346,2.72c0,1.021,0.401,1.958,1.199,2.776c0.783,0.833,2.165,1.988,4.121,3.49
                    c1.963,1.436,3.604,2.724,4.918,3.805c1.273,1.088,2.31,2.098,3.035,3.053c0.753,0.974,1.283,1.936,1.567,2.92
                    C29.463,44.322,29.613,45.419,29.613,46.603z"/>
                <path fill="#010101" stroke-width="0" stroke-opacity="0" stroke="#010101" d="M74.654,37.077c0,3.067-0.486,5.863-1.407,8.415c-0.924,2.547-2.217,4.778-3.882,6.688
                    c-1.669,1.913-3.642,3.42-5.896,4.452c-2.287,1.064-4.735,1.592-7.386,1.592c-1.204,0-2.304-0.095-3.355-0.304
                    c-1.025-0.209-1.993-0.557-2.924-1.045c-0.934-0.488-1.854-1.124-2.775-1.895c-0.904-0.777-1.839-1.747-2.831-2.879v24.536
                    h-9.942V18.587h9.942l0.065,5.64c1.806-2.257,3.765-3.922,5.901-4.977c2.1-1.056,4.55-1.581,7.346-1.581
                    c2.547,0,4.855,0.47,6.951,1.428c2.086,0.952,3.898,2.273,5.427,3.983c1.516,1.702,2.704,3.741,3.518,6.118
                    C74.245,31.57,74.654,34.198,74.654,37.077z M63.84,37.492c0-4.252-0.866-7.594-2.579-10.044
                    c-1.725-2.457-4.043-3.687-7.022-3.687c-3.105,0-5.572,1.307-7.395,3.917c-1.815,2.62-2.72,6.15-2.72,10.584
                    c0,4.33,0.892,7.734,2.674,10.229c1.813,2.487,4.243,3.724,7.359,3.724c1.887,0,3.438-0.467,4.645-1.444
                    c1.23-0.954,2.216-2.153,2.963-3.641c0.749-1.472,1.289-3.065,1.601-4.797C63.7,40.601,63.84,38.994,63.84,37.492z"/>
                <path fill="#010101" stroke-width="0" stroke-opacity="0" stroke="#010101" d="M79.086,57.276V0.468h10.2v56.808H79.086z"/>
                <path fill="#010101" stroke-width="0" stroke-opacity="0" stroke="#010101" d="M122.695,57.288l-0.042-5.186c-1.962,2.176-3.975,3.737-6.035,4.685c-2.078,0.97-4.48,1.438-7.211,1.438
                    c-3.053,0-5.624-0.601-7.705-1.807c-2.109-1.222-3.638-3.027-4.555-5.394c-0.252-0.587-0.445-1.176-0.569-1.775
                    c-0.136-0.633-0.251-1.344-0.366-2.135c-0.111-0.821-0.15-1.732-0.18-2.761c-0.042-1.033-0.047-2.295-0.047-3.806V18.521h10.204
                    v22.184c0,1.976,0.093,3.457,0.274,4.515c0.183,1.021,0.494,1.947,0.968,2.782c1.191,2.163,3.285,3.25,6.31,3.25
                    c3.835,0,6.468-1.592,7.935-4.8c0.357-0.841,0.612-1.75,0.781-2.765c0.169-1.007,0.239-2.441,0.239-4.309V18.521h10.185v38.768
                    H122.695z"/>
                <path fill="#010101" stroke-width="0" stroke-opacity="0" stroke="#010101" d="M166.721,57.276V35.149c0-1.955-0.086-3.453-0.274-4.482c-0.188-1.036-0.517-1.947-0.98-2.783
                    c-1.176-2.168-3.294-3.26-6.298-3.26c-1.909,0-3.562,0.411-4.94,1.199c-1.384,0.811-2.397,1.995-3.055,3.527
                    c-0.369,0.881-0.633,1.828-0.772,2.835c-0.112,0.988-0.165,2.42-0.165,4.226v20.866H139.92v-38.67h10.315l0.012,5.177
                    c1.971-2.168,3.98-3.734,6.058-4.686c2.06-0.958,4.469-1.428,7.215-1.428c3.047,0,5.608,0.623,7.719,1.88
                    c2.074,1.266,3.583,3.064,4.52,5.381c0.22,0.57,0.388,1.147,0.544,1.747c0.163,0.585,0.288,1.272,0.389,2.042
                    c0.102,0.777,0.173,1.695,0.196,2.743c0.025,1.062,0.054,2.343,0.054,3.837v21.976H166.721z"/>
                <path fill="#010101" stroke-width="0" stroke-opacity="0" stroke="#010101" d="M209.677,58.055l-15.401-21.374v20.596h-10.282V0.472h10.282v33.355h1.104l13.686-15.876l7.742,3.345
                    l-13.173,14.086l15.579,19.34L209.677,58.055z"/>
            </g>
            <g>
                <path fill="#969796" stroke-width="0" stroke-opacity="0" stroke="#969796" d="M228.03,56.218v-6.803l24.015-11.82l-24.015-11.68v-6.95l30.971,15.537v6.342L228.03,56.218z"/>
            </g>
        </g>
    </g>
</svg>
"""
