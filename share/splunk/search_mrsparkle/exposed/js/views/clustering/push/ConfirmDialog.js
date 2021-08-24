define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'uri/route',
    'views/shared/Modal',
    'models/clustering/Actions'
],
    function(
        $,
        _,
        Backbone,
        module,
        route,
        Modal,
        ActionsModel
        ) {
        return Modal.extend({
            moduleId: module.id,
            className: Modal.CLASS_NAME,
            /**
             * @param {Object} options {
             *       model: <models>,
             *       onHiddenRemove: {Boolean},
             *       action: <ActionsModel.actions>
             * }
             */
            initialize: function(options) {
                Modal.prototype.initialize.apply(this, arguments);
                this.action = this.options.action;
            },
            events: $.extend({}, Modal.prototype.events, {
                'click .btn-primary': function(e) {
                    this.model.pushModel.trigger('action');
                    this.model.pushModel.trigger(this.action);
                    this.hide();
                }
            }),
            getTemplateContent: function() {
                var content = {};
                switch (this.action) {
                    case ActionsModel.actions.PUSH:
                        content.header = _('Distribute Configuration Bundle').t();
                        content.select = _('Push Changes').t();
                        content.body = _('Some configuration changes might require a restart of all peers. ' +
                                         'Would you like to push the changes?').t();
                        break;
                    case ActionsModel.actions.CHECK_RESTART:
                        content.header = _('Validate and Check if Restart is Required').t();
                        content.select = _('Validate and Check Restart').t();
                        content.body = _('Some configuration changes might only be valid on certain versions of Splunk Enterprise, or ' +
                                         'might require a restart of all peers. Would you like to validate and ' +
                                         'check if these changes would require a restart? This will not push the changes.').t();
                        break;
                    case ActionsModel.actions.ROLLBACK:
                        content.header = _('Rollback Last Applied Configuration Bundle').t();
                        content.select = _('Rollback Changes').t();
                        content.body = _('Some configuration changes might require a restart of all peers. ' +
                                         'Would you like to rollback the last applied configuration bundle?').t();
                        break;
                    default:
                }
                return content;
            },
            render: function() {
                var content = this.getTemplateContent();
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(content.header);
                var root = this.model.application.get('root'),
                    locale = this.model.application.get('locale'),
                    link = route.docHelp(root, locale, 'manager.clustering.bundle');

                var html = this.compiledTemplate({
                    learnmoreLink: link,
                    content: content
                });
                this.$(Modal.BODY_SELECTOR).append(html);
                this.$(Modal.BODY_SELECTOR).show();
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="btn btn-primary modal-btn-primary">'+ content.select +'</a>');
                return this;
            },
            template: "<%= content.body %> <a href='<%=learnmoreLink %>' class='external' target='_blank'><%= _('Learn More').t() %></a>"
        });
    });
