define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'views/Base',
        'views/shared/reportcontrols/dialogs/AccelerationDialog'
    ],
    function($, _, Backbone, module, Base, AccelerationDialog) {
        return Base.extend({
            moduleId: module.id,
            tagName: 'span',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
            },
            events: {
                'click a.edit-acceleration': function(e) {
                    this.children.accelerationDialog = new AccelerationDialog({
                        model: {
                            report: this.model.report,
                            searchJob: this.model.searchJob,
                            application: this.model.application,
                            user: this.model.user
                        },
                        collection: {
                            workloadManagementStatus: this.collection.workloadManagementStatus
                        },
                        onHiddenRemove: true
                    });

                    this.children.accelerationDialog.render().appendTo($("body"));
                    this.children.accelerationDialog.show();

                    e.preventDefault();
                }
            },
            render: function() {
                this.$el.html(this.compiledTemplate({
                    _: _
                }));
                return this;
            },
            template: '\
                <a class="edit-acceleration" aria-label="<%- _("Edit Acceleration").t() %>" href="#"><%- _("Edit").t() %></a>\
            '
        });
    }
);
