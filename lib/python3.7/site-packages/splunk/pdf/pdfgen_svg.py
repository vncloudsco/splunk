from __future__ import division
from __future__ import absolute_import
# Change the default lxml parsing to not allow imported entities
from past.utils import old_div
from builtins import object
from builtins import zip
from builtins import range

import splunk.lockdownlxmlparsing

import lxml.etree as et
import re
import math

from reportlab.platypus.flowables import Flowable
import reportlab.graphics.shapes as shapes
import reportlab.lib.colors as colors
from reportlab.graphics.shapes import Drawing, Group
import reportlab.graphics.renderPDF as renderPDF

import splunk.pdf.pdfgen_utils as pu
import splunk.pdf.image_utils as image_utils
import splunk.pdf.graphics_utils as graphics_utils

logger = pu.getLogger()

def getSvgImageFromString(svgString, fontManager):
    """ returns a Platypus Flowable object that will draw the SVG that's given
        in the string svgString """
    logger.debug("getSvgImageFromString> svgString: " + str(svgString))

    try:
        svgRenderer = SVGRenderer(svgString, fontManager)
        drawing = svgRenderer.getDrawing()
    except Exception as e:
        errorMsg = "Error parsing SVG. Exception=\"%s\" svgString=\"%s\"" % (str(e), svgString)
        pu.logErrorAndTrace(errorMsg)
        return None

    logger.debug("getSvgImageFromString> drawing: " + str(vars(drawing)))
    logger.debug("getSvgImageFromString> drawing.contents: " + str(repr(drawing.contents)))
    return SVGWrapper(drawing)

def getSvgImageFromFilename(svgFilename, fontManager):
    """ returns a Platypus Flowable object that will draw the SVG that's given
        in the file at svgFilename """
    f = open(svgFilename, 'r')
    svgString = f.read()
    f.close()

    return getSvgImageFromString(svgString, fontManager)

class SVGWrapper(Flowable):
    _debugDrawFrame = False

    def __init__(self, svgDrawing, debugDrawFrame = False):
        self._drawing = svgDrawing
        self._debugDrawFrame = debugDrawFrame

    def wrap(self, availWidth, availHeight):
        (width, height) = self._drawing.wrap(availWidth, availHeight)
        scale = 1.0
        if width > availWidth:
            scale = old_div(availWidth, width)
        if scale * height > availHeight:
            scale = old_div(availHeight, height)

        self._drawing.width = self._drawing.minWidth() * scale
        self._drawing.height = self._drawing.height * scale
        self._drawing.scale(scale, scale)
        return self._drawing.wrap(availWidth, availHeight)

    def draw(self):
        if self._debugDrawFrame:
            self.canv.rect(0, 0, self._drawing.width * self._drawing.renderScale, self._drawing.height * self._drawing.renderScale)
        self._drawing.drawOn(self.canv, 0, 0)

