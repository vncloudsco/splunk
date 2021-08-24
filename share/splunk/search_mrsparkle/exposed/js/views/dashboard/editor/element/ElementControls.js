define([
    'underscore',
    'module',
    'views/Base',
    'views/shared/delegates/Popdown',
    'views/dashboard/editor/element/DialogHelper'
], function(_,
            module,
            BaseView,
            Popdown,
            DialogHelper
) {

    var ElementControls = BaseView.extend({
        moduleId: module.id,
        className: 'dashboard-element-controls',
        initialize: function(options) {
            BaseView.prototype.initialize.apply(this, arguments);
            this.searchManager = options.searchManager;
            this.eventManager = options.eventManager;
            this.settings = options.settings;
        },
        events: {
            'click a.action-edit-drilldown': function(e) {
                e.preventDefault();
                var dialog = DialogHelper.openEditDrilldownDialog({
                    settings: this.settings,
                    model: this.model,
                    collection: this.collection,
                    eventManager: this.eventManager
                }).on('drilldownUpdated', function() {
                    this.model.controller.trigger('edit:drilldown', {eventManagerId: this.eventManager.id});
                    dialog.hide();
                }.bind(this));
                this.children.popdown.hide();
            }
        },
        getTemplateArgs: function() {},
        render: function() {
            this.$el.html(this.compiledTemplate(_.extend({
                iconClass: this.getIconClass()
            }, this.getTemplateArgs())));
            this.children.popdown = new Popdown({el: this.el, mode: 'dialog'});
            return this;
        }
    });
    return ElementControls;
});
