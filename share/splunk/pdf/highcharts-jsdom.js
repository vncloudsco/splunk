/**
 * Extension to jsdom that provides just enough SVG capabilities to
 * render Highcharts.
 */
/* eslint-env node */
var jsdom = require('jsdom');
var PDFDocument = require('pdfkit');
var baseFn = jsdom.jsdom;

jsdom.jsdom = function () {
    var doc = baseFn.apply(this, arguments);
    var window = doc.defaultView;

    doc.createElementNS = function (ns, tagName) {
        var elem = doc.createElement(tagName);

        // Set private namespace to satisfy jsdom's getter
        elem._namespaceURI = ns; // eslint-disable-line no-underscore-dangle
        /**
         * Pass Highcharts' test for SVG capabilities
         * @returns {undefined}
         */
        elem.createSVGRect = function () {};
        /**
         * jsdom doesn't compute layout (see https://github.com/tmpvar/jsdom/issues/135).
         * This getBBox implementation provides just enough information to get Highcharts
         * to render text boxes correctly, and is not intended to work like a general
         * getBBox implementation.
         * @returns {Object} The bounding box
         */
        elem.getBBox = function () {
            try {
                if (this.textContent) {
                    var doc = new PDFDocument(),
                        fontSize = parseInt(window.getComputedStyle(elem, null).getPropertyValue("font-size"), 10),
                        font = doc.font('Helvetica', fontSize),
                        // Multi-line labels are implemented using a <tspan> element for each line.
                        lines = this.querySelectorAll('tspan'),
                        // Count the number of <tspan>s to determin the number of lines, or assume one line if no <tspans>.
                        numLines = Math.max(lines.length, 1),
                        // SPL-146805, when there's no tspan, the width of BBox should still return the width of the string
                        maxWidthOfLines = font.widthOfString(this.textContent);

                    if (!fontSize) {
                        window.console.log('ERROR: In getBBox, element has no font size');
                        // To track down the log statement above, un-comment this throw and comment out the try-catch around getBBox in Highcarts
                        // throw new Error('In getBBox, element has no font size');
                    }

                    // SPL-146805, only compute the maxWidth of the line when there's a tspan element found
                    if (lines.length > 0) {
                        maxWidthOfLines = Array.prototype.reduce.call(lines,
                            function getMaxWidth(maxWidth, line) {
                                return Math.max(maxWidth, font.widthOfString(line.textContent));
                            }, 0);
                    }

                    return ({
                        x: elem.offsetLeft,
                        y: elem.offsetTop,
                        width: maxWidthOfLines,
                        height: font.currentLineHeight() + (numLines - 1) * font.currentLineHeight(true)
                    });
                }
                return ({
                    x: elem.offsetLeft || 0,
                    y: elem.offsetTop || 0,
                    width: elem.offsetWidth || 0,
                    height: elem.offsetHeight || 0
                });
            } catch (e) {
                console.log('highcharts-jsdom getBBox error ' + e);
            }
        };
        return elem;
    };
    return doc;
};

module.exports = jsdom;
