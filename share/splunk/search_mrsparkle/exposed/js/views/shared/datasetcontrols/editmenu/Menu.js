define(
    [
        'module',
        'jquery',
        'underscore',
        'models/search/ScheduledReport',
        'models/services/datamodel/DataModel',
        'models/services/datasets/PolymorphicDataset',
        'views/shared/PopTart',
        'views/shared/datasetcontrols/editmenu/FetchDeleteDialog',
        'views/shared/datasetcontrols/editmenu/FetchAccelerationDialog',
        'views/shared/documentcontrols/dialogs/TitleDescriptionDialog',
        'views/shared/documentcontrols/dialogs/DeleteDialog',
        'views/shared/documentcontrols/dialogs/permissions_dialog/Master',
        'views/shared/reportcontrols/dialogs/schedule_dialog/Master',
        'views/data_model_manager/components/PermissionsDialog',
        'uri/route',
        'util/string_utils'
    ],
    function(
        module,
        $,
        _,
        ScheduledReportModel,
        DataModel,
        PolymorphicDatasetModel,
        PopTartView,
        FetchDeleteDialog,
        FetchAccelerationDialog,
        TitleDescriptionDialog,
        DeleteDialog,
        PermissionsDialog,
        ScheduleDialog,
        DataModelPermissionsDialog,
        route,
        stringUtil
    ) {
        return PopTartView.extend({
            moduleId: module.id,
            className: 'dropdown-menu dropdown-menu-narrow',

            initialize: function() {
                PopTartView.prototype.initialize.apply(this, arguments);

                var defaults = {
                    button: true,
                    deleteRedirect: false,
                    fetchDelete: false
                };

                _.defaults(this.options, defaults);
            },

            events: {
                'click a.edit-description': function(e) {
                    this.hide();
                    this.children.titleDescriptionDialog = new TitleDescriptionDialog({
                        model: {
                            report: this.model.dataset
                        },
                        onHiddenRemove: true
                    });

                    this.children.titleDescriptionDialog.render().appendTo($("body")).show();

                    e.preventDefault();
                },

                'click a.delete': function(e) {
                    this.hide();
                    this.children.deleteDialog = new DeleteDialog({
                        model: {
                            dataset: this.model.dataset,
                            application: this.model.application
                        },
                        deleteRedirect: this.options.deleteRedirect,
                        onHiddenRemove: true
                    });

                    this.children.deleteDialog.render().appendTo($("body"));
                    this.children.deleteDialog.show();

                    e.preventDefault();
                },

                'click a.fetch-delete': function(e) {
                    this.hide();
                    this.children.fetchDeleteDialog = new FetchDeleteDialog({
                        model: {
                            dataset: this.model.dataset,
                            application: this.model.application
                        },
                        deleteRedirect: this.options.deleteRedirect,
                        onHiddenRemove: true
                    });

                    this.children.fetchDeleteDialog.render().appendTo($("body"));
                    this.children.fetchDeleteDialog.show();

                    e.preventDefault();
                },

                'click a.edit-permissions': function(e) {
                    var PermissionsDialogConstructor = PermissionsDialog,
                        // Remember that PolymorphicDatasetModel.DATAMODEL is a Datamodel Dataset. The reason why those aren't acceleratable is that you have to accelerate the
                        // parent Datamodel itself, which means that many Datamodel Datasets in the Datasets Listings page would be accelerated at once.
                        acceleratable = this.model.dataset.typeCanBeAccelerated() && (this.model.dataset.getType() !== PolymorphicDatasetModel.DATAMODEL),
                        originalACL = this.model.dataset.entry.acl.toJSON(),
                        fetchDatasetDeferred = $.Deferred();

                    if (acceleratable) {
                        PermissionsDialogConstructor = DataModelPermissionsDialog;
                        this.model.dataset.fetch({
                            success: function(model, response) {
                                fetchDatasetDeferred.resolve();
                            }.bind(this),
                            error: function(model, response) {
                                fetchDatasetDeferred.resolve();
                            }.bind(this)
                        });
                    } else {
                        fetchDatasetDeferred.resolve();
                    }

                    this.hide();

                    $.when(fetchDatasetDeferred).then(function() {
                        this.children.permissionsDialog = new PermissionsDialogConstructor({
                            model: {
                                document: this.model.dataset,
                                nameModel: this.model.dataset.entry,
                                user: this.model.user,
                                serverInfo: this.model.serverInfo,
                                application: this.model.application
                            },
                            collection: this.collection.roles,
                            onHiddenRemove: true,
                            nameLabel: this.model.dataset.getDatasetDisplayType()
                        });

                        this.children.permissionsDialog.render().appendTo($("body"));
                        this.children.permissionsDialog.show();

                        if (acceleratable) {
                            this.listenTo(this.children.permissionsDialog, 'hidden', function() {
                                var currentACL = this.model.dataset.entry.acl.toJSON();

                                // Now, this is going to sound strange, because it is, but we have
                                // to POST the datamodel back to the datamodel endpoint after changing the ACL
                                // to ensure that the conf entry is in the correct state, regardless of what any GET
                                // after the ACL POST tells us.
                                if (!_.isEqual(currentACL, originalACL) && (currentACL.sharing === 'user')) {
                                    this.model.dataset.entry.content.acceleration.set('enabled', 0);
                                    this.model.dataset.save({}, {
                                        success: function(model, response) {
                                            this.model.dataset.entry.content.set('accelerated', false);
                                            if (this.model.state) {
                                                this.model.state.trigger('change:search');
                                            }
                                        }.bind(this)
                                    });
                                }
                                this.remove();
                            }.bind(this));
                        }
                    }.bind(this));

                    e.preventDefault();
                },

                'click a.edit-acceleration': function(e) {
                    this.hide();

                    this.children.fetchAccelerationDialog = new FetchAccelerationDialog({
                        model: {
                            dataset: this.model.dataset,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            application: this.model.application
                        },
                        collection: {
                            roles: this.collection.roles
                        },
                        onHiddenRemove: false,
                        nameLabel: stringUtil.capitalize(this.model.dataset.getDatasetDisplayType())
                    });

                    this.children.fetchAccelerationDialog.render().appendTo($("body"));
                    this.children.fetchAccelerationDialog.show();

                    e.preventDefault();
                },

                'click a.schedule-dataset': function(e) {
                    e.preventDefault();
                    this.hide();

                    this.model.report = new ScheduledReportModel();
                    $.when(this.model.report.fetch({
                        data: {
                            app: this.model.application.get('app'),
                            owner: this.model.application.get('owner')
                        }
                    })).then(function() {
                        this.model.report.entry.content.set({
                            'search': this.model.dataset.getFromSearch(),
                            'is_scheduled': true,
                            'disabled': false,
                            'dispatch.earliest_time': this.model.dataset.entry.content.get('dispatch.earliest_time'),
                            'dispatch.latest_time': this.model.dataset.entry.content.get('dispatch.latest_time')
                        });

                        this.children.scheduleDialog = new ScheduleDialog({
                            model: {
                                application: this.model.application,
                                report: this.model.report,
                                timeRange: this.model.timeRange,
                                user: this.model.user
                            },
                            collection: {
                                roles: this.collection.roles,
                                times: this.collection.times
                            },
                            successMessage: _('You have successfully created and scheduled a report from this dataset.').t()
                        });

                        this.children.scheduleDialog.render().appendTo($('body')).show();
                    }.bind(this));
                }
            },

            render: function() {
                var canWrite = this.model.dataset.canWrite(),
                    showScheduleLink = this.options.showScheduleLink && this.model.user.canScheduleSearch(),
                    canDelete = this.model.dataset.canDelete(),
                    canTable = this.model.dataset.canTable() && this.model.user.canAccessSplunkDatasetExtensions(),
                    canEditDescription = this.model.dataset.canEditDescription(),
                    canEditPermission = this.model.dataset.canEditPermissions(),
                    canAccelerateDatamodels = this.model.user.canAccelerateDataModel(),
                    canAccelerateDatasetType = this.model.dataset.typeCanBeAccelerated(),
                    type = this.model.dataset.getType(),
                    datasetName = this.model.dataset.getFromName(),
                    fromType = this.model.dataset.getFromType(),
                    canFetchDelete = this.options.fetchDelete && (type !== PolymorphicDatasetModel.DATAMODEL),
                    fromQuery = '| from ' + fromType + ':"' + datasetName + '"',
                    extendTableLink = route.table(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get('app'),
                        { data: {
                            bs: fromQuery
                        }
                    }),
                    editLink,
                    editType;

                if (type === DataModel.DOCUMENT_TYPES.TABLE) {
                    if (canTable) {
                        editType = _('Edit Table').t();
                        editLink = route.table(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            this.model.application.get('app'),
                            {
                                data: {
                                    t: this.model.dataset.id
                                }
                            }
                        );
                    }

                } else if (type === PolymorphicDatasetModel.LOOKUP_TRANSFORM) {
                    editType = _('Edit Lookup Definition').t();
                    editLink = route.managerEdit(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get('app'),
                        ['data', 'transforms', 'lookups', this.model.dataset.entry.content.get('name')],
                        this.model.dataset.id
                    );

                } else if (type === PolymorphicDatasetModel.LOOKUP_TABLE) {
                    editType = _('Edit Lookup Table Files').t();
                    editLink = route.manager(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get('app'),
                        ['data', 'lookup-table-files']
                    );

                } else if (type === PolymorphicDatasetModel.DATAMODEL) {
                    editType = _('Edit Data Model').t();

                    editLink = route.data_model_editor(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get('app'),
                        {
                            data: {
                                model: this.model.dataset.entry.content.get('parent.link')
                            }
                        }
                    );
                }

                this.$el.html(PopTartView.prototype.template_menu);
                this.$el.append(this.compiledTemplate({
                    _: _,
                    button: this.options.button,
                    dataset: this.model.dataset,
                    user: this.model.user,
                    editLink: editLink,
                    editType: editType
                }));

                if (canWrite) {
                    if (editLink) {
                        this.$('.edit_actions').append('<li><a class="edit-link" href="' + editLink + '">' + editType + '</a></li>');
                    }

                    if (canEditDescription) {
                        this.$('.edit_actions').append('<li><a class="edit-description" href="#">' + _("Edit Description").t() + '</a></li>');
                    }

                    if (canEditPermission && this.model.dataset.entry.acl.get('can_change_perms')) {
                        this.$('.edit_actions').append('<li><a class="edit-permissions" href="#">' + _("Edit Permissions").t() + '</a></li>');
                    }

                    if (canAccelerateDatamodels && canAccelerateDatasetType && (type !== PolymorphicDatasetModel.DATAMODEL)) {
                        this.$('.edit_actions').append('<li><a class="edit-acceleration" href="#">' + _("Edit Acceleration").t() + '</a></li>');
                    }
                } else {
                    this.$('.edit_actions').remove();
                }

                if (canTable) {
                    this.$('.other_actions').append('<li><a href="' + extendTableLink + '" class="extend">' + _("Extend in Table").t() + '</a></li>');
                }

                if (showScheduleLink) {
                    this.$('.other_actions').append('<li><a href="#" class="schedule-dataset">' + _("Schedule Report").t() + '</a></li>');
                }

                if (canDelete) {
                    this.$('.other_actions').append('<li><a href="#" class="delete">' + _("Delete").t() + '</a></li>');
                } else if (canFetchDelete) {
                    this.$('.other_actions').append('<li><a href="#" class="fetch-delete">' + _("Delete").t() + '</a></li>');
                }

                if (!canFetchDelete && !canDelete && !canTable && !showScheduleLink) {
                    this.$('.other_actions').remove();
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
