define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'views/shared/FlashMessages',
    'views/shared/Modal',
    'splunk.util'
],
    function(
        $,
        _,
        module,
        BaseView,
        FlashMessagesView,
        Modal,
        splunkUtils
        ) {
        return BaseView.extend({
            moduleId: module.id,
            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.children.flashMessages = new FlashMessagesView({
                    model: this.model.installApp
                });
                this.appRemoteType = this.model.appRemote.get('type') === 'addon' ? 'Add-on' : 'App';
                this.headerText = splunkUtils.sprintf(_('%s Installation Failed').t(), this.appRemoteType);
            },

            events: $.extend({}, Modal.prototype.events, {
                'click .btn-primary': function(e) {
                    this.model.wizard.set('step', 1);
                }
            }),

            render: function() {
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(this.headerText);
                this.children.flashMessages.render().prependTo(this.$(Modal.BODY_SELECTOR));
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="btn btn-primary modal-btn-primary">' + _('Retry').t() + '</a>');
                return this;
            }
        });
});
