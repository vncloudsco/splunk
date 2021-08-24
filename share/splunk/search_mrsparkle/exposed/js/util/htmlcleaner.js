define(['underscore', 'jquery', 'dompurify', 'util/console'], function (_, $, DOMPurify, console) {

    var HTML_COMMENTS_PATTERN = /<!--.+?-->/gmi;
    var BAD_NODE_SELECTOR = 'script,base,link,meta,head,*[type="text/javascript"]';
    //var ALLOWED_URLS = /^(?:\/[^\/]|https?:|#)/g;
    var BAD_URL_SCHEMES = /(?:javascript|jscript|livescript|vbscript|data(?!:image\/)|about|mocha):/i;
    var WITH_SCRIPT = /<script>(.*?)<\/script>/i;
    var WITH_MULTI_LINE_SCRIPT = /<script>(.+)((\s)+(.+))+<\/script>/i;
    var EVENT_HANDLER_ATTRIBUTE_PREFIX = "on";
    var CSS_NODE_SELECTOR = 'style';
    var CSS_EXPRESSION_PATTERN = /(^|[\s\W])expression(\s*\()/gmi;
    var CSS_EXPRESSION_REPLACE = '$1no-xpr$2';
    var URL_ATTRIBUTES = {
        link: ['href'],
        applet: ['code', 'object'],
        iframe: ['src', 'srcdoc'],
        img: ['src'],
        embed: ['src'],
        layer: ['src'],
        a: ['href']
    };
    var forbidAttr = [];
    var WRAP_EMBED_TAGS = false;
    var ALLOW_INLINE_STYLE = false;
    var dashboardTags = [];
    var dashboardTelemetry = false;

    function cleanupUrl(url) {
        var decodedURI = $.trim(url || '');
        try {
            decodedURI = decodeURIComponent(decodedURI);
        } catch (err) {
            console.log('Caught an exception: ' + err);
            decodedURI = _.unescape(decodedURI);
        }
        return decodedURI.replace(/\s/gmi, '');
    }

    function isBadUrl(url) {
        return BAD_URL_SCHEMES.test(cleanupUrl(url));
    }

    function isBadNodeValue(val) {
        var convertedStr = (_.unescape($.trim(val || ''))).replace(/\s/gmi, '');
        return BAD_URL_SCHEMES.test(convertedStr) || WITH_MULTI_LINE_SCRIPT.test(convertedStr) || WITH_SCRIPT.test(convertedStr);
    }

    function cleanStylesheet(styleNode) {
        var $style = $(styleNode);
        var cssText = $style.html();
        var newText = cleanCssText(cssText);
        if (cssText != newText) {
            $style.text(newText);
        }
    }

    function cleanCssText(cssText) {
        CSS_EXPRESSION_PATTERN.lastIndex = 0;
        return cssText.replace(CSS_EXPRESSION_PATTERN, CSS_EXPRESSION_REPLACE);
    }

    function clearAttributes(node) {
        _.each(getAttributeNames(node), function (name) {
            node.removeAttribute(name);
        });
    }

    function getAttributeNames(node) {
        var attrNames = [];
        _.each(node.attributes, function (attr) {
            attrNames.push(attr.name);
        });
        return attrNames;
    }

    function isValidAttribute(attrName, attrValue, node) {
        var lcAttrName = attrName.toLowerCase();
        var lcTagName = node.tagName && node.tagName.toLowerCase();
        // remove invalid data attributes
        if (lcAttrName === "data-main") {
            return false;
        }
        else if (lcAttrName === "data-target") {
            try {
                if (node.ownerDocument.querySelector(attrValue)) {
                    return true;
                }
            } catch(error) {
                console.error(error);
            }
            return false;
        }
        // remove event listener
        if ((lcAttrName.indexOf(EVENT_HANDLER_ATTRIBUTE_PREFIX) === 0)
            || isBadNodeValue(attrValue)
            || forbidAttr.indexOf(lcAttrName) !== -1) {
            if (lcTagName !== 'iframe') {
                return false;
            }
        }
        var urlAttrs = URL_ATTRIBUTES[lcTagName];
        if (urlAttrs && _(urlAttrs).contains(lcAttrName)) {
            if (isBadUrl(attrValue)) {
                return false;
            }
        }
        return true;
    }

    var validAttributeNames = [];
    var validAttributes = {};

    DOMPurify.addHook('beforeSanitizeAttributes', function (node) {
        validAttributeNames = [];
        validAttributes = {};
        _.each(getAttributeNames(node), function (name) {
            var val = node.getAttribute(name);
            if (isValidAttribute(name, val, node)) {
                validAttributeNames.push(name);
                validAttributes[name] = val;
            }
        });
    });

    DOMPurify.addHook('afterSanitizeAttributes', function (node) {
        clearAttributes(node);
        if (node.tagName.toLowerCase() === 'iframe' && !('sandbox' in validAttributes)) {
            validAttributeNames.push('sandbox');
            validAttributes['sandbox'] = 'allow-scripts';
        }
        _.each(validAttributeNames, function (attrName) {
            try {
                node.setAttribute(attrName, validAttributes[attrName]);
            } catch (ex) {
                console.error('Cannot set an invalid attribute: ' + attrName);
            }
        });
    });

    DOMPurify.addHook('afterSanitizeElements', function (currentNode) {
        // hook to clean <style> content
        if (currentNode.tagName && currentNode.tagName.toLowerCase() === 'style') {
            cleanStylesheet(currentNode);
        }
    });

    DOMPurify.addHook('beforeSanitizeElements', function (currentNode) {
        if (dashboardTelemetry && currentNode.tagName) {
            dashboardTags.push(currentNode.tagName);
        }
    });

    function wrapEmbedTag(embedNode) {
        var embedTag = $(embedNode);
        var style = 'style="background-color: transparent; border: 0px none transparent; padding: 0px; overflow: hidden; width: 100%; height: 100%;"';
        var className = '"embed-wrapper"';
        if (!ALLOW_INLINE_STYLE) {
            embedTag.removeAttr('style');
            style = '';
        }
        var outer = _.escape(embedTag.prop('outerHTML'));
        var wrapped = '<iframe sandbox="allow-scripts" srcdoc="' + outer + '" ' + style + ' class=' + className + '></iframe>';
        embedTag.replaceWith(wrapped);
        return embedTag;
    }

    DOMPurify.addHook('afterSanitizeElements', function (currentNode) {
        if (currentNode.tagName && currentNode.tagName.toLowerCase() === 'embed' && WRAP_EMBED_TAGS) {
            wrapEmbedTag(currentNode);
        }
    });

    /**
     *
     * @param htmlText {string}
     * @param options {object}
     * @param options.allowInlineStyles {boolean}
     * @param options.allowIframes {boolean}
     * @returns {*}
     */
    function dompurifyHtml(htmlText, options) {
        try {
            // convert xml(if it is) into valid html
            var validHtml = $('<tmp>' + htmlText + '</tmp>').html();
            options || (options = {});
            var forbidTags = BAD_NODE_SELECTOR.split(',');
            forbidAttr = ['allowscriptaccess'];
            // these attrs are currently being used, we need to whitelist them
            var allowAttr = ['i18ntag', 'i18nattr', 'section-label'];
            var allowTag = ['iframe', 'embed', 'h7', 'h8', 'h9', 'splunk-search-dropdown', 'splunk-control-group', 'splunk-select', 'splunk-radio-input', 'splunk-text-area', 'splunk-text-input', 'splunk-color-picker', 'splunk-color'];
            if(options.allowIframes === false) {
                forbidTags.push('iframe');
            }
            if (options.allowInlineStyles === false) {
                forbidAttr.push('style');
                ALLOW_INLINE_STYLE = false;
            }
            if (options.allowEmbeds === false) {
                forbidTags.push('embed');
                forbidTags.push('iframe');
            }
            if (options.wrapEmbedTags === true && options.allowIframes !== false) {
                WRAP_EMBED_TAGS = true;
            }
            if (options.dashboardTelemetry === true) {
                dashboardTelemetry = true;
            }
            dashboardTags = [];

            var domPurifyCfg = {
                SAFE_FOR_JQUERY: true,
                ALLOW_DATA_ATTR: true,
                FORCE_BODY: true,
                ADD_TAGS: allowTag,
                ADD_ATTR: allowAttr,
                FORBID_TAGS: forbidTags,
                FORBID_ATTR: forbidAttr
            };
            var cleanHtml = DOMPurify.sanitize(validHtml, domPurifyCfg);
            WRAP_EMBED_TAGS = false;
            ALLOW_INLINE_STYLE = true;
            if (dashboardTelemetry){
                var data = { type: 'htmlcleaner.dashboard', data: { sanitizedTags: dashboardTags } };
                window._splunk_metrics_events && window._splunk_metrics_events.push(data);
            }
            dashboardTelemetry = false;
            return cleanHtml;
        } catch (ex) {
            return htmlText;
        }
    }

    return {
        clean: dompurifyHtml,
        isBadUrl: isBadUrl,
        isBadNodeValue: isBadNodeValue,
        _cleanCssText: cleanCssText
    };

});
