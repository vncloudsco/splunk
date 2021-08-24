define(
    [
        'module',
        'jquery',
        'underscore',
        'models/Base',
        'views/shared/PopTart',
        'views/shared/federatedsearchcontrols/dialogs/EditFederatedSearchModal',
        'views/shared/documentcontrols/dialogs/permissions_dialog/Master',
        'views/shared/documentcontrols/dialogs/DeleteDialog',
        'util/general_utils',
        'bootstrap.modal'
    ],
    function(
        module,
        $,
        _,
        BaseModel,
        PopTartView,
        EditFederatedSearchModal,
        PermissionsDialog,
        DeleteDialog,
        util,
        bootstrapModal
    ) {
        return PopTartView.extend({
            moduleId: module.id,
             /**
             * @param {Object} options {
             *      model: {
             *          report: <models.search.Report>,
             *          application: <models.Application>,
             *          user: <models.service.admin.user>,
             *          serverInfo: <models.services.server.ServerInfo>,
             *          controller: <Backbone.Model> (Optional)
             *      },
             *      collection: {
             *          fshRoles: <collections.services.authorization.FshRoles>,
             *          searchBNFs: <collections/services/configs/SearchBNFs>
             *          federations: <collections/services/dfs/Federations>
             *      },
             *      {Boolean} deleteRedirect: (Optional) Whether or not to redirect to reports page after delete. Default is false.
             *      {Boolean} showSearchField: (Optional) Whether to display a field to the user for entering the search string.
             *                                    Default is false,
             *      {Function} onOpenFederatedSearchDialog: (Optional) Handler for click on edit search.
             * }
             */
            className: 'dropdown-menu dropdown-menu-narrow',
            initialize: function() {
                PopTartView.prototype.initialize.apply(this, arguments);
                var defaults = {
                    deleteRedirect: false,
                    showSearchField: false
                };

                _.defaults(this.options, defaults);
            },
            events: {
                'click a.edit-description': function(e) {
                    this.hide();
                    this.options.onOpenFederatedSearchDialog();
                    e.preventDefault();
                },
                'click a.edit-permissions': function(e) {
                    this.hide();
                    this.children.permissionsDialog = new PermissionsDialog({
                        model: {
                            document: this.model.report,
                            nameModel: this.model.report.entry,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            application: this.model.application
                        },
                        collection: this.collection.fshRoles,
                        onHiddenRemove: true,
                        nameLabel: _('Federated Search').t(),
                        showDispatchAs: true,
                        federated: true
                    });

                    this.children.permissionsDialog.render().appendTo($("body"));
                    this.children.permissionsDialog.show();
                    this.listenTo(this.children.permissionsDialog, 'hidden', function() {
                        // SPL-111103: Set dispatchAs to owner if report is scheduled.
                        if (this.model.report.entry.content.get('is_scheduled') && this.model.report.entry.content.get('dispatchAs') === 'user') {
                            this.model.report.entry.content.set('dispatchAs', 'owner');
                            this.model.report.save();
                        }
                    });

                    e.preventDefault();
                },
                'click a.delete': function(e){
                    this.hide();
                    this.children.deleteDialog = new DeleteDialog({
                        model: {
                            report: this.model.report,
                            application: this.model.application,
                            controller: this.model.controller
                        },
                        deleteRedirect: this.options.deleteRedirect,
                        onHiddenRemove: true
                    });

                    this.children.deleteDialog.render().appendTo($("body"));
                    this.children.deleteDialog.show();

                    e.preventDefault();
                }
            },
            render: function() {
                var canWrite = this.model.report.canWrite(this.model.user.canScheduleSearch(), this.model.user.canRTSearch()),
                    canDelete = this.model.report.canDelete(),
                    isEmbedded = util.normalizeBoolean(this.model.report.entry.content.get('embed.enabled'));
                var html = this.compiledTemplate({});
                this.$el.html(PopTartView.prototype.template_menu);
                this.$el.append(html);

                if (canWrite && !isEmbedded) {
                    var editDescriptionText = this.options.showSearchField ? _("Edit Search").t() : _("Edit Description").t();
                    this.$('.edit_actions').append('<li><a class="edit-description" href="#">' + editDescriptionText + '</a></li>');

                    // Only show if user has perm to change perms
                    if (this.model.report.entry.acl.get('can_change_perms')) {
                        this.$('.edit_actions').append('<li><a class="edit-permissions" href="#">' + _("Edit Permissions").t() + '</a></li>');
                    }
                } else {
                    this.$('.edit_actions').remove();
                }

                if (canDelete && !isEmbedded) {
                    this.$('.other_actions').append('<li><a href="#" class="delete">' + _("Delete").t() + '</a></li>');
                }
                return this;
            },
            template: '\
                <ul class="edit_actions">\
                </ul>\
                <ul class="other_actions">\
                </ul>\
            '
        });
    }
);