class SVGRenderer(object):
    _svgString=None
    _svgNode=None
    _drawing=None
    _width=0
    _height=0
    _clipPaths = {}
    _ignoreElements = ["highcharts-tooltip", "highcharts-tracker"]
    _debugDraw = False
    _fontManager = None
    _viewBoxClipPath = None
    _currentlyRenderingClipPath = False

    _attributeMapLineShape = {
        "stroke": {"pdfkey": "strokeColor", "type": "color", "default": "none"},
        "stroke-width": {"pdfkey": "strokeWidth", "type": "float", "default": 0.0},
        "stroke-opacity": {"pdfkey": "strokeOpacity", "type": "float", "default": 1.0},
        "stroke-dasharray": {"pdfkey": "strokeDashArray", "type": "array", "element": int}
        }
    _attributeMapSolidShape = {
        "fill": {"pdfkey": "fillColor", "type": "color", "default": "none"},
        "fill-opacity": {"pdfkey": "fillOpacity", "type": "float", "default": 1.0}
        }
    _attributeMapRect = {
        "x": {"pdfkey": "x", "type": "float"},
        "y": {"pdfkey": "y", "type": "float"},
        "width": {"pdfkey": "width", "type": "float"},
        "height": {"pdfkey": "height", "type": "float"},
        "rx": {"pdfkey": "rx", "type": "float"},
        "ry": {"pdfkey": "ry", "type": "float"}
        }
    _attributeMapPolygon = {
        "points": {"pdfkey": "points", "type": "point", "element": float}
        }

    _attributeMapPolyline = {
        "points": {"pdfkey": "points", "type": "point", "element": float}
        }

    _attributeMapLine = {
        "x1": {"pdfkey": "x1", "type": "float"},
        "y1": {"pdfkey": "y1", "type": "float"},
        "x2": {"pdfkey": "x2", "type": "float"},
        "y2": {"pdfkey": "y2", "type": "float"},
        }

    _attributeMapCircle = {
        "cx": {"pdfkey": "cx", "type": "float"},
        "cy": {"pdfkey": "cy", "type": "float"},
        "r": {"pdfkey": "r", "type": "float"}
        }

    _attributeMapPath = {
        }

    _attributeMapText = {
        "x": {"pdfkey": "x", "type": "float"},
        "y": {"pdfkey": "y", "type": "float"},
        "text-anchor": {"pdfkey": "textAnchor", "type": "string"},
        "font-size": {"pdfkey": "fontSize", "type": "string"},
        "color": {"pdfkey": "fillColor", "type": "color", "default": "none"},
        "fill": {"pdfkey": "fillColor", "type": "color", "default": "none"}
        }

    _attributeMapImage = {
        "x": {"pdfkey": "x", "type": "float"},
        "y": {"pdfkey": "y", "type": "float"},
        "width": {"pdfkey": "width", "type": "float"},
        "height": {"pdfkey": "height", "type": "float"},
        "{http://www.w3.org/1999/xlink}href": {"pdfkey": "path", "type": "string"},
        "opacity": {"pdfkey": "opacity", "type": "float"}
        }

    _colorOpacityMap = {
        "strokeColor": "strokeOpacity",
        "fillColor": "fillOpacity"
        }

    _opacityOverrideMap = {
        "stroke": "strokeOpacity",
        "fill": "fillOpacity"
        }

    #
    #
    #
    def __init__(self, svgString, fontManager):
        logger.debug("SVGRenderer::__init__> svgString = " + svgString)

        self._viewBox = None
        self._svgString = svgString
        self._fontManager = fontManager
        self._svgNode = et.fromstring(self._svgString)

        self.initDimension()
        # initialize attribute maps
        import itertools
        self._attributeMapSolidShape = dict(itertools.chain(self._attributeMapSolidShape.items(), self._attributeMapLineShape.items()))
        self._attributeMapRect       = dict(itertools.chain(self._attributeMapRect.items(), self._attributeMapSolidShape.items()))
        self._attributeMapPolygon    = dict(itertools.chain(self._attributeMapPolygon.items(), self._attributeMapSolidShape.items()))
        self._attributeMapPolyline   = dict(itertools.chain(self._attributeMapPolyline.items(), self._attributeMapSolidShape.items()))
        self._attributeMapLine       = dict(itertools.chain(self._attributeMapLine.items(), self._attributeMapSolidShape.items()))
        self._attributeMapCircle     = dict(itertools.chain(self._attributeMapCircle.items(), self._attributeMapSolidShape.items()))
        self._attributeMapPath       = dict(itertools.chain(self._attributeMapPath.items(), self._attributeMapSolidShape.items()))

        # buildup function map
        self.renderFunctionMap = {
            "{http://www.w3.org/2000/svg}svg": self.renderElementSvg,
            "{http://www.w3.org/2000/svg}g": self.renderElementGroup,
            "{http://www.w3.org/2000/svg}defs": self.renderElementDefs,
            "{http://www.w3.org/2000/svg}clippath": self.renderElementClipPath,
            "{http://www.w3.org/2000/svg}rect": self.renderElementRect,
            "{http://www.w3.org/2000/svg}polygon": self.renderElementPolygon,
            "{http://www.w3.org/2000/svg}polyline": self.renderElementPolyline,
            "{http://www.w3.org/2000/svg}circle": self.renderElementCircle,
            "{http://www.w3.org/2000/svg}text": self.renderElementText,
            "{http://www.w3.org/2000/svg}path": self.renderElementPath,
            "{http://www.w3.org/2000/svg}image": self.renderElementImage,
            "{http://www.w3.org/2000/svg}line": self.renderElementLine
        }

        # elements that can be used as clip path
        self.renderClipPathFunctionMap = {
            "{http://www.w3.org/2000/svg}rect": self.renderElementRect,
            "{http://www.w3.org/2000/svg}polygon": self.renderElementPolygon,
            "{http://www.w3.org/2000/svg}circle": self.renderElementCircle,
            "{http://www.w3.org/2000/svg}path": self.renderElementPath
        }

    def initDimension(self):
        if "style" in self._svgNode.attrib:
            styleMap = self._getStyleMap(self._svgNode.get("style"))
            if "width" in styleMap:
                self._width = int(styleMap.get("width")[0].replace("px", ""))
            if "height" in styleMap:
                self._height = int(styleMap.get("height")[0].replace("px", ""))

        if "width" in self._svgNode.attrib and not self._width:
            widthStr = self._svgNode.get("width")
            if len(widthStr) > 0:
                self._width = int(widthStr)

        if "height" in self._svgNode.attrib and not self._height:
            heightStr = self._svgNode.get("height")
            if len(heightStr) > 0:
                self._height = int(heightStr)

        if not self._width:
            self._width = 600 # TODO: allow for configuration of default
            logger.info("SVGRenderer::__init__> width is undefined")

        if not self._height:
            self._height = 400 # TODO: allow for configuration of default
            logger.warning("SVGRenderer::__init__> height is undefined")

        logger.debug("SVGRenderer::__init__> width = " + str(self._width) + " height = " + str(self._height))

    # TODO: unit testing:
    #  1) verify that a non-None drawing is returned
    def getDrawing(self):
        """ returns reportlab graphics.shapes.drawing """
        self._drawing = Drawing(width = self._width, height = self._height)
        self.renderElement(element = self._svgNode, group = self._drawing)
        return self._drawing

    # TODO: unit testing:
    #   1) verify that each known element type is rendered
    #   2) verify that unknown element types are not rendered
    def renderElement(self, element, group, isClipPath=0):
        if "visibility" in element.attrib:
            if element.attrib["visibility"] == "hidden":
                return
        if "display" in element.attrib:
            if element.attrib["display"] == "none":
                return

        elemTag = element.tag.lower()
        elemClass = element.get("class")
        logger.debug("SVGRenderer::renderElement> tag = " + str(elemTag) + " class = " + str(elemClass))

        if elemClass in self._ignoreElements:
            logger.debug("SVGRenderer::renderElement> ignoring element, class = " + str(elemClass))
            return

        renderFunctionMap = self.renderClipPathFunctionMap if isClipPath else self.renderFunctionMap

        if elemTag in renderFunctionMap:
            renderElementFunction = renderFunctionMap[elemTag]
            clipPath = self._getClipPath(element)
            if clipPath:
                # build a new group for each clip path and target element
                for path in clipPath:
                    clippedGroup = Group()
                    clippedGroup.add(self._applyWrappingTransformIfNeeded(element, path))
                    group.add(clippedGroup)
                    logger.debug("SVGREnderer::renderElement> render element %s with clipGroup" % str(elemTag))
                    renderElementFunction(element, clippedGroup, isClipPath)
            else:
                renderElementFunction(element, group, isClipPath)
        else:
            logger.debug("SVGREnderer::renderElement> unknown tag %s isCliPath %s " % (str(elemTag), isClipPath))


    def _getClipPath(self, element):
        """
         Get clip paths from clip path definitions if it's defined in element attributes
        :param element:
        :return:
        """
        ret = None
        if "clip-path" in element.attrib:
            clipPathUrl = element.attrib["clip-path"]
            logger.debug("SVGRenderer::renderElementGroup> clipPathUrl: " + clipPathUrl)
            (dummy, sep, keyNugget) = clipPathUrl.partition("#")
            logger.debug("SVGRenderer::renderElementGroup> keyNugget: " + keyNugget)
            (key, sep, dummy) = keyNugget.partition(")")
            logger.debug("SVGRenderer::renderElementGroup> key: " + key)
            if key in self._clipPaths:
                ret = self._clipPaths[key]

        return ret

    #
    #
    #
    def renderElementSvg(self, element, group, isClipPath=0):
        logger.debug("SVGRenderer::renderElementSvg> num children = " + str(len(element)))


        # SVG coordinate system is top-left
        # PDF coordinate system is bottom-left
        # transform the entire drawing so that we can place all of our elements using SVG coordinates

        coordinateMappingWrapper = Group()
        coordinateMappingWrapper.translate(0, self._height)
        coordinateMappingWrapper.scale(1, -1)
        group.add(coordinateMappingWrapper)

        # get the viewBox -- only draw within the box
        viewBoxString = element.attrib.get("viewBox")
        if viewBoxString != None:
            # convert from "x0 y0 x1 y1" to [x0, y0, x1, y1]
            viewBoxStringArray = viewBoxString.split(" ")
            self._viewBox = [float(x) for x in viewBoxStringArray]
            # NOTE: even though we want to consider the viewBox outside of any transformations
            #       we don't need to map by the transform in the coordinateMappingWrapper since
            #       that will end up being the identity for a non-rotated rectangle
        else:
            self._viewBox = [0, 0, self._width, self._height]

        logger.debug("SVGRenderer::renderElementSvg> viewBox: %s" % self._viewBox)

        # always build the clip path for entire viewbox
        viewBoxClipPath = self._buildClipPathRect(self._viewBox)

        # add viewBox clip path
        coordinateMappingWrapper.add(viewBoxClipPath)
        self._renderChildren(coordinateMappingWrapper, element)

    #
    #
    #
    def renderElementGroup(self, element, group, isClipPath=0):
        logger.debug("SVGRenderer::renderElementGroup> num children = " + str(len(element)))

        newGroup = Group()
        self.applyTransform(element, newGroup)
        group.add(newGroup, name=element.get("class"))

        self._renderChildren(newGroup, element, isClipPath)

    def renderElementDefs(self, element, group, isClipPath=0):
        """
            Render pre defined elements.
            These elements will not be appended in render tree unless other element use them
        :param element:
        :param group:
        :param isClipPath:
        :return:
        """
        logger.debug("SVGRenderer::renderElementDefs> num children = " + str(len(element)))

        tempGroup = Group() # temp group so that they will be append in render tree
        self.applyTransform(element, tempGroup)
        self._renderChildren(tempGroup, element, isClipPath)

    def _renderChildren(self, group, parentElement, isClipPath=0):
        for child in parentElement:
            self.renderElement(child, group, isClipPath=isClipPath)

    def _newClipPath(self):
        clipPath = shapes.Path()
        clipPath.setProperties({
            "isClipPath": True,
            "fillColor": None,
            "fillOpacity": 1,
            "strokeColor": None,
            "strokeOpacity": 0,
            "strokeWidth": 0})
        return clipPath

    def _buildClipPathRect(self, rect):
        """ builds a clip path shape that covers the specified rect
            rect is given in the tuple (x0 y0 x1 y1)
        """
        clipPath = self._newClipPath()
        clipPath.moveTo(rect[0], rect[1])
        clipPath.lineTo(rect[2], rect[1])
        clipPath.lineTo(rect[2], rect[3])
        clipPath.lineTo(rect[0], rect[3])
        clipPath.closePath()
        return clipPath

    def _buildClipPathCircle(self, cx, cy, r):
        """
            Use shapes.Path build a circle path.
        :param x: center x
        :param y: center y
        :param r: radius
        :return:
        """
        clipPath = self._newClipPath()
        # oops.. no draw circle function that i can use..let's simulate one
        clipPath.moveTo(cx + r, cy)
        # separate into 180 segments
        for i in range(180):
            x = math.cos(math.radians(i * 2)) * r + cx
            y = math.sin(math.radians(i * 2)) * r + cy
            clipPath.lineTo(x, y)
        clipPath.closePath()
        return clipPath

    def _buildClipPathPolygon(self, points):
        """
            Use shapes.Path build a polygon path
        :param points: [x1,y1,x2,y2 ...]
        :return:
        """
        clipPath = self._newClipPath()
        sPoint = points[:2]
        points = points[2:]
        clipPath.moveTo(sPoint[0], sPoint[1])
        for (x, y) in zip(points[0::2], points[1::2]):
            clipPath.lineTo(x, y)
        clipPath.closePath()
        return clipPath
    #
    #
    #
    def renderElementClipPath(self, element, group, isClipPath=0):
        # need to convert the contained shape into a path and then store the path
        #  in the clippath dictionary
        tempGroup = Group()
        # indicate we're rendering clip path element, set isClipPath to 1
        self._renderChildren(tempGroup, element, isClipPath=1)
        # register the list of clip path
        self._clipPaths[element.attrib["id"]] = tempGroup.getContents()

        logger.debug("SVGRenderer::renderElementClipPath> self._clipPaths: " + str(self._clipPaths))

    # TODO: unit testing:
    #    1) check 'none', '#XXXXXX', '#XXX' and 'rgb(r,g,b)'
    def _parseColor(self, colorString):
        logger.debug("SVGRenderer::parseColor> colorString: " + colorString)

        if 'none' in colorString:
            return None

        # fix special case: #XXX, e.g. #FFF means #FFFFFF
        if len(colorString) == 4 and colorString.startswith('#'):
            colorString = '#' + colorString[1]*2 + colorString[2]*2 + colorString[3]*2

        try:
            color = colors.toColor(colorString)
        except ValueError as e:
            logger.warning("SVGRenderer::parseColor> toColor for " + colorString + " raised " + str(e))
            color = colors.black

        return color

    # TODO: unit testing:
    #   1) check different attribute maps with 'empty' element, verify default value
    def _getAttributes(self, element, attributeMap):
        """ Extract, convert and provide defaults for attributes provided in the element node.
            Iterate through the attributes in the attributeMap. If an attribute exists in the svg node,
            convert the string to the type provided in the mapping, and add the attribute value to the
            output pdf dictionary under the key provided by the mapping. If the attribute does not exist
            in the svg node, output the default value as provided in the mapping

            attributeMap needs to be in the format:
            { svg-attribute-key-1: { "pdfkey": pdf-attribute-key, "type": attribute-type, "default": default-value},
              svg-attribute-key-2: {...} ... }
        """

        attributes = {}

        svgAttributes = element.attrib

        # parse style attributes first
        if "style" in svgAttributes:
            styleMap = self._getStyleMap(svgAttributes.get("style"))
            for key, v in styleMap.items():
                # ignore attributes that starts with "-", for example "-hc-text-stroke"
                if not key.startswith("-"):
                    svgAttributes[key] = v[0]

        for svgKey, attribInfo in attributeMap.items():
            value = None
            strValue = None

            if svgKey in svgAttributes:
                strValue = svgAttributes[svgKey]

            type = attribInfo["type"]
            if type == "float":
                if strValue is None or len(strValue) == 0:
                    if "default" in attribInfo:
                        value = attribInfo["default"]
                    else:
                        value = 0.0
                else:
                    value = float(strValue.replace("px", ""))
            elif type == "color":
                if strValue is None or len(strValue) == 0:
                    strValue = 'none'
                value = self._parseColor(strValue)
            elif type == "string":
                if strValue is None or len(strValue) == 0:
                    strValue = None
                else:
                    value = strValue
            elif type == "array":
                if strValue is not None and len(strValue) > 0 and strValue != 'none':
                    convert = attribInfo['element']
                    value = [convert(n.strip()) for n in strValue.split(',')]
            elif type == "point":
                # transform string "x1,y1 x2,y2" into a flatten array [x1,y1,x2,y2]
                if strValue is not None and len(strValue) > 0 and strValue != 'none':
                    value = []
                    convert = attribInfo['element']
                    for p in strValue.split(' '):
                        pair = p.split(',')
                        value.append(convert(pair[0].strip()))
                        value.append(convert(pair[1].strip()))

            if value is not None:
                attributes[attribInfo["pdfkey"]] = value

        # handle opacities
        attributes = self._opacityMapping(attributes, svgAttributes)

        return attributes

    # TODO: Unit testing:
    # 1) verify mapping for all members of colorOpacityMap
    def _opacityMapping(self, attributes, svgAttributes):
        # For color attributes where an opacity can be specified inline via the rgba(...) syntax, that opacity should trump the
        # associated opacity attribute.  For example if fill is 'rgba(0, 0, 0, 0.5)' and fill-opacity is 0.2,
        # the computed opacity should be 0.5.
        for opacityOverrideKey in self._opacityOverrideMap:
            if opacityOverrideKey in svgAttributes and re.match('^\s*rgba', svgAttributes[opacityOverrideKey]):
                del attributes[self._opacityOverrideMap[opacityOverrideKey]]

        for colorKey in self._colorOpacityMap:
            if colorKey in attributes and self._colorOpacityMap[colorKey] in attributes:
                if attributes[colorKey] is not None and attributes[colorKey] != 'none':
                    logger.debug("SVGRenderer::_opacityMapping> colorKey: " + colorKey + ", color = " + str(attributes[colorKey]))
                    color = attributes[colorKey]

                    origColor = str(color)
                    opacity = attributes[self._colorOpacityMap[colorKey]]
                    attributes[colorKey].alpha = color.alpha * opacity
                    logger.debug("SVGRenderer::_opacityMapping> modifying " + colorKey + " with opacity: " + str(opacity) + " from: " + str(origColor) + " to: " + str(attributes[colorKey]))
        return attributes

    #
    #
    #
    def renderElementRect(self, element, group, isClipPath=0):
        attr = self._getAttributes(element, self._attributeMapRect)

        if attr["height"] == 0.0:
            attr["height"] = 0.1
        if attr["width"] == 0.0:
            attr["width"] = 0.1

        # if strokeColor is missing from the attr dictionary, the reportlab shape rendering will still render a stroke
        if "strokeColor" not in attr:
            attr["strokeColor"] = colors.Color(0, 0, 0, 0)
            attr["strokeOpacity"] = 0.0
        if "fillColor" not in attr:
            attr["fillColor"] = colors.Color(0, 0, 0, 0)
            attr["fillOpacity"] = 0.0

        logger.debug("SVGRenderer::renderElementRect> attributes: " + str(attr))

        if isClipPath:
            # rect with round corner(rx,ry is not supported)
            rect = self._buildClipPathRect(
                (attr["x"], attr["y"], attr["x"] + attr["width"], attr["y"] + attr["height"]))
        else:
            #TODO: add rx,ry rules (http://www.w3.org/TR/SVG/shapes.html#RectElementRXAttribute)
            rect = shapes.Rect(**attr)
        group.add(self._applyWrappingTransformIfNeeded(element, rect))

    #
    #
    #
    def renderElementPolygon(self, element, group, isClipPath=0):
        attr = self._getAttributes(element, self._attributeMapPolygon)
        if "strokeColor" not in attr:
            attr["strokeColor"] = colors.Color(0, 0, 0, 0)
            attr["strokeOpacity"] = 0.0
        if "fillColor" not in attr:
            attr["fillColor"] = colors.Color(0, 0, 0, 0)
            attr["fillOpacity"] = 0.0

        logger.debug("SVGRenderer::renderElementPolygon> attributes: " + str(attr))

        if isClipPath:
            polygon = self._buildClipPathPolygon(attr["points"])
        else:
            polygon = shapes.Polygon(**attr)
        group.add(self._applyWrappingTransformIfNeeded(element, polygon))

    #
    #
    #
    def renderElementLine(self, element, group, isClipPath=0):
        attr = self._getAttributes(element, self._attributeMapLine)
        if "strokeColor" not in attr:
            attr["strokeColor"] = colors.Color(0, 0, 0, 0)
            attr["strokeOpacity"] = 0.0
        if "fillColor" not in attr:
            attr["fillColor"] = colors.Color(0, 0, 0, 0)
            attr["fillOpacity"] = 0.0

        logger.debug("SVGRenderer::_attributeMapLine> attributes: " + str(attr))
        if not ("x1" in attr and "y1" in attr and "x2" in attr and "y2" in attr):
            logger.error("missing coordinate attributes for svg <line>")
            return
        x1 = attr["x1"]
        y1 = attr["y1"]
        x2 = attr["x2"]
        y2 = attr["y2"]
        # remove coordinate attributes as they're explicitly defined in constructor
        for key in ["x1", "y1", "x2", "y2"]:
            del attr[key]
        line = shapes.Line(x1, y1, x2, y2, **attr)
        group.add(self._applyWrappingTransformIfNeeded(element, line))


    #
    #
    #
    def renderElementPolyline(self, element, group, isClipPath=0):
        attr = self._getAttributes(element, self._attributeMapPolyline)
        if "strokeColor" not in attr:
            attr["strokeColor"] = colors.Color(0, 0, 0, 0)
            attr["strokeOpacity"] = 0.0
        if "fillColor" not in attr:
            attr["fillColor"] = colors.Color(0, 0, 0, 0)
            attr["fillOpacity"] = 0.0

        logger.debug("SVGRenderer::_attributeMapPolyline> attributes: " + str(attr))

        polyline = shapes.PolyLine(**attr)
        group.add(self._applyWrappingTransformIfNeeded(element, polyline))


    #
    #
    #
    def renderElementCircle(self, element, group, isClipPath=0):
        attr = self._getAttributes(element, self._attributeMapCircle)

        # if strokeColor is missing from the attr dictionary, the reportlab shape rendering will still render a stroke
        if "strokeColor" not in attr:
            attr["strokeColor"] = colors.Color(0, 0, 0, 0)
            attr["strokeOpacity"] = 0.0
        if "fillColor" not in attr:
            attr["fillColor"] = colors.Color(0, 0, 0, 0)
            attr["fillOpacity"] = 0.0

        logger.debug("SVGRenderer::renderElementCircle> attributes: " + str(attr))
        if isClipPath:
            circle = self._buildClipPathCircle(attr["cx"], attr["cy"], attr["r"])
        else:
            circle = shapes.Circle(**attr)
        group.add(self._applyWrappingTransformIfNeeded(element, circle))

    #
    #
    #
    def renderElementText(self, element, group, isClipPath=0):
        attr = self._getAttributes(element, self._attributeMapText)

        logger.debug("SVGRenderer::renderElementText> attributes='%s'" % attr)

        # get font-size from styleMap or element attribute
        fontSizeStr = attr.get("fontSize")
        if fontSizeStr is not None:
            sizes = re.findall("[0-9.]+", fontSizeStr)
            if len(sizes) > 0:
                attr["fontSize"] = float(sizes[0])

        logger.debug("SVGRenderer::renderElementText> attributes: " + str(attr))

        # get text
        elementText = None
        if element.text and len(element.text) > 0:
            elementText = element.text.strip(" \n\t\r")
        if elementText is None and len(element) < 1:
            logger.warning("SVGRenderer::renderElementText> no text for element = %s" % et.tostring(element))
            return

        # there may be transformation applied to the svg text element
        # we need to wrap the pdf element in a group in order to perform the transformation
        # we will want all transformation to occur within the pdf element group
        # therefore, move the absolute positioning into the group transformation
        tx = attr["x"]
        ty = attr["y"]
        attr["x"] = 0
        attr["y"] = 0
        attr['fontManager'] = self._fontManager

        wrapperGroup = Group()
        if "transform" in element.attrib:
            self.applyTransform(element, wrapperGroup)
        wrapperGroup.translate(tx, ty)

        # since we are scaling the entire drawing by 1,-1 to fix the coordinate system mapping,
        #  we need to flip the text so that it isn't upside-down
        sx = 1
        sy = -1
        wrapperGroup.scale(sx, sy)

        if elementText:
            textShape = FontManagedString(text=elementText, **attr)
            # inversion madness! since we're flipping the text, we need to shift by fontsize, but only when the text is clipped to the bottom edge
            if 'dominant-baseline' in element.attrib and element.attrib['dominant-baseline'] == 'text-before-edge':
                textShape.y -= textShape.fontSize
            wrapperGroup.add(textShape)

        # iterate over child tspan elements
        for child in element:
            text = child.text
            logger.debug("SVGRenderer::renderElementText> child attrib: " + str(child.attrib))

            # handle relative y offsets
            if "dy" in child.attrib:
                yVal = attr["y"]
                # since the wrapperGroup has a scale factor of sy applied to the y coordinate
                #  reverse that if necessary
                if sy != 0.0:
                    inv_sy = 1.0 / sy
                else:
                    inv_sy = 0.0
                yVal = yVal + inv_sy * self._getFloatValueFromText(child.attrib["dy"])
                attr["y"] = yVal

            logger.debug("SVGRenderer::renderElementText> final attr: " + str(attr))

            textShape = FontManagedString(text = text, **attr)
            wrapperGroup.add(textShape)
            logger.debug("SVGRenderer::renderElementText> text=%s wrapperGroup.transform=%s" % (text, wrapperGroup.transform))


        group.add(wrapperGroup)

    def _getStyleMap(self, styleStr):
        styleMap = {}
        if styleStr is not None:
            styleComponents = styleStr.split(";")
            for styleComponent in styleComponents:
                styleKey, sep, styleDataStr = styleComponent.partition(":")
                styleKey = styleKey.strip()

                styleData = []
                if styleKey in ['font-family']:
                    styleDataTemp = styleDataStr.split(",")
                    for styleDataItem in styleDataTemp:
                        styleData.append(styleDataItem.strip())
                else:
                    styleData.append(styleDataStr.strip())

                if len(styleKey) > 0 and len(styleData) > 0:
                    styleMap[styleKey] = styleData
        return styleMap
    #
    #
    #
    def _getFloatValueFromText(self, text):
        items = re.findall("[-]?[\d]+\.[\d]*|[-]?[\d]+", text)
        if len(items) == 0:
            return None
        return float(items[0])

    # TODO: Add unit testing:
    #   2) try out variety of M, L, Z
    #   3) test A
    _pathExplicitlyClosed = False
    def renderElementPath(self, element, group, isClipPath=0):
        forceClosedPath = False # we will forcibly close the path if a fill is set and the path is not closed explicitly

        attributes = self._getAttributes(element, self._attributeMapPath)
        # if strokeColor is missing from the attr dictionary, the reportlab shape rendering will still render a stroke
        if "strokeColor" not in attributes:
            attributes["strokeColor"] = colors.Color(0, 0, 0, 0)
            attributes["strokeOpacity"] = 0.0
        if "fillColor" not in attributes:
            attributes["fillColor"] = colors.Color(0, 0, 0, 0)
            attributes["fillOpacity"] = 0.0
        elif attributes["fillColor"] != "none":
            forceClosedPath = True

        logger.debug("SVGRenderer::renderElementPath> attributes: " + str(attributes))

        pathCommandStr = element.get("d")
        if pathCommandStr is None:
            logger.warn("SVGRenderer::renderElementPath> path has no \"d\" attribute, ignoring")
            return

        # pathCommandStr is like "M X0 Y0 L X1 Y1 L X2 Y2 Z"
        #                    or  "M X0 Y0 L X1 Y1" or "M X0 Y0 L X1 Y1 ... Xn Yn"
        #                    or  "M X0 Y0 A rx ry x-axis-rotation large-arc-flag sweep-flag x y"
        # M is moveTo, L is lineTo, Z or z is close-path, A is elliptic-arc-to

        # split up the pathCommandStr based on entities that we accept as either commands or arguments
        #  sample SVG documents reveal that sometimes these are split by spaces, sometimes by commas,
        #  and in some instances a sequence of argument command argument is not split by anything at all
        pathCommands = re.findall("[a-zA-Z]|[+-]?\d+(?:\.\d+)?(?:[eE][+-]\d+)?", pathCommandStr)
        logger.debug("SVGRenderer::renderElementPath> pathCommandStr: " + str(pathCommandStr))

        path = shapes.Path(isClipPath=isClipPath, **attributes)

        pathCommandFunctions = {
            "M": self._renderElementPath_MoveTo,
            "m": self._renderElementPath_MoveToRelative,
            "L": self._renderElementPath_LineTo,
            "l": self._renderElementPath_LineToRelative,
            "Z": self._renderElementPath_ClosePath,
            "z": self._renderElementPath_ClosePath,
            "A": self._renderElementPath_Arc,
            "C": self._renderElementPath_Curve,
            "c": self._renderElementPath_CurveRelative,
            "H": self._renderElementPath_HorizLineTo,
            "h": self._renderElementPath_HorizLineToRelative,
            "V": self._renderElementPath_VertLineTo,
            "v": self._renderElementPath_VertLineToRelative
            }

        self._pathExplicitlyClosed = False

        for (i, pathCommand) in enumerate(pathCommands):

            # only process if a command and not an argument
            if re.match("[a-zA-Z]", pathCommand):

                # determine the number of arguments til next command
                nextCommandIndex = len(pathCommands)
                for p in range(1, len(pathCommands) - i):
                    if re.match("[a-zA-Z]", pathCommands[i+p]):
                        nextCommandIndex = i + p
                        break
                arguments = pathCommands[i+1:nextCommandIndex]
                logger.debug("SVGRenderer::renderElementPath> command: " + str(pathCommand) + ", arguments: " + str(arguments))

                # execute the pathCommand by indirecting through the pathCommandFunctions map
                if pathCommand in pathCommandFunctions:
                    numArguments = len(arguments)
                    addPathCommand = True
                    while addPathCommand:
                        try:
                            argsUsed = pathCommandFunctions[pathCommand](path, arguments[len(arguments)-numArguments:], group)
                            numArguments = numArguments - argsUsed
                            if numArguments == 0:
                                addPathCommand = False
                        except self.InvalidArgumentCount as e:
                            logger.warning("SVGRenderer::renderElementPath> exception: %s" % str(e))
                            break
                        except self.InvalidArguments as e:
                            logger.warning("SVGRenderer::renderElementPath> exception parsing path command: %s" % str(e))
                            break
                else:
                    logger.warning("SVGRenderer::renderElementPath> unhandled path command for " + pathCommandStr + " at pathCommand index " + str(i))

        # add the path to the parent group if we added at least one point
        if len(path.points) > 0:
            # fault-tolerance:
            #  if the final point is the same as the starting point, call closePath()
            if len(path.points) > 4 and self._pathExplicitlyClosed == False:
                if (path.points[0], path.points[1]) == (path.points[len(path.points) - 2], path.points[len(path.points) - 1]) or forceClosedPath:
                    path.closePath()


            logger.debug("SVGRenderer::renderElementPath> points: " + str(path.points) + " operators: " + str(path.operators))
            group.add(self._applyWrappingTransformIfNeeded(element, path))

    class InvalidArgumentCount(Exception):
        def __init__(self, command, validArgumentCount, argumentCount):
            self.command = command
            self.validArgumentCount = validArgumentCount
            self.argumentCount = argumentCount

        def __str__(self):
            return "pathCommand %s requires at least %s arguments; %s arguments provided" % (self.command, self.validArgumentCount, self.argumentCount)

    class InvalidArguments(Exception):
        def __init__(self, command, message, arguments):
            super(Exception, self).__init__(message)
            self.command = command
            self.arguments = arguments

        def __str__(self):
            return "pathCommand %s failed with arguments %s with message %s" % (self.command, self.arguments, self.args[0])

    #
    #
    #
    def _renderElementPath_ClosePath(self, path, arguments, group):
        """ ClosePath command string: Z """
        logger.debug("SVGRenderer::_renderElementPath_ClosePath> closing path")
        path.closePath()
        self._pathExplicitlyClosed = True
        return 0

    #
    #
    #
    def _renderElementPath_MoveTo(self, path, arguments, group):
        """ MoveTo command string: M X Y """

        if len(arguments) < 2:
            raise self.InvalidArgumentCount("M", 2, len(arguments))
        else:
            x, y = self._getPointFromArguments(arguments[:2])
            path.moveTo(x, y)
        return 2

    #
    #
    #
    def _renderElementPath_MoveToRelative(self, path, arguments, group):
        """ MoveTo command string: m dX dY """
        if len(arguments) < 2:
            raise self.InvalidArgumentCount("m", 2, len(arguments))
        else:
            x0, y0 = self._renderElementPath_GetCurrentPoint(path)
            x, y = self._getPointFromArgumentsRelative(arguments[:2], x0, y0)
            path.moveTo(x, y)
        return 2

    #
    #
    #
    def _renderElementPath_LineTo(self, path, arguments, group):
        """ LineTo command string: L X0 Y0 ... Xn Yn """
        if len(arguments) < 2:
            raise self.InvalidArgumentCount("L", 2, len(arguments))
        else:
            numPoints = old_div(len(arguments),2)
            for i in range(numPoints):
                x, y = self._getPointFromArguments(arguments[i*2:i*2 + 2])
                path.lineTo(x, y)
            return numPoints * 2
    #
    #
    #
    def _renderElementPath_LineToRelative(self, path, arguments, group):
        """ LineTo command string: l X0 Y0 ... Xn Yn """
        if len(arguments) < 2:
            raise self.InvalidArgumentCount("l", 2, len(arguments))
        else:
            x0, y0 = self._renderElementPath_GetCurrentPoint(path)

            numPoints = old_div(len(arguments),2)
            for i in range(numPoints):
                x, y = self._getPointFromArgumentsRelative(arguments[i*2:i*2 + 2], x0, y0)
                path.lineTo(x, y)
            return numPoints * 2
    #
    #
    #
    def _renderElementPath_HorizLineTo(self, path, arguments, group):
        """ HorizLineTo command string: H X0 Xn """
        x0, y0 = self._renderElementPath_GetCurrentPoint(path)

        if len(arguments) < 1:
            raise self.InvalidArgumentCount("H", 1, len(arguments))
        else:
            numPoints = len(arguments)
            for i in range(numPoints):
                x = float(arguments[i])
                path.lineTo(x, y0)
        return len(arguments)
    #
    #
    #
    def _renderElementPath_HorizLineToRelative(self, path, arguments, group):
        """ HorizLineToRelative command string: h dX0 dXn """
        x0, y0 = self._renderElementPath_GetCurrentPoint(path)

        if len(arguments) < 1:
            raise self.InvalidArgumentCount("h", 1, len(arguments))
        else:
            numPoints = len(arguments)
            for i in range(numPoints):
                x = x0 + float(arguments[i])
                path.lineTo(x, y0)
        return len(arguments)

    #
    #
    #
    def _renderElementPath_VertLineTo(self, path, arguments, group):
        """ HorizLineTo command string: V Y0 Yn """
        x0, y0 = self._renderElementPath_GetCurrentPoint(path)

        if len(arguments) < 1:
            raise self.InvalidArgumentCount("V", 1, len(arguments))
        else:
            numPoints = len(arguments)
            for i in range(numPoints):
                y = float(arguments[i])
                path.lineTo(x0, y)
        return len(arguments)
    #
    #
    #
    def _renderElementPath_VertLineToRelative(self, path, arguments, group):
        """ HorizLineToRelative command string: v dY0 dYn """
        x0, y0 = self._renderElementPath_GetCurrentPoint(path)

        if len(arguments) < 1:
            raise self.InvalidArgumentCount("v", 1, len(arguments))
        else:
            numPoints = len(arguments)
            for i in range(numPoints):
                y = y0 + float(arguments[i])
                path.lineTo(x0, y)
        return len(arguments)


    #
    #
    #
    def _renderElementPath_Arc(self, path, arguments, group):
        """ Arc command string: A RX RY X-Axis-Rotation Large-Arc-Flag Sweep-Flag X Y """
        # elliptic arc parameter def:Draws an elliptical arc from the current point to (x, y).
        #	The size and orientation of the ellipse are defined by two radii (rx, ry) and an x-axis-rotation,
        #	which indicates how the ellipse as a whole is rotated relative to the current coordinate system.
        #	The center (cx, cy) of the ellipse is calculated automatically to satisfy the constraints imposed by the other parameters.
        #	large-arc-flag and sweep-flag contribute to the automatic calculations and help determine how the arc is drawn.

        if len(arguments) < 7:
            raise self.InvalidArgumentCount("A", 7, len(arguments))
        # we can only render circular arcs
        # TODO: warn if we are given an elliptic arc
        rx = float(arguments[0])
        ry = float(arguments[1])
        xAxisRotation = float(arguments[2])
        largeArcFlag = int(arguments[3])
        sweepFlag = int(arguments[4])
        x1, y1 = self._getPointFromArguments(arguments[5:7])

        radius = rx

        # p0 is starting point, p1 is finishing point
        p0 = (self._renderElementPath_GetCurrentPoint(path))
        p1 = (x1, y1)
        logger.debug("SVGRenderer::renderElementPath> p0: " + str(p0) + ", p1: " + str(p1))
        logger.debug("SVGRenderer::renderElementPath> radius: " + str(radius))

        if p0 == p1:
            return 7

        # we currently only handle circular arcs
        if rx != ry:
            raise self.InvalidArguments("A", "SVGRenderer does not currently support elliptic arc paths", arguments)

        if radius <= 0.0:
            raise self.InvalidArguments("A", "radius is less than or equal to 0", arguments)

        if self._debugDraw:
            if largeArcFlag == 1:
                marker = shapes.Circle(p0[0], p0[1], 3)
            else:
                marker = shapes.Rect(p0[0] - 3, p0[1] - 3, 6, 6)
            if sweepFlag == 1:
                marker.setProperties({"fillColor":colors.Color(0, 0, 0, 1)})
            else:
                marker.setProperties({"fillColor":colors.Color(1, 0, 1, 1)})
            group.add(marker)

        # compute the center of the arc
        # ---------------------------------------
        # the center will exist on a line that goes through p_mid and is perpindicular to p0->p1
        # we use a combination of the largeArcFlag and the sweepFlag to determine which side of the p0->p1 line is the center

        # build up triangle T whose sides are: p0    -> p_mid
        #                                      p_mid -> center
        #                                      p0    -> center
        # the angle of the arc will be twice the angle at center

        # p_mid is halfway between p0 and p1
        p_mid = (old_div((p1[0] - p0[0]),2) + p0[0], old_div((p1[1] - p0[1]),2) + p0[1])
        logger.debug("SVGRenderer::renderElementPath> p_mid: " + str(p_mid))

        # l_p0_p_mid is the length of the line between p0 and p_mid
        #  it forms one side of triangle, T:
        #        p0 -> p_mid         len = l_p0_p_mid
        #        p_mid -> center     len = ?
        #        center -> p0        len = radius
        l_p0_p_mid = math.hypot((p_mid[1] - p0[1]), (p_mid[0] - p0[0]))
        logger.debug("SVGRenderer::renderElementPath> l_p0_p_mid: " + str(l_p0_p_mid))

        if l_p0_p_mid > radius:
            raise self.InvalidArguments("A", "arc delta: %s is bigger than radius: %s"  % (l_p0_p_mid, radius), arguments)
        elif l_p0_p_mid <= 0:
            raise self.InvalidArguments("A", "arc delta: %s is <= 0"  % l_p0_p_mid, arguments)

        # a_norm is a normalized vector from p0 to p_mid
        #  refresher: a normalized vector is one whose length is 1
        a = (p_mid[0] - p0[0], p_mid[1] - p0[1])
        a_norm = (old_div(a[0],l_p0_p_mid), old_div(a[1],l_p0_p_mid))

        # invert a_norm to get a perpindicular vector
        # inversion is based on large-arc-flag ??? and sweep-flag ???
        # inversion matrix is |  0  1  | for (L=0,S=1) and (L=1,S=0)
        #                     | -1  0  |
        # inversion matrix is |  0 -1  | for (L=0,S=0) and (L=1,S=1)
        #                     |  1  0  |
        inversionMultiplier = (1.0, -1.0)
        if (largeArcFlag is 0 and sweepFlag is 1) or (largeArcFlag is 1 and sweepFlag is 0):
            inversionMultiplier = (-1.0, 1.0)
        a_inv = (a_norm[1] * inversionMultiplier[0], a_norm[0] * inversionMultiplier[1])

        # l_adj is the length of p_mid -> center in triangle T
        l_adj = math.sqrt(math.pow(radius, 2) - math.pow(l_p0_p_mid, 2))

        # the vector from p_mid to the center is a_inv increased to a length of l_adj
        c_from_mid = (a_inv[0] * l_adj, a_inv[1] * l_adj)

        # center = p_mid + c_from_mid
        center = (p_mid[0] + c_from_mid[0], p_mid[1] + c_from_mid[1])
        logger.debug("SVGRenderer::renderElementPath> a_inv: " + str(a_inv) + ", c_from_mid: " + str(c_from_mid) + ", center: " + str(center))

        # determine the start angle, and end angle
        # ----------------------------------------
        # translate the circle so that the center == origin
        # remove center from p0, p1
        q0 = (p0[0] - center[0], p0[1] - center[1])
        q1 = (p1[0] - center[0], p1[1] - center[1])

        # the start of the arc is the angle to q0
        alpha_start = math.atan2(q0[1], q0[0])

        # the end of the arc is the angle to q1
        alpha_end = math.atan2(q1[1], q1[0])

        # get the angular vector from the start to the end
        angularVector = alpha_end - alpha_start

        if sweepFlag == 1 and angularVector < 0:
            angularVector = (2.0 * math.pi) + angularVector
        elif sweepFlag == 0 and angularVector > 0:
            angularVector = (-2.0 * math.pi) + angularVector

        # check to see if the angularVector needs to be flipped
        #  note: we have to change direction if we are changing arcs (major->minor or minor->major)
        #direction = -1.0 * angularVector / abs(angularVector)
        #if abs(angularVector) < math.pi and largeArcFlag == 1:
        #    angularVector = direction * (2.0 * math.pi - abs(angularVector))
        #elif abs(angularVector) > math.pi and largeArcFlag == 0:
        #    angularVector = direction * (2.0 * math.pi - abs(angularVector))

        # draw the arc (I didn't have much luck using path.arcTo)
        numSegments = int(max(5, abs(angularVector * 286)))	# 286 ~= 5 * 180.0 / pi == 5 segments per degree
        angleInterval = old_div(angularVector, numSegments)
        logger.debug("SVGRenderer::renderElementPath_Arc> arguments: %s center: %s flags: %s alpha_start: %s alpha_end: %s angleDelta: %s" % (arguments, center, (largeArcFlag, sweepFlag), alpha_start, alpha_end, angularVector))
        for j in range(numSegments):
            gamma0 = alpha_start + angleInterval * j
            gamma1 = alpha_start + angleInterval * (j + 1)
            segPt0 = (center[0] + radius * math.cos(gamma0), center[1] + radius * math.sin(gamma0))
            segPt1 = (center[0] + radius * math.cos(gamma1), center[1] + radius * math.sin(gamma1))
            path.lineTo(segPt1[0], segPt1[1])

        return 7

    #
    #
    #
    def _renderElementPath_Curve(self, path, arguments, group):
        """ cubic bezier from x0,y0 to x3,y3 with control points x1,y1 and x2,y2 """
        if len(arguments) < 6 or (len(arguments) % 6) != 0:
            raise self.InvalidArgumentCount("C", 6, len(arguments))

        numCurves = old_div(len(arguments), 6)
        for i in range(numCurves):
            x1, y1 = self._getPointFromArguments(arguments[i * 6    :i * 6 + 2])
            x2, y2 = self._getPointFromArguments(arguments[i * 6 + 2:i * 6 + 4])
            x3, y3 = self._getPointFromArguments(arguments[i * 6 + 4:i * 6 + 6])

            path.curveTo(x1, y1, x2, y2, x3, y3)
        return numCurves * 6
    #
    #
    #
    def _renderElementPath_CurveRelative(self, path, arguments, group):
        """ cubic bezier from x0,y0 to x3,y3 with control points x1,y1 and x2,y2 """
        if len(arguments) < 6 or (len(arguments) % 6) != 0:
            raise self.InvalidArgumentCount("c", 6, len(arguments))

        x0, y0 = self._renderElementPath_GetCurrentPoint(path)

        numCurves = old_div(len(arguments), 6)
        for i in range(numCurves):
            x1, y1 = self._getPointFromArgumentsRelative(arguments[i * 6    :i * 6 + 2], x0, y0)
            x2, y2 = self._getPointFromArgumentsRelative(arguments[i * 6 + 2:i * 6 + 4], x0, y0)
            x3, y3 = self._getPointFromArgumentsRelative(arguments[i * 6 + 4:i * 6 + 6], x0, y0)

            path.curveTo(x1, y1, x2, y2, x3, y3)
        return 6 * numCurves

    #
    #
    #
    def _getPointFromArguments(self, arguments):
        x = float(arguments[0])
        y = float(arguments[1])
        return (x, y)

    #
    #
    #
    def _getPointFromArgumentsRelative(self, arguments, x0, y0):
        x, y = self._getPointFromArguments(arguments)
        return (x + x0, y + y0)

    #
    #
    #
    def _renderElementPath_GetCurrentPoint(self, path):
        if len(path.points) < 2:
            x0 = 0
            y0 = 0
        else:
            x0 = path.points[len(path.points) - 2]
            y0 = path.points[len(path.points) - 1]

        return x0, y0

    #
    #
    #
    def renderElementImage(self, element, group, isClipPath=0):
        attrs = self._getAttributes(element, self._attributeMapImage)
        elementTransformList = self.parseTransform(element)

        # nromalize element x,y to (0,0) by adding a (x,y) translation to the transform list
        x = attrs["x"]
        y = attrs["y"]
        attrs["x"] = 0
        attrs["y"] = 0
        elementTransformList.append(graphics_utils.translateTransform(x, y))

        if self._viewBox != None:
            # compute any necessary clipping rect
            # need to compute the fully transformed bounds of the desired image
            #  so that we can compare against the SVG's
            #   *  get transform matrix for element
            elementTransformMatrix = graphics_utils.computeTransformMatrix(elementTransformList)
            #   *  get transform matrix for group
            #      TODO: This won't handle nested group transforms
            groupTransformMatrix = group.transform
            #   *  post-multiply the group transform by the element transform to get complete transform
            transformMatrix = shapes.mmult(groupTransformMatrix, elementTransformMatrix)
            #   *  build bounding rect of the element
            x = attrs["x"]
            y = attrs["y"]
            w = attrs["width"]
            h = attrs["height"]
            boundingRect = (x, y, x+w, y+h)
            #   * compute the inverse of the transform matrix
            #     this will allow us to move the SVG-wide bounds into the image's coordinate space
            #     so that we can then compute the clipping rect in the image's space
            transformMatrixInv = shapes.inverse(transformMatrix)
            #   * get a viewBox rect in the element's coordinate space
            viewBoxP1 = (self._viewBox[0], self._viewBox[1])
            viewBoxP2 = (self._viewBox[2], self._viewBox[3])
            viewBoxP1_elemSpace = shapes.transformPoint(transformMatrixInv, viewBoxP1)
            viewBoxP2_elemSpace = shapes.transformPoint(transformMatrixInv, viewBoxP2)
            viewBox_elemSpace = (viewBoxP1_elemSpace[0], viewBoxP1_elemSpace[1], viewBoxP2_elemSpace[0], viewBoxP2_elemSpace[1])

            #   * check for intersection
            clipRect = graphics_utils.computeRectIntersection(boundingRect, viewBox_elemSpace)

            logger.debug("renderElementImage transformMatrix=%s, boundingRect=%s, viewBox_elemSpace=%s, clipRect=%s" %
                        (transformMatrix, boundingRect, viewBox_elemSpace, clipRect))

            if clipRect == None:
                # no intersection at all, don't add image
                return

            elementTransformList.append(graphics_utils.translateTransform(clipRect[0], clipRect[1]))

            attrs["clipRect"] = (clipRect[0] - x, clipRect[1] - y, clipRect[2] - x, clipRect[3] - y)
            logger.debug("renderElementImage clipRect with origin at boundingRect origin %s, x=%s, y=%s" % (attrs["clipRect"], x, y))

        # we only handle PNG images right now
        image = image_utils.PngImage(**attrs)
        # flip the image about the x-axis -- since image.y ALWAYS is 0, we only have to translate by the height to offset the -1 scale
        elementTransformList.append(graphics_utils.translateTransform(0, image.height))
        elementTransformList.append(graphics_utils.scaleTransform(1.0, -1.0))

        group.add(self._applyWrappingTransformList(elementTransformList, image))

    def _applyWrappingTransformIfNeeded(self, svgElement, pdfObject):
        """ if there is a transform specified in the svgElement,
            wrap the pdfObject in a group with the applied transform """
        if "transform" in svgElement.attrib:
            transformList = self.parseTransform(svgElement)
            return self._applyWrappingTransformList(transformList, pdfObject)

        return pdfObject

    def _applyWrappingTransformList(self, transformList, pdfObject):
        wrapperGroup = Group()
        self.applyTransformList(transformList, wrapperGroup)
        wrapperGroup.add(pdfObject)
        return wrapperGroup

    def applyTransform(self, svgElement, pdfGroup):
        """ extracts transform attribute from element,
            parses out information from transform string """
        transformList = self.parseTransform(svgElement)
        self.applyTransformList(transformList, pdfGroup)

    def applyTransformList(self, transformList, pdfGroup):
        for transform in transformList:
            if transform['transform'] is 'translate':
                pdfGroup.translate(transform['tx'], transform['ty'])
            elif transform['transform'] is 'rotate':
                pdfGroup.translate(transform['cx'], transform['cy'])
                pdfGroup.rotate(transform['theta'])
                pdfGroup.translate(-1.0 * transform['cx'], -1.0 * transform['cy'])
            elif transform['transform'] is 'scale':
                pdfGroup.scale(transform['sx'], transform['sy'])
            else:
                logger.warning("SVGRenderer::applyTransform> unknown transform type: %s" % transform['transform'])

        logger.debug("SVGRenderer::applyTransform> final matrix: " + str(pdfGroup.transform))

    def parseTransform(self, svgElement):
        """ returns a list of transform elements each of which is a dictionary:
            {transform:"translate", tx:"tx", ty:"ty"}
            {transform:"rotate", cx:"cx", cy:"cy"}
            {transform:"scale", sx:"sx", sy:"sy"}
        """
        transformList = []

        transformsString = svgElement.get("transform")
        if transformsString is None:
            return transformList

        # find each individual transform string <transform-type>(arg0...argN)
        transformMatches = re.findall("[\w]+\([\s]*[+-]?\d+(?:\.\d+)?(?:[eE][+-]\d+)?[\s]*(?:[\s,][\s]*[+-]?\d+(?:\.\d+)?(?:[eE][+-]\d+)?[\s]*)*\)", transformsString)

        for transformString in transformMatches:
            logger.debug("SVGRenderer::parseTransform> transformString: " + transformString)

            transformStringComponents = re.findall("[+-]?\d+(?:\.\d+)?(?:[eE][+-]\d+)?|\w+", transformString)
            if len(transformStringComponents) > 0:
                command = transformStringComponents[0]
                numArgs = len(transformStringComponents) - 1

                if command == "translate":
                    # translate is like "translate(tx,ty)"
                    if numArgs == 2:
                        tx = float(transformStringComponents[1])
                        ty = float(transformStringComponents[2])
                        logger.debug("SVGRenderer::parseTransform> tx = " + str(tx) + " ty = " + str(ty))
                        transformList.append({"transform":"translate", "tx":tx, "ty":ty})

                    elif numArgs == 1:
                        # set y to 0 if there's only x provided
                        tx = float(transformStringComponents[1])
                        ty = 0
                        logger.debug("SVGRenderer::parseTransform> tx = " + str(tx) + " ty = " + str(ty))
                        transformList.append({"transform": "translate", "tx": tx, "ty": ty})
                    else:
                        logger.warning("SVGRenderer::parseTransform> translate command given something other than 2 arguments: " + transformString)
                elif command == "rotate":
                    # rotate is like "rotate(theta,cx,cy)"
                    #  theta is in degrees and is about a z-axis that comes out of an upper-left coordinate system
                    #  it needs to be mapped to a z-axis coming out of bottom-left coordinate system
                    # cx,cy indicate a translation that should occur prior to rotation, it is reverted after translation
                    #  we need to coordinate map the cy translation
                    if numArgs == 1 or numArgs == 3:
                        theta = float(transformStringComponents[1])
                        cx = 0
                        cy = 0
                        if numArgs == 3:
                            cx = float(transformStringComponents[2])
                            cy = float(transformStringComponents[3])

                        logger.debug("SVGRenderer::parseTransform> theta = " + str(theta) + ", cx = " + str(cx) + ", cy = " + str(cy))

                        transformList.append({"transform":"rotate", "theta":theta, "cx":cx, "cy":cy})
                    else:
                        logger.warning("SVGRenderer::parseTransform> rotate command given something other than 1 or 3 arguments: " + transformString)
                elif command == "scale":
                    sx = 1.0
                    sy = 1.0
                    if numArgs == 1:
                        sx = float(transformStringComponents[1])
                        sy = sx
                    elif numArgs == 2:
                        sx = float(transformStringComponents[1])
                        sy = float(transformStringComponents[2])
                    else:
                        logger.warning("SVGRenderer::parseTransform> scale command given something other than 1 or 2 arguments: " + transformString)
                    logger.debug("SVGRenderer::parseTransform> scaling: " + str(sx) + ", " + str(sy))
                    transformList.append({"transform":"scale", "sx":sx, "sy":sy})

                else:
                    logger.debug("SVGRenderer::parseTransform> unknown transformType: " + command)

        return transformList


