/**
 * @author claral
 * @date 3/30/16
 *
 * Represents a row in the table. The row contains links to perform
 * operations on the given saved search.
 */
define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'models/Base',
    'models/search/Alert',
    'views/Base',
    'views/shared/alertcontrols/EditMenu',
    'views/shared/alertcontrols/dialogs/edit/Master',
    'views/shared/basemanager/SharingCell',
    'views/shared/basemanager/StatusCell',
    'views/shared/documentcontrols/dialogs/EditSearchDialog',
    'views/shared/reportcontrols/editmenu/Master',
    'views/shared/federatedsearchcontrols/dialogs/EditFederatedSearchModal',
    'views/shared/federatedsearchcontrols/editmenu/Master',
    'contrib/text!views/savedsearches/GridRow.html',
    'util/general_utils',
    'util/string_utils',
    'util/savedsearches/FederatedUtils',
    'uri/route',
    'splunk.util',
    'bootstrap.tooltip'
],
    function (
        $,
        _,
        Backbone,
        module,
        BaseModel,
        AlertModel,
        BaseView,
        AlertEditMenuView,
        AlertEditDialog,
        SharingCellView,
        StatusCellView,
        ReportEditSearchDialog,
        ReportEditMenuView,
        EditFederatedSearchDialog,
        FederatedSearchEditMenuView,
        Template,
        util,
        stringUtils,
        federatedUtils,
        route,
        splunkUtils,
        bootstrapTooltip
        ) {

        return BaseView.extend({
            moduleId: module.id,
            tagName: "tr",
            className: "list-item",
            template: Template,

            events: {
                'click .edit-entity-link': function(e) {
                    var type = this.model.entity.getType();
                    if (type.value === 'federated') {
                        this.handleOpenFederatedSearchDialog();
                    } else if (type.value === 'alert') {
                        this.children.editAlertDialog = new AlertEditDialog({
                            model: {
                                alert: this.model.entity,
                                application: this.model.application,
                                user: this.model.user,
                                serverInfo: this.model.serverInfo,
                                controller: this.model.controller
                            },
                            collection: {
                                alertActions: this.collection.alertActions,
                                searchBNFs: this.collection.searchBNFs
                            },
                            onHiddenRemove: true,
                            showSearchField: true
                        });
                        this.children.editAlertDialog.render().appendTo($("body"));
                        this.children.editAlertDialog.show();
                    } else {
                        this.children.reportEditSearchDialog = new ReportEditSearchDialog({
                            model: {
                                report: this.model.entity,
                                application: this.model.application,
                                user: this.model.user
                            },
                            collection: {
                                searchBNFs: this.collection.searchBNFs
                            },
                            onHiddenRemove: true,
                            showSearchField: true
                        });
                        this.children.reportEditSearchDialog.render().appendTo($("body"));
                        this.children.reportEditSearchDialog.show();
                    }
                    e.preventDefault();
                },
                'click .run-action': function(e) {
                    // use SS app if it's visible, otherwise take app from url
                    var app = this.model.entity.entry.acl.get('app'),
                        isInvisible = this.collection.appLocalsUnfilteredAll.find(function(model) {
                            if (model.entry.get('name') === app &&
                                model.entry.content.get('visible') === false) {
                                return true;
                            }
                        });
                    if (isInvisible) {
                        app = this.model.application.get("app");
                        if (app === 'system') {
                            app = 'search';
                        }
                    }
                    var type = this.model.entity.getType();
                    var data = null;
                    if (type.value === 'federated') {
                        var searchName = this.model.entity.entry.get('name');
                        var query = '| dfsjob [| from federated:"' + searchName + '"]';
                        data = { q: query };
                    } else {
                        data = { s: this.model.entity.id };
                    }
                    window.open(route.search(
                        this.model.application.get("root"),
                        this.model.application.get("locale"),
                        app,
                        {data: data}));
                    e.preventDefault();
                },
                'click .view-recent-action': function(e) {
                    var app = this.model.application.get("app");
                    if (app === 'system') {
                        app = 'search';
                    }
                    window.open(route.job_manager(
                        this.model.application.get("root"),
                        this.model.application.get("locale"),
                        app,
                        {data: {
                            app: this.model.entity.entry.acl.get('app'),
                            filter: "label=\"" + this.model.entity.entry.get('name') + "\""
                        }}));
                    e.preventDefault();
                },
                'click .model-more-description, .model-less-description': function(e) {
                    e.preventDefault();
                    this.$('.model-description-short, .model-description-full').toggle();
                },
                'click .entity-summarization': function(e) {
                    e.preventDefault();
                    if (this.model.user.hasCapability('accelerate_search') &&
                        this.model.user.hasCapability('schedule_search')) {
                        window.open(route.manager(
                            this.model.application.get("root"),
                            this.model.application.get("locale"),
                            'system',
                            ['summarization', this.model.entity.entry.get('name')]
                        ));
                    }
                }
            },

            initialize: function (options) {
                BaseView.prototype.initialize.call(this, options);

                this.children.sharingCell = new SharingCellView({
                    collection: this.collection,
                    model: this.model,
                    showPermissions: false
                });

                this.children.statusCell = new StatusCellView({
                    collection: this.collection,
                    model: this.model
                });

                var type = this.model.entity.getType();
                if (type.value === 'federated') {
                    this.canShowFederatedModal = true;
                    this.model.federatedModalState = new BaseModel({
                        open: false,
                        titleRef: null
                    });

                    this.handleFederatedSearchOpen = this.handleFederatedSearchOpen.bind(this);
                    this.handleFederatedSearchClose = this.handleFederatedSearchClose.bind(this);
                    this.handleEditFederatedSearch = this.handleEditFederatedSearch.bind(this);
                    this.handleFederatedDescriptionChanged = this.handleFederatedDescriptionChanged.bind(this);
                    this.handleFederatedApplicationChanged = this.handleFederatedApplicationChanged.bind(this);
                    this.handleFederatedProviderChanged = this.handleFederatedProviderChanged.bind(this);
                    this.handleOpenFederatedSearchDialog = this.handleOpenFederatedSearchDialog.bind(this);

                    this.createEditFederatedSearchDialog();
                } else if (type.value === 'alert') {
                    this.createEditAlertDialog();
                } else {
                    this.createEditReportDialog();
                }
            },

            handleFederatedSearchOpen: function() {
                this.children.editFederatedSearchDialog.render().appendTo($('body'));
                this.model.federatedModalState.set('open', true);
            },

            handleFederatedSearchClose: function() {
                this.model.federatedModalState.set('open', false);
                var modalClosedListener = setInterval(function() {
                    if (!this.model.federatedModalState.get('titleRef')) {
                        this.children.editFederatedSearchDialog.remove();
                        this.canShowFederatedModal = true;
                        clearInterval(modalClosedListener);
                    }
                }.bind(this), 50);
            },

            handleEditFederatedSearch: function() {
                var validationErrors = this.model.inmem.entry.content.validate();
                if (!validationErrors) {
                    this.model.inmem.save({}, {
                        validate: true,
                        success: function() {
                            this.handleFederatedSearchClose();
                            if (this.model.inmem.get('updated') > this.model.entity.get('updated')) {
                                // now we know have updated the clone
                                this.model.entity.entry.content.set(
                                    this.modelAttribute,
                                    this.model.inmem.entry.content.get(this.modelAttribute)
                                );
                                this.model.entity.entry.set('updated', this.model.inmem.entry.get('updated'));
                                this.model.controller.trigger('refreshEntities');
                            }
                        }.bind(this)
                    });
                }
            },

            handleFederatedDescriptionChanged: function(e, value) {
                this.model.inmem.entry.content.set('description', value.value);
            },

            handleFederatedApplicationChanged: function(e, value) {
                var appLocalModel = this.collection.appLocalsUnfilteredAll.get(value.value);
                this.model.inmem.entry.acl.set('app', appLocalModel.entry.get('name'));
            },

            handleFederatedProviderChanged: function(e, value) {
                var federationModel = this.collection.federations.get(value.value);
                this.model.inmem.entry.content.set('federated.provider', federationModel.entry.get('name'));
            },

            handleOpenFederatedSearchDialog: function() {
                if (this.canShowFederatedModal) {
                    this.canShowFederatedModal = false;
                    this.model.inmem = this.model.entity.clone();
                    this.children.editFederatedSearchDialog = new EditFederatedSearchDialog({
                        model: {
                            inmem: this.model.inmem,
                            application: this.model.application,
                            user: this.model.user,
                            state: this.model.federatedModalState,
                        },
                        collection: {
                            federations: this.collection.federations,
                            searchBNFs: this.collection.searchBNFs
                        },
                        onClose: this.handleFederatedSearchClose,
                        onSubmit: this.handleEditFederatedSearch,
                        onDescriptionChanged: this.handleFederatedDescriptionChanged,
                        onApplicationChanged: this.handleFederatedApplicationChanged,
                        onProviderChanged: this.handleFederatedProviderChanged
                    });
                    this.handleFederatedSearchOpen();
                }
            },

            createEditFederatedSearchDialog: function() {
                this.children.editmenu = new FederatedSearchEditMenuView({
                    model: {
                        application: this.model.application,
                        report: this.model.entity,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo,
                        controller: this.model.controller
                    },
                    collection: {
                        fshRoles: this.collection.fshRoles,
                        searchBNFs: this.collection.searchBNFs,
                        federations: this.collection.federations
                    },
                    button: false,
                    showSearchField: true,
                    onOpenFederatedSearchDialog: this.handleOpenFederatedSearchDialog
                });
            },

            createEditReportDialog: function() {
                this.children.editmenu = new ReportEditMenuView({
                    model: {
                        application: this.model.application,
                        report: this.model.entity,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        serverInfo: this.model.serverInfo,
                        controller: this.model.controller
                    },
                    collection: {
                        roles: this.collection.rolesCollection,
                        appLocals: this.collection.appLocalsUnfilteredAll,
                        searchBNFs: this.collection.searchBNFs,
                        indexes: this.collection.indexes,
                        workloadManagementStatus: this.collection.workloadManagementStatus
                    },
                    button: false,
                    showOpenActions: false,
                    showDisable: true,
                    entitySingular: this.options.entitySingular,
                    showMove: true,
                    showAdvancedEdit: this.model.user.canScheduleSearch() && true,
                    showSearchField: true,
                    showSummaryIndexing: true
                });

                this.listenTo(this.model.entity, 'updateCollection', function() {
                    this.model.controller.trigger('refreshEntities');
                });
                this.listenTo(this.model.entity.entry.acl, 'change:sharing', function() {
                    this.model.controller.trigger('refreshEntities');
                });
                this.listenTo(this.model.entity.entry.content, 'change:disabled', function() {
                    this.model.controller.trigger('refreshEntities');
                });
            },

            createEditAlertDialog: function() {
                // Convert model to alert
                this.model.entity = new AlertModel({}, {splunkDPayload: this.model.entity.toSplunkD()});

                this.children.editmenu = new AlertEditMenuView({
                    model: {
                        savedAlert: this.model.entity,
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo,
                        controller: this.model.controller
                    },
                    collection: {
                        roles: this.collection.rolesCollection,
                        alertActions: this.collection.alertActions,
                        appLocals: this.collection.appLocalsUnfilteredAll,
                        searchBNFs: this.collection.searchBNFs
                    },
                    button: false,
                    showOpenActions: false,
                    entitySingular: this.options.entitySingular,
                    showMove: true,
                    showAdvancedEdit: this.model.user.canScheduleSearch() && true,
                    showSearchField: true
                });

                this.listenTo(this.model.entity, 'updateCollection', function() {
                    this.model.controller.trigger('refreshEntities');
                });
                this.listenTo(this.model.entity.entry.acl, 'change:sharing', function() {
                    this.model.controller.trigger('refreshEntities');
                });
                this.listenTo(this.model.entity.entry.content, 'change:disabled', function() {
                    this.model.controller.trigger('refreshEntities');
                });
            },

            getAlertCount: function() {
                return this.model.entity.entry.content.get('triggered_alert_count') || _('0').t();
            },

            render: function () {
                var showNameLink = true;
                // Hide name link if the entity is a report and the license is free
                if (this.model.entity.isAlert() && !this.model.user.canUseAlerts()) {
                    showNameLink = false;
                }
                // Hide name link if the user lacks permission to edit or the report is embedded.
                if (showNameLink && !this.model.entity.canWrite(this.model.user.canScheduleSearch(), this.model.user.canRTSearch()) ||
                    util.normalizeBoolean(this.model.entity.entry.content.get('embed.enabled'))) {
                    showNameLink = false;
                }

                var html = this.compiledTemplate({
                    model: this.model.entity,
                    canDeleteSourcetype: this.model.entity.entry.links.has('remove'),
                    description: _(this.model.entity.entry.content.get('description') || '').t(),
                    stringUtils: stringUtils,
                    descMaxLength: 300,
                    canViewAccelerated: this.model.user.hasCapability('accelerate_search') &&
                        this.model.user.hasCapability('schedule_search'),
                    isCloud: this.model.serverInfo.isCloud(),
                    alertCount: this.getAlertCount(),
                    showNameLink: showNameLink,
                    canRunFederatedSearches: federatedUtils.canRunFederatedSearches(this.model.user, this.model.serverInfo)
                });

                this.$el.html(html);
                this.children.editmenu.render().prependTo(this.$('.cell-actions'));
                this.children.sharingCell.render().appendTo(this.$('.sharing-cell-placeholder'));
                this.children.statusCell.render().appendTo(this.$('.status-cell-placeholder'));
                this.$('.model-description-full').hide();
                this.$('.tooltip-link').tooltip({animation:false, container: 'body'});

                return this;
            }
        }, {
            columns: [
                {
                    id: 'name',
                    title: _('Name').t()
                }, {
                    id: 'auto_summarize',
                    html: '<span class="accelerate-header visuallyhidden">' + _('Accelerate').t() + '</span><i aria-label="' + _('Accelerate').t() + '" class="icon-lightning"></i>',
                    noSort: true
                }, {
                    id: 'type',
                    title: _('Type').t(),
                    noSort: true
                }, {
                    id: 'next_scheduled_time',
                    title: _('Next Scheduled Time').t()
                }, {
                    id: 'displayview',
                    title: _('Display View').t()
                }, {
                    id: 'eai:acl.owner',
                    title: _('Owner').t()
                }, {
                    id: 'eai:acl.app',
                    title: _('App').t()
                }, {
                    id: 'triggered_alert_count',
                    title: _('Alerts').t()
                }, {
                    id: 'eai:acl.sharing',
                    title: _('Sharing').t()
                }, {
                    id: 'disabled',
                    title: _('Status').t()
                }
            ]
        });
    });
