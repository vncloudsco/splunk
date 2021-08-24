from __future__ import absolute_import
__author__ = 'michael'

import logging

from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, SimpleDocTemplate, PageTemplate, BaseDocTemplate
from reportlab import rl_config

import splunk.pdf.pdfgen_svg as ps
import splunk.pdf.pdfgen_table as pt
import splunk.pdf.pdfgen_utils as pu

reportlabLogger = logging.getLogger('reportlab.platypus')
_FUZZ = rl_config._FUZZ

logger = pu.getLogger()


class PDFFrame(Frame):
    def _add(self, flowable, canv, trySplit=0):
        """
         Copied from parent class except height & width validation part
        """
        flowable._frame = self
        flowable.canv = canv  # so they can use stringWidth etc
        try:
            if getattr(flowable, 'frameAction', None):
                flowable.frameAction(self)
                return 1

            y = self._y
            p = self._y1p
            s = 0
            aW = self._getAvailableWidth()
            if not self._atTop:
                s = flowable.getSpaceBefore()
                if self._oASpace:
                    if getattr(flowable, '_SPACETRANSFER', False):
                        s = self._prevASpace
                    s = max(s - self._prevASpace, 0)
            h = y - p - s
            if h > 0:
                w, h = flowable.wrap(aW, h)
            else:
                return 0

            h += s
            y -= h

            # Check the width as well if it's a DivisibleTable instance
            # If the flowable is too big to draw in current frame, 0 will be returned and split() will be called on that flowable
            if y < p - _FUZZ or (isinstance(flowable, pt.DivisibleTable) and w > aW - _FUZZ):
                if not rl_config.allowTableBoundsErrors and ((h > self._aH or w > aW) and not trySplit):
                    from reportlab.platypus.doctemplate import LayoutError

                    raise LayoutError("Flowable %s (%sx%s points) too large for frame (%sx%s points)." % (
                        flowable.__class__, w, h, aW, self._aH))
                return 0
            else:
                #now we can draw it, and update the current point.
                flowable.drawOn(canv, self._x + self._leftExtraIndent, y, _sW=aW-w)
                flowable.canv=canv
                if self._debug: reportlabLogger.debug('drew %s' % flowable.identity())
                s = flowable.getSpaceAfter()
                y -= s
                if self._oASpace: self._prevASpace = s
                if y!=self._y: self._atTop = 0
                self._y = y
                return 1
        finally:
            # sometimes canv/_frame aren't still on the flowable
            for a in ('canv', '_frame'):
                if hasattr(flowable, a):
                    delattr(flowable, a)

    add = _add


def _doNothing(canvas, doc):
    "Dummy callback for onPage"
    pass


class PDFDocTemplate(SimpleDocTemplate):
    def __init__(self, filename, **kw):
        self._title = ""
        self._logoDrawing = None
        self._fontManager = None
        self._settings = None
        self._desc = ""
        self._showHeader = None
        self._showFooter = None
        self._pageElements = None
        self._image = None
        self._requestSettings = None
        SimpleDocTemplate.__init__(self, filename, **kw)

    def setFontManager(self, fontManager):
        self._fontManager = fontManager

    def getFontManager(self):
        return self._fontManager

    def setTitle(self, title):
        self._title = title

    def getTitle(self):
        return self._title

    def setTimestamp(self, timestamp):
        self._timeStamp = timestamp

    def getTimestamp(self):
        return self._timeStamp

    def setLogoSvgString(self, logoSvgString):
        svgRenderer = ps.SVGRenderer(logoSvgString, self._fontManager)
        self._logoDrawing = svgRenderer.getDrawing()

    def setLogoDrawing(self, logoDrawing):
        self._logoDrawing = logoDrawing

    def getLogoDrawing(self):
        return self._logoDrawing

    def setPageSettings(self, showHeader, showFooter, pageElements):
        self._showHeader = showHeader
        self._showFooter = showFooter
        self._pageElements = pageElements

    def getPageSettings(self):
        return self._showHeader, self._showFooter, self._pageElements

    def setRequestSettings(self, requestSettings):
        self._requestSettings = requestSettings

    def getRequestSettings(self):
        return self._requestSettings

    def setDesc(self, description):
        self._desc = description

    def getDesc(self):
        return self._desc

    def setLogoImage(self, image):
        self._image = image

    def getLogoImage(self):
        return self._image

    def build(self, flowables, onFirstPage=_doNothing, onLaterPages=_doNothing, canvasmaker=canvas.Canvas):
        """
        Copied from parent class except using PDFFrame instead of Frame
        """
        self._calc()  # in case we changed margins sizes etc
        # switch to use PDFFrame
        frameT = PDFFrame(self.leftMargin, self.bottomMargin, self.width, self.height, leftPadding=0, bottomPadding=0,
                          rightPadding=4, topPadding=4, id='normal')
        self.addPageTemplates([PageTemplate(id='First', frames=frameT, onPage=onFirstPage, pagesize=self.pagesize),
                               PageTemplate(id='Later', frames=frameT, onPage=onLaterPages, pagesize=self.pagesize)])
        if onFirstPage is _doNothing and hasattr(self, 'onFirstPage'):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self, 'onLaterPages'):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        BaseDocTemplate.build(self, flowables, canvasmaker=canvasmaker)


