define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/reportcontrols/dialogs/createreport/Master'
    ],
    function($, _, module, Base, SaveAsDialog) {
        return Base.extend({
            moduleId: module.id,
            className: 'save-report-as',
            tagName: 'li',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
            },
            events: {
                'click a': function(e) {
                    e.preventDefault();

                    this.children.saveAsDialog = new SaveAsDialog({
                        model:  {
                            report: this.model.report,
                            application: this.model.application,
                            searchJob: this.model.searchJob,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo
                        },
                        onHiddenRemove: true
                    });

                    this.children.saveAsDialog.render().appendTo($('body')).show();

                    this.listenTo(this.children.saveAsDialog, 'createSuccess', function () {
                        this.model.report.trigger('createReport', { status: 'success' });
                    }.bind(this));
                }
            },
            render: function() {
                var template = this.compiledTemplate({
                    _: _
                });
                this.$el.html(template);
                return this;
            },
            template: '\
                <a href="#"><%- _("Report").t() %></a>\
            '
        });
    }
);
