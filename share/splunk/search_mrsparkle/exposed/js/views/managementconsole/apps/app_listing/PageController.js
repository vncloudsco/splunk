define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'controllers/BaseManagerPageController',
        'models/managementconsole/App',
        'models/apps_remote/ProxyLogin',
        'models/services/shcluster/Config',
        'collections/managementconsole/Apps',
        'views/managementconsole/apps/app_listing/Grid',
        'views/managementconsole/apps/app_listing/GridRow',
        'views/managementconsole/apps/app_listing/MoreInfo',
        'views/managementconsole/apps/app_listing/ActionCell',
        'views/managementconsole/apps/app_listing/controls/SuccessDialog',
        'views/managementconsole/apps/app_listing/actionflows/statuschange/Master',
        'views/managementconsole/apps/app_listing/actionflows/uninstall/Master',
        'views/managementconsole/apps/app_listing/actionflows/update/Master',
        'views/managementconsole/apps/app_listing/controls/PermissionsDialog',
        'views/managementconsole/apps/app_listing/controls/CreateAppDialog',
        'views/managementconsole/apps/app_listing/NewButtons',
        'views/shared/controls/SyntheticSelectControl',
        'views/managementconsole/shared/TopologyProgressControl',
        'helpers/managementconsole/url',
        'views/shared/pcss/basemanager.pcss',
        'views/managementconsole/shared.pcss',
        './PageController.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        BaseController,
        AppModel,
        LoginModel,
        ShClusterModel,
        AppsCollection,
        Grid,
        GridRow,
        MoreInfo,
        ActionCell,
        SuccessDialog,
        StatusChangeDialog,
        UninstallDialog,
        UpdateDialog,
        PermissionsDialog,
        CreateAppDialog,
        NewButtons,
        SyntheticSelectControl,
        TopologyProgressControl,
        urlHelper,
        cssBaseManager,
        cssShared,
        css
    ) {
        return BaseController.extend({
            moduleId: module.id,
            className: [BaseController.prototype.className, 'app-listing'].join(' '),

            initialize: function(options) {
                this.model = this.model || {};

                var newAppLinkHref = urlHelper.appBrowserUrl(),
                    appOperation = urlHelper.getUrlParam('operation'),
                    appLabel = urlHelper.getUrlParam('appLabel'),
                    appVersion = urlHelper.getUrlParam('appVersion'),
                    packageName = urlHelper.getUrlParam('packageName');

                this.appsLocalMap = {};
                this.updateAppLocalsMap();

                this.deferreds = this.deferreds || {};
                this.model.ShClusterConfig = new ShClusterModel();
                this.deferreds.ShClusterConfigReady = this.model.ShClusterConfig.fetch();

                options = $.extend(true, options, {
                    header: {
                        pageTitle: _('Apps').t(),
                        pageDesc: _('App Management lets you view and manage your Splunk apps. You can install applications, view dependencies, and download app packages to deploy manually to forwarders.').t()
                    },
                    learnMoreLink: '', // TODO
                    noEntitiesMessage: _('No apps found.').t(),
                    entitySingular: _('App').t(),
                    entitiesPlural: _('Apps').t(),
                    deleteDialogButtonLabel: _('Uninstall').t(),
                    entityModelClass: AppModel,
                    entitiesCollectionClass: AppsCollection,
                    deferreds: {
                        deployModel: this.model.deployModel.fetch()
                    },
                    grid: {
                        showAppFilter: false,
                        showOwnerFilter: false,
                        showSharingColumn: false,
                        showStatusColumn: false
                    },
                    customViews: {
                        Grid: Grid,
                        GridRow: GridRow,
                        ActionCell: ActionCell,
                        NewButtons: NewButtons,
                        MoreInfo: MoreInfo
                    },
                    editLinkHref: newAppLinkHref,
                    appsLocalMap: this.appsLocalMap,
                    syncAppsLocal: this.syncAppsLocal
                });

                BaseController.prototype.initialize.call(this, options);

                this.model.state = this.model.state || new Backbone.Model();

                this.model.auth = new LoginModel();

                this.children.progressControl = new TopologyProgressControl({
                    model: {
                        topologyTask: this.model.deployTask,
                        user: this.model.user
                    },
                    onDeployTaskSuccessCB: function() {
                        return $.when(this.syncApps(), this.updateSplunkBarApps());
                    }.bind(this)
                });

                this.children.appTypeFilter = new SyntheticSelectControl({
                    label: _('Install Type:').t(),
                    menuWidth: 'narrow',
                    className: 'btn-group',
                    items: [
                        {value: '*', label: _('All').t()},
                        {value: 'external', label: _('Splunk').t()},
                        {value: 'self-service', label: _('Self-Service').t()}
                    ],
                    model: this.model.state,
                    modelAttribute: 'serviceability',
                    toggleClassName: 'btn-pill',
                    popdownOptions: {
                        detachDialog: true
                    }
                });

                if (appOperation && appLabel && appVersion) {
                    this.openSuccessDialog(appOperation, appLabel, appVersion);
                } else if (packageName) {
                    this.openSuccessDialog(packageName);
                }

                this.model.state.on('change:serviceability', this.handleServiceabilityFilterChange.bind(this));

                this.model.controller.on('toggleUpdateChecking', this.toggleUpdateChecking.bind(this));
                this.model.controller.on('toggleVisibility', this.toggleVisibility.bind(this));
                this.model.controller.on('toggleStatus', this.openStatusDialog.bind(this));
                this.model.controller.on('editPermissions', this.handleEditPermissions.bind(this));
                this.model.controller.on('updateApp', this.openUpdateDialog.bind(this));
                this.model.controller.on('uninstallApp', this.openUninstallDialog.bind(this));
                this.model.controller.on('createApp', this.openCreateAppDialog.bind(this));

                this.model.deployTask.on('syncApps', this.syncApps.bind(this));
                this.collection.appsLocal.on('sync', this.updateAppLocalsMap.bind(this));
            },

            openCreateAppDialog: function() {
                var createAppDialog = new CreateAppDialog({});

                $('body').append(createAppDialog.render().el);
                createAppDialog.show();
            },

            syncApps: function() {
                return this.collection.entities.fetch().done(this.collection.appsLocal.fetch.bind(this.collection.appsLocal));
            },

            // Construct map to perform merge with apps from dmc/apps
            // in O(n). Merge is required to not duplicate work / information
            // already available to us through apps/local endpoint
            // maps: name -> app model
            updateAppLocalsMap: function() {
                this.collection.appsLocal.each(function(app) {
                    this.appsLocalMap[app.entry.get('name')] = app;
                }.bind(this));

                this.collection.appsLocal.trigger('syncAppsLocal', this.appsLocalMap);
            },

            syncAppsLocal: function(updatedAppsLocalMap) {
                var prevAppLocalModel = this.model.appLocal;
                this.appsLocalMap = updatedAppsLocalMap;
                this.model.appLocal = this.appsLocalMap[this.model.entity.entry.get('name')];

                this.stopListening(prevAppLocalModel);
                this.listenTo(this.model.appLocal, 'sync', this.render);

                this.render();
            },

            render: function() {
                BaseController.prototype.render.apply(this, arguments);

                $.when(this.renderDfd).then(function() {
                    this.children.progressControl.render().insertAfter($('.text-name-filter-placeholder'));
                    this.children.appTypeFilter.render().insertBefore($('.text-name-filter-placeholder'));
                }.bind(this));

                return this;
            },

            handleServiceabilityFilterChange: function(model, newVal) {
                switch (newVal) {
                    case 'external':
                            this.model.metadata.setQueryAttr('external', true);
                        break;
                    case 'self-service':
                            this.model.metadata.setQueryAttr('external', false);
                        break;
                    default:
                        this.model.metadata.unsetQueryAttr('external');
                }
            },

            openSuccessDialog: function(appOperation, appLabel, appVersion) {
                var packageName,
                    successDialog,
                    dialogOptions = {};

                if (appLabel && appVersion) {
                    urlHelper.removeUrlParam('operation');
                    urlHelper.removeUrlParam('appLabel');
                    urlHelper.removeUrlParam('appVersion');

                    dialogOptions = {
                        operation: appOperation,
                        appLabel: appLabel,
                        appVersion: appVersion
                    };
                } else if (appOperation) {
                    // Only appOperation was passed, so this is just a packagName
                    // case
                    packageName = appOperation;
                    urlHelper.removeUrlParam('packageName');

                    dialogOptions = {
                        operation: 'install',
                        appLabel: packageName
                    };
                }

                successDialog = new SuccessDialog(dialogOptions);
                 $('body').append(successDialog.render().el);
                successDialog.show();
            },

            // General Note on executing REST call on a model for basemanager:
            // Always make a clone of it before any functions like app.update,
            // app.uninstall, etc. This way if the call ends with a error on the
            // model, it will not automatically display the error message below the table row
            openUninstallDialog: function(appModel) {
                var uninstallDialog = new UninstallDialog({
                    willDeploy: true,
                    model: {
                        app: appModel.clone(),
                        deployTask: this.model.deployTask
                    },
                    getSuccessPromises: function() {
                        return [this.fetchEntitiesCollection()];
                    }.bind(this),
                    primFn: appModel.uninstall.bind(appModel)
                });

                $('body').append(uninstallDialog.render().el);
                uninstallDialog.show();
            },

            openUpdateDialog: function(appModel) {
                var dmcApp = appModel.clone(),
                    updateDialog = new UpdateDialog({
                    willDeploy: true,
                    model: {
                        app: dmcApp,
                        deployTask: this.model.deployTask,
                        auth: this.model.auth
                    },
                    getSuccessPromises: function() {
                        return [this.fetchEntitiesCollection()];
                    }.bind(this),
                    primFn: appModel.update.bind(dmcApp)
                });

                $("body").append(updateDialog.render().el);
                updateDialog.show();
            },

            openStatusDialog: function(appModel) {
                var appLocal = this.appsLocalMap[appModel.entry.get('name')],
                    isExternalApp = appModel.isExternal(),
                    app = isExternalApp ? appLocal.clone() : appModel.clone(),
                    appName = isExternalApp ? appLocal.getTitle() : appModel.getAppLabel(),
                    appVersion = app.getVersion(),
                    isDisabled = appLocal.entry.content.get('disabled'),
                    primFn = isDisabled ? app.enable.bind(app) : app.disable.bind(app);

                var getSuccessPromises = function() {
                    return [
                        appLocal.fetch.call(appLocal),
                        appModel.fetch.call(appModel),
                        this.updateSplunkBarApps.call(this)
                    ];
                }.bind(this);

                var dialog = new StatusChangeDialog({
                        operation: isDisabled ? 'enable' : 'disable',
                        appName: appName,
                        appVersion: appVersion,
                        isDisabled: isDisabled,
                        primFn: primFn,
                        willDeploy: isExternalApp ? false : true,
                        model: {
                            app: app,
                            deployTask: this.model.deployTask
                        },
                        getSuccessPromises: getSuccessPromises
                    });

                $('body').append(dialog.render().el);
                dialog.show();
            },

            handleEditPermissions: function(appModel) {
                var appLocal = this.appsLocalMap[appModel.entry.get('name')],
                    permissionsDialog = new PermissionsDialog({
                    model: {
                        app: appLocal,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo
                    },
                    collection: {
                        roles: this.collection.roles
                    }
                });

                $('body').append(permissionsDialog.render().el);
                permissionsDialog.show();
            },

            toggleUpdateChecking: function(appModel) {
                var appLocal = this.appsLocalMap[appModel.entry.get('name')];
                appLocal.toggleUpdateChecking();
                appLocal.save();
            },

            toggleVisibility: function(appModel) {
                var appLocal = this.appsLocalMap[appModel.entry.get('name')];
                appLocal.toggleVisibility();
                appLocal.save().done(this.updateSplunkBarApps.bind(this));
            },

            updateSplunkBarApps: function() {
                // fetch data taken from views/shared/splunkbar/Master.js
                return this.collection.appLocals.fetch({
                    data: {
                        sort_key: 'name',
                        sort_dir: 'asc',
                        app: '-' ,
                        owner: this.model.application.get('owner'),
                        search: 'visible=true AND disabled=0 AND name!=launcher',
                        count: -1
                    }
                });
            }
        });
    }
);
