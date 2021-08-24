define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/shared/Modal',
    'splunk.util'
],
    function(
        $,
        _,
        module,
        BaseView,
        Modal,
        splunkUtils
        ) {
        return BaseView.extend({
            moduleId: module.id,
            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.appType = this.model.appRemote.get('type') === 'addon' ? 'Add-on' : 'App';
                this.headerText = splunkUtils.sprintf('%s %s...', _("Installing").t(), this.appType);
            },

            render: function() {
                this.$el.html(Modal.TEMPLATE);
                // load custom header instead of default if it exists
                this.$(Modal.HEADER_TITLE_SELECTOR).html(this.options.customHeader ? this.options.customHeader : this.headerText);
                this.$(Modal.BUTTON_CLOSE_SELECTOR).remove();

                var msg = this.options.customBody || splunkUtils.sprintf(_("%s is being downloaded and installed.").t(), this.model.appRemote.get('title'));
                var template = this.compiledTemplate({
                    msg: msg
                });
                this.$(Modal.BODY_SELECTOR).append(template);
                return this;
            },

            template: '\
                <p>\
                    <%- msg %>\
                </p>\
            '
        });
    });
