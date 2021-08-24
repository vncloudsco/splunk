from __future__ import absolute_import
from builtins import object

import mimetypes
from reportlab.platypus.flowables import Flowable

import splunk.pdf.image_utils as imageUtils
import splunk.pdf.pdfgen_utils as pu

logger = pu.getLogger()

MAX_IMAGE_RATIO = 0.95

IMAGE_ALIGNMENT = ['CENTER', 'LEFT', 'RIGHT']

class HtmlMaxHeightMixIn(object):
    def setMaxHeight(self, availHeight):
        self.availHeightValue = availHeight
        if availHeight < 70000:
            if hasattr(self, "canv"):
                if not hasattr(self.canv, "maxAvailHeightValue"):
                    self.canv.maxAvailHeightValue = 0
                self.availHeightValue = self.canv.maxAvailHeightValue = max(
                    availHeight,
                    self.canv.maxAvailHeightValue)
        else:
            self.availHeightValue = availHeight
        if not hasattr(self, "availHeightValue"):
            self.availHeightValue = 0
        return self.availHeightValue

    def getMaxHeight(self):
        if not hasattr(self, "availHeightValue"):
            return 0
        return self.availHeightValue

class HtmlImage(Flowable, HtmlMaxHeightMixIn):

    def __init__(self, imageFileName, width=None, height=None, hAlign='CENTER', mask='auto', mimetype=None, requestSettings=None, **kw):
        self.kw = kw
        if hAlign not in IMAGE_ALIGNMENT:
            hAlign = 'CENTER'
        self.hAlign = hAlign
        self._mask = mask
        self.fileName = imageFileName
        self.mimetype = mimetypes.guess_type(imageFileName)[0]
        self._requestSettings = requestSettings
        self.image = self.getImage()
        if self.image:
            self.imageWidth, self.imageHeight = self.image.getSize()
        if width and not height:
            self.drawWidth = width
            factor = float(width) / self.imageWidth
            self.drawHeight = self.imageHeight * factor
        elif height and not width:
            self.drawHeight = height
            factor = float(height) / self.imageHeight
            self.drawWidth = self.imageWidth * factor
        else:
            self.drawWidth = width or self.imageWidth
            self.drawHeight = height or self.imageHeight

    def wrap(self, availWidth, availHeight):
        availHeight = self.setMaxHeight(availHeight)
        width = min(self.drawWidth, availWidth)
        wfactor = float(width) / self.drawWidth
        height = min(self.drawHeight, availHeight * MAX_IMAGE_RATIO)
        hfactor = float(height) / self.drawHeight
        factor = min(wfactor, hfactor)
        self.dWidth = self.drawWidth * factor
        self.dHeight = self.drawHeight * factor
        logger.debug('event=wrap_html_image draw_width=%s draw_height=%s available_width=%s available_height=%s image_width=%s image_height=%s'
            % (self.drawWidth, self.drawHeight, availWidth, availHeight, self.dWidth, self.dHeight))
        return self.dWidth, self.dHeight

    def getImage(self):
        if self.mimetype == 'image/png':
            image = imageUtils.PngImageReader(self.fileName, requestSettings=self._requestSettings)
        elif self.mimetype == 'image/jpeg':
            image = imageUtils.JpgImageReader(self.fileName, requestSettings=self._requestSettings)
        return image

    def __getattr__(self, attr):
        return getattr(self.image, attr)

    def draw(self):
        if self.image:
            self.canv.drawImage(
                self.image,
                0, 0,
                self.dWidth,
                self.dHeight,
                mask=self._mask,
                preserveAspectRatio=True)

    def identity(self, maxLen=None):
        r = Flowable.identity(self, maxLen)
        return r
