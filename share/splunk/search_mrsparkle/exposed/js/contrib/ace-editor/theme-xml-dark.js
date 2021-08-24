ace.define("ace/theme/xml-dark",["require","exports","module","ace/lib/dom"], function(require, exports, module) {
exports.isDark = true;
exports.cssClass = "ace-xml-dark";
exports.cssText =".ace-xml-dark .ace_gutter {\
    background: #333333;\
    color: #999999;\
}\
.ace-xml-dark .ace_marker-layer .ace_selection {\
    background: rgba(27, 170, 222, 0.38)\
}\
.ace-xml-dark {\
    background-color: #31373E;\
    color: #CCCCCC;\
}\
.ace-xml-dark.ace_editor.ace_autocomplete .ace_rightAlignedText{\
    color:#999999;\
}\
.ace-xml-dark.ace_editor.ace_autocomplete {\
    background: #31373E;\
    color: #CCCCCC;\
}\
.ace-xml-dark.ace_editor.ace_autocomplete .ace_marker-layer .ace_active-line {\
    background: rgba(61, 170, 255, 0.22);\
}\
.ace-xml-dark.ace_editor.ace_autocomplete .ace_marker-layer .ace_line-hover {\
    background: #333333;\
}\
.ace-xml-dark.read-only .ace_cursor {\
    opacity: 0;\
}\
.ace-xml-dark.disabled .ace_content {\
    cursor: not-allowed;\
    opacity: 0.6;\
}\
.ace-xml-dark.disabled {\
    background-color: #333333;\
}\
.ace-xml-dark .ace_attribute-name {\
    color: #AF575A;\
}\
.ace-xml-dark .ace_attribute-value {\
    color: #58A383;\
}\
.ace-xml-dark .ace_text {\
    color: #FFFFFF;\
}\
.ace-xml-dark .ace_tag {\
    color: #BD9872;\
}\
";

var dom = require("../lib/dom");
dom.importCssString(exports.cssText, exports.cssClass);
});
