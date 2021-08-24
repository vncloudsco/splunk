define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/jobcontrols/menu/EditModal'
    ],
    function($, _, module, BaseView, EditModal) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'edit',
            tagName: 'li',
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },
            events: {
                'click a[class!="disabled"]': function(e) {
                    this.children.editModal = new EditModal({
                        model: {
                            searchJob: this.model.searchJob,
                            application: this.model.application,
                            report: this.model.report,
                            user: this.model.user
                        },
                        collection: {
                            workloadManagementStatus: this.collection.workloadManagementStatus
                        },
                        onHiddenRemove: true,
                        externalJobLinkPage: this.options.externalJobLinkPage
                    });

                    this.children.editModal.render().appendTo($("body"));
                    this.children.editModal.show();

                    e.preventDefault();
                },
                'click a.disabled': function(e) {
                    e.preventDefault();
                }
            },
            render: function() {
                this.$el.html('<a href="#" aria-disabled="false">' + _("Edit Job Settings...").t() + '</a>');
                var canWrite = this.model.searchJob.entry.acl.canWrite();
                if (!this.model.searchJob.entry.acl.canWrite()) {
                    this.$('a').addClass('disabled').attr('aria-disabled', 'true');
                    
                }
                return this;
            }
        }
    );
});
