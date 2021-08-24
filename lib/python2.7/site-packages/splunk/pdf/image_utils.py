from __future__ import division
from __future__ import absolute_import
from builtins import zip
import logging
import math
import re
import sys
from past.utils import old_div

from reportlab.lib.utils import ImageReader
import reportlab.graphics.shapes as shapes
import reportlab.graphics.renderPDF as renderPDF

import splunk.pdf.pdfgen_utils as pu

logger = pu.getLogger()

class PngImage(shapes.Shape):
    """ PngImage
        This Shape subclass allows for adding PNG images to a PDF without
        using the Python Image Library
    """
    x = 0
    y = 0
    width = 0
    height = 0
    path = None
    clipRect = None

    def __init__(self, x, y, width, height, path, clipRect=None, opacity=1.0, **kw):
        """ if clipRect == None, then the entire image will be drawn at (x,y) -> (x+width, y+height)
            if clipRect = (cx0, cy0, cx1, cy1), all coordinates are in the same space as (x,y), but with (x,y) as origin
                then
                iwidth = image.width, iheight = image.height
                ix0 = (cx0-x)*image.width/width
                ix1 = (cx1-x)*image.width/width
                iy0 = (cy0-y)*image.height/height
                iy1 = (cy1-y)*image.height/height
                the subset of the image, given by (ix0, iy0, ix1, iy0) will be drawn at (x,y)->(x+cx1-cx0, y+cy1-cy0)
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.path = path
        self.opacity = opacity

        if clipRect != None:
            self.origWidth = width
            self.origHeight = height
            self.width = clipRect[2] - clipRect[0]
            self.height = clipRect[3] - clipRect[1]
            self.clipRect = clipRect

    def copy(self):
        new = self.__class__(self.x, self.y, self.width, self.height, self.path, self.clipRect)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        if self.clipRect == None:
            return (self.x, self.y, self.x + self.width, self.y + self.height)
        else:
            return (self.x, self.y, self.x + self.clipRect[2] - self.clipRect[0], self.y + self.clipRect[3] - self.clipRect[1])

    def _drawTimeCallback(self, node, canvas, renderer):
        if not isinstance(renderer, renderPDF._PDFRenderer):
            logger.error("PngImage only supports PDFRenderer")
            return

        requestSettings = {}
        if canvas != None and canvas._doctemplate != None:
            requestSettings = canvas._doctemplate._requestSettings

        image = PngImageReader(self.path, opacity=self.opacity, requestSettings=requestSettings)
        if self.clipRect != None:
            (imageWidth, imageHeight) = image.getSize()
            imageClipRect = (int(math.floor(self.clipRect[0] * imageWidth / self.origWidth)),
                             int(math.floor(self.clipRect[1] * imageHeight / self.origHeight)),
                             int(math.ceil(self.clipRect[2] * imageWidth / self.origWidth)),
                             int(math.ceil(self.clipRect[3] * imageHeight / self.origHeight)))

            image.setClipRect(imageClipRect)
        canvas.drawImage(image, self.x, self.y, width=self.width, height=self.height)

class PngImageReader(ImageReader):
    _format = None
    _isRemote = False
    _clipRect = None

    def __init__(self, fileName, opacity=1.0, requestSettings=None):
        """ fileName is either a local file or a remote file (http)
            clipRect is either None, indicating no clipping, or a 4-tuple of left, top, right, bottom
        """
        # check if the file is remote, if so, download it to a temporary file and reset fileName

        self._isRemote = _getIsRemote(fileName)
        if self._isRemote:
            fileName, self._format = _getRemoteFile(fileName, requestSettings)
        else:
            self._format = _getFormat(fileName)

        if self._format != 'png':
            raise IllegalFormat(fileName, 'PNG')

        if not 0 <= opacity <= 1:
            raise Exception('invalid opacity value %s' % opacity)

        self._dataA = None
        # PNG data
        self._pixelComponentString = None

        import png
        self._pngReader = png.Reader(filename=fileName)
        self._pngReaderInfo = png.Reader(filename=fileName)
        self._pngReaderInfo.preamble()
        self.mode = 'RGB'
        self._width = self._pngReaderInfo.width
        self._height = self._pngReaderInfo.height
        self._filename = fileName
        self._opacity = opacity

    def setClipRect(self, clipRect):
        if clipRect != None:
            if clipRect[2] <= clipRect[0]:
                raise InvalidClipRect(clipRect)
            if clipRect[3] <= clipRect[1]:
                raise InvalidClipRect(clipRect)
            if clipRect[2] > self._width or clipRect[0] < 0:
                raise InvalidClipRect(clipRect)
            if clipRect[3] > self._height or clipRect[1] < 0:
                raise InvalidClipRect(clipRect)

            self._clipRect = clipRect

            clipRectWidth = self._clipRect[2] - self._clipRect[0]
            clipRectHeight = self._clipRect[3] - self._clipRect[1]
            self._width = clipRectWidth
            self._height = clipRectHeight

    def getRGBData(self):
        if self._pixelComponentString is None:
            # rows is an iterator that returns an Array for each row,
            (dataWidth, dataHeight, rows, metaData) = self._pngReader.asDirect()
            dataRect = (0, 0, dataWidth, dataHeight) if self._clipRect == None else self._clipRect

            # the planes of pixels can be 3(RGB) or 4(one extra alpha channel)
            # read https://pythonhosted.org/pypng/png.html for details
            planes = metaData["planes"]
            outputRect = (dataRect[0] * planes, dataRect[1], dataRect[2] * planes, dataRect[3])

            # we need to return a string of bytes: RGBRGBRGBRGBRGB...
            pixelComponentArray = []

            for (rowIdx, row) in enumerate(rows):
                if rowIdx >= outputRect[1] and rowIdx < outputRect[3]:
                    validPixels = row[outputRect[0]:outputRect[2]]
                    # Map RGB/RGBA into RGB strings
                    if planes == 3:
                        # Apply opacity directly if no alpha channel
                        for rgb in zip(validPixels[0::3], validPixels[1::3], validPixels[2::3]):
                            computedRGB = self.computeRGBWithAplha(rgb, self._opacity)
                            pixelComponentArray.extend(computedRGB)
                    elif planes == 4:
                        # Transform RGBA into RGB color
                        # Use algorithm described at http://en.wikipedia.org/wiki/Alpha_compositing#Alpha_blending
                        # Use white (255,255,255) as background color
                        # Zip is costly for huge amount of pixels, but it should be fine for logo and small pictures
                        for rgba in zip(validPixels[0::4], validPixels[1::4], validPixels[2::4], validPixels[3::4]):
                            # rgba = [R,G,B,A]
                            # Apply opacity on top of alpha channel
                            alpha = old_div(float(rgba[3]),  255 * self._opacity)
                            computedRGB = self.computeRGBWithAplha(rgba[0:3], alpha)
                            pixelComponentArray.extend(computedRGB)
            self._pixelComponentString = ''.join(pixelComponentArray)
        return self._pixelComponentString.encode("ISO 8859-1") if sys.version_info >= (3, 0) else self._pixelComponentString

    def computeRGBWithAplha(self, rgb, alpha):
        r = int(((1 - alpha) * 255) + (alpha * rgb[0]))
        g = int(((1 - alpha) * 255) + (alpha * rgb[1]))
        b = int(((1 - alpha) * 255) + (alpha * rgb[2]))
        return [chr(r), chr(g), chr(b)]

    def getTransparent(self):
        # need to override -- or not, not sure when this is used
        return None

class JpgImageReader(ImageReader):
    _format = None
    _isRemote = False

    def __init__(self, fileName,ident=None, requestSettings=None):
        # check if the file is remote, if so, download it to a temporary file and reset fileName
        self._isRemote = _getIsRemote(fileName)
        if self._isRemote:
            fileName, self._format = _getRemoteFile(fileName, requestSettings)
        else:
            self._format = _getFormat(fileName)

        if self._format != 'jpg':
            raise IllegalFormat(fileName, 'JPG')


        ImageReader.__init__(self, fileName, ident)

    def getRGBData(self):
        return ImageReader.getRGBData(self)

    def getTransparent(self):
        return ImageReader.getTransparent(self)


def _getFormat(fileName):
    m = re.search('.([^.]+)$', fileName)
    if m is None:
        return None

    # since the regex matched and there are required
    # characters in the group capture, there must be a index-1 group
    fileSuffix = m.group(1)
    fileSuffix = fileSuffix.lower()

    if fileSuffix == "jpg" or fileSuffix == "jpeg":
        return "jpg"
    elif fileSuffix == "png":
        return "png"

    return None

def _getIsRemote(fileName):
    m = re.search('^(http|https)', fileName)
    if m is None:
        return False
    return True

class IllegalFormat(Exception):
    def __init__(self, fileName, format):
        self.fileName = fileName
        self.format = format

    def __str__(self):
        return "%s is not a %s file" % (self.fileName, self.format)

class CannotAccessRemoteImage(Exception):
    def __init__(self, path, status):
        self.path = path
        self.status = status
    def __str__(self):
        return "Cannot access %s status=%s" % (self.path, self.status)

class InvalidClipRect(Exception):
    def __init__(self, clipRect):
        self.clipRect = clipRect

    def __str__(self):
        return "%s is an invalid clipRect" % str(self.clipRect)

def _getRemoteFile(path, requestSettings):
    ''' uses httplib2 to retrieve @path
    returns tuple: the local path to the downloaded file, the format
    raises exception on any failure
    '''
    import httplib2
    http = httplib2.Http(timeout=60, disable_ssl_certificate_validation=True, proxy_info=None)
    (response, content) = http.request(path)
    if response.status < 200 or response.status >= 400:
        raise CannotAccessRemoteImage(path, response.status)

    format = ''
    content_type = response.get('content-type')
    if content_type == 'image/png':
        format = 'png'
    elif content_type =='image/jpeg':
        format = 'jpg'

    import tempfile
    # preserve the suffix so that the file can be read by ImageReader
    localFile = tempfile.NamedTemporaryFile(suffix="." + format, delete=False)
    localFile.write(content)
    localFile.close()
    return localFile.name, format

if __name__ == '__main__':
    import unittest

    class ImageTest(unittest.TestCase):
        def test_ImageReader_size(self):
            imageReaderJPG = JpgImageReader("svg_image_test.jpg")
            self.assertEquals(imageReaderJPG._width, 399)
            self.assertEquals(imageReaderJPG._height, 470)

            imageReaderPNG = PngImageReader("svg_image_test.png")
            self.assertEquals(imageReaderPNG._width, 250)
            self.assertEquals(imageReaderPNG._height, 183)

            imageReaderPNGClipped = PngImageReader("svg_image_test.png")
            imageReaderPNGClipped.setClipRect((10, 10, 50, 60))
            self.assertEquals(imageReaderPNGClipped._width, 40)
            self.assertEquals(imageReaderPNGClipped._height, 50)

        def test_illegal_image_format(self):
            with self.assertRaises(IllegalFormat):
                imageReader = PngImageReader("test.tiff")

        def test_cannot_access_remote_image(self):
            from future.moves.urllib import error as urllib_error
            with self.assertRaises(urllib_error.HTTPError):
                imageReader = PngImageReader("http://www.splunk.com/imageThatDoesntExist.png")

        def test_invalid_clip_rect(self):
            with self.assertRaises(InvalidClipRect):
                imageReader = PngImageReader("svg_image_test.png")
                imageReader.setClipRect((10, 10, 5, 5))

            with self.assertRaises(InvalidClipRect):
                imageReader = PngImageReader("svg_image_test.png")
                imageReader.setClipRect((0, -4, 30, 40))

            with self.assertRaises(InvalidClipRect):
                imageReader = PngImageReader("svg_image_test.png")
                imageReader.setClipRect((0, 0, 500, 40))

        def test_clipping(self):
            clipRect = (10, 20, 100, 110)
            imageReader = PngImageReader("svg_image_test.png")
            imageReader.setClipRect(clipRect)
            imageData = imageReader.getRGBData()
            imageDataLen = len(imageData)
            self.assertEquals(imageDataLen, (clipRect[2] - clipRect[0]) * (clipRect[3] - clipRect[1]) * 3)

    unittest.main()
