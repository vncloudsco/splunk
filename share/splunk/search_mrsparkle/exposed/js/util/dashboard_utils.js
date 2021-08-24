/**
 * utility class that used in dashboard rendering
 */
define([
    'jquery',
    'underscore',
    'splunk.config',
    'util/general_utils'
], function($, _, SplunkConfig, GeneralUtils) {
    return {
        /**
         * Get app and source out of a string
         * Example Usage:
         * 'myapp:file','defaultApp'  -> {app:'myapp',src:'file'}
         * 'file','defaultApp'  -> {app:'defaultApp',src:'file'}
         * 'myapp:folder/file.js'  -> {app:'myapp',src:'folder/file.js'}
         * 'myapp:file:others'  -> {app:'myapp',src:'file:others'}
         */
        getAppAndSource: function(path, defaultApp) {
            var ret = {
                app: defaultApp
            };
            if (_.isString(path)) {
                var parts = path.split(':');
                if (parts.length === 1) {
                    ret.src = parts[0];
                }
                else if (parts.length === 2) {
                    ret.app = parts[0];
                    ret.src = parts.slice(1).join(':');
                }
            }
            return ret;
        },

        /**
         * Determine whether inline stylesheets are allowed for inline HTML elements in dashboards. This is determined
         * by examining the splunk.config ($C) from the server
         * @returns {Boolean} true if inline stylesheets are allowed, otherwise false
         */
        allowInlineStyles: function() {
            return GeneralUtils.normalizeBoolean(SplunkConfig['DASHBOARD_HTML_ALLOW_INLINE_STYLES'], {"default": true});
        },
        /**
         * Determine whether iframes are allowed for HTML elements in dashboards. This is determined
         * by examining the splunk.config ($C) from the server
         * @returns {Boolean} true if iframes are allowed, otherwise false
         */
        allowIframes: function() {
            return GeneralUtils.normalizeBoolean(SplunkConfig['DASHBOARD_HTML_ALLOW_IFRAMES'], {"default": true});
        },
        /**
         * Determine whether embeddable content is allowed for HTML elements in dashboards. This is determined
         * by examining the splunk.config ($C) from the server
         * @returns {Boolean} true if iframes are allowed, otherwise false
         */
        allowEmbeds: function() {
            return GeneralUtils.normalizeBoolean(SplunkConfig['DASHBOARD_HTML_ALLOW_EMBEDDABLE_CONTENT'], {"default": false});
        },
        /**
         * Determine whether embed tags should be sandboxed in dashboards. This is determined
         * by examining the splunk.config ($C) from the server
         * @returns {Boolean} true if embed tags should be sandboxed, otherwise false
         */
        allowWrapEmbed: function() {
            return GeneralUtils.normalizeBoolean(SplunkConfig['DASHBOARD_HTML_WRAP_EMBED'], {"default": true});
        },
        updateSearchMessage: function(model, searchId, level, message, options) {
            options = options || {};
            var messages = model.get(searchId);
            if (!messages || options.reset) {
                messages = {
                    errors: [],
                    warnings: []
                };
            }
            switch (level) {
                case 'warning':
                    messages.warnings.push(message);
                    messages.warnings = _.uniq(messages.warnings);
                    break;
                default:
                    messages.errors.push(message);
                    messages.errors = _.uniq(messages.errors);
                    break;
            }
            model.set(searchId, messages);
        },
        getPrimarySearchManager: function(managerIds, registry) {
            if (_.isArray(managerIds)) {
                // find primary search manager
                return _.chain(managerIds).map(function(id) {
                    return registry.get(id);
                }).find(function(manager) {
                    return manager && manager.getType() === 'primary';
                }).value();
            } else if (_.isString(managerIds)) {
                return registry.get(managerIds);
            }
        },

        /**
         * HTML element content will be localized if it contains i18ntag attribute.
         * HTML element’s attribute value will be localized if it is listed in i18nattr attribute.
         * Example:-
         * <sometag i18ntag="">Blablabla</sometag> would cause "Blablabla" to be extracted in messages.pot file when using splunk extract i18n command
         * <sometag title="Foobar" render="True" i18nattr="title, render" /> would cause "Foobar" and "True" to be extracted.
         * @returns {String} HTML string after localization
         */
        localizeHtmlContent: function(inputHtml) {
            var html = $('<div></div>')
                        .html(inputHtml)
                        .find("[i18ntag], [i18nattr]")
                            .each(function() {
                                var $el = $(this);
                                if (!_.isUndefined($el.attr("i18ntag"))) {
                                    $el.text(_($el.text()).t());
                                }
                                var i18nattr = $el.attr("i18nattr");
                                if (i18nattr) {
                                    $.each(i18nattr.split(","), function(key, value) {
                                        if(value) {
                                            value = value.trim();
                                            if  ($el.prop(value)) {
                                                $el.prop(value, _($el.prop(value)).t());
                                            }
                                        }
                                    });
                                }
                            })
                        .end()
                        .html();
            return html;
        }
    };
});