class FontManagedString(shapes.Shape):
    """ FontManagedString
        This Shape subclass represents a string that can contain characters that require
        different fonts for rendering. The fonts used is determined by the FontManager.
        (see font_manager.py)
    """

    _cachedWidth = -1
    _cachedTextSegments = None
    x = 0
    y = 0
    text = None
    fontSize = 10
    textAnchor = 'start'
    fontManager = None
    fillColor = colors.Color(0, 0, 0, 1)

    def __init__(self, x, y, text, **kw):
        self.x = x
        self.y = y
        self.text = text
        if 'fontSize' in kw:
            self.fontSize = kw['fontSize']
        if 'fontManager' in kw:
            self.fontManager = kw['fontManager']
        if 'textAnchor' in kw:
            self.textAnchor = kw['textAnchor']
        if 'fillColor' in kw:
            self.fillColor = kw['fillColor']

    # taken from reportlab.shapes.string
    def copy(self):
        new = self.__class__(self.x, self.y, self.text)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        width = self._getWidth()
        x = self._getAnchoredX()

        return (x, self.y - 0.2 * self.fontSize, x + width, self.y + self.fontSize)

    def _getWidth(self):
        if self._cachedWidth == -1:
            if self.fontManager == None:
                logger.error("FontManagedString::_getWidth fontManager is None")
                return 0

            textSegments = self._getTextSegments()

            self._cachedWidth = self.fontManager.textWidth(self.text, self.fontSize, textSegments)

        return self._cachedWidth

    def _getTextSegments(self):
        if self._cachedTextSegments == None:
            self._cachedTextSegments = self.fontManager.segmentTextByFont(self.text)

        return self._cachedTextSegments

    def _getAnchoredX(self):
        textAnchor = self.textAnchor
        x = self.x
        width = self._getWidth()

        if textAnchor != 'start':
            if textAnchor == 'middle':
                x -= 0.5 * width
            elif textAnchor == 'end':
                x -= width
            elif textAnchor == 'numeric':
                logger.warning("FontManagedString does not support textAnchor=numeric")

        return x

    def _drawTimeCallback(self, node, canvas, renderer):
        if not isinstance(renderer, renderPDF._PDFRenderer):
            logger.error("FontManagedString only supports PDFRenderer")
            return

        if self.fontManager == None:
            logger.error("FontManagedString::_drawTimeCallback fontManager is none")
            return

        x = self._getAnchoredX()
        textSegments = self._getTextSegments()

        canvas.setFillColor(self.fillColor)
        textObject = canvas.beginText(x, self.y)
        self.fontManager.addTextAndFontToTextObject(textObject, self.text, self.fontSize, textSegments)
        canvas.drawText(textObject)
