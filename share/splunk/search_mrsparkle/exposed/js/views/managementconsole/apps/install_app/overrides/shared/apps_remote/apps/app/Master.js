define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'uri/route',
    'models/managementconsole/Task',
    'views/shared/apps_remote/apps/app/Master',
    'views/managementconsole/apps/app_listing/actionflows/installapp/Master',
    'views/managementconsole/apps/app_listing/actionflows/update/Master'
], function(
        $,
        _,
        Backbone,
        module,
        route,
        TaskModel,
        AppView,
        InstallDialog,
        UpdateDialog
){
    return AppView.extend({
        moduleId: module.id,
        installMethodKey: 'install_method_distributed',

        initialize: function(options) {
            AppView.prototype.initialize.call(this, options);

            this.listenTo(this.collection.appLocals, 'sync', this.render);
            this.listenTo(this.collection.dmcApps, 'sync', this.render);

            this.model.deployTask = new TaskModel();
            this.model.confirmation = new Backbone.Model();
            this.listenTo(this.model.confirmation, 'installApp', this.showDialog);
        },

        events: $.extend({}, AppView.prototype.events, {
            'click .install-button': function(e) {
                e.preventDefault();

                var confirmDialog = new InstallDialog({
                    model: {
                        app: this.model.dmcApp,
                        appRemote: this.model.appRemote,
                        auth: this.model.auth,
                        application: this.model.application,
                        deployTask: this.model.deployTask
                    },
                    collection: {
                        appLocalsUnfiltered: this.collection.appLocalsUnfiltered
                    },
                    willDeploy: true,
                    isSHC: this.options.isSHC
                });

                this.$('body').append(confirmDialog.render().el);
                confirmDialog.on('hide', function() {
                    // fetch collections when the dialog is closed, this refreshes
                    // state of "install" button
                    this.fetchAppsCollections();
                }, this);
                confirmDialog.show();
            },

            'click .update-button': function(e) {
                e.preventDefault();

                var appId = this.model.appRemote.get('appid'),
                    dmcApp = this.collection.dmcApps.findByEntryName(appId),
                    updateDialog = new UpdateDialog({
                        willDeploy: true,
                        model: {
                            app: dmcApp,
                            deployTask: this.model.deployTask,
                            auth: this.model.auth
                        },
                        getSuccessPromises: function() {
                            return [this.fetchAppsCollections()];
                        }.bind(this),
                        primFn: dmcApp.update.bind(dmcApp)
                    });

                $("body").append(updateDialog.render().el);
                updateDialog.show();
            }
        }),

        // Fetch Both dmcApps and appLocals collections to update the app browser entry
        fetchAppsCollections: function() {
            this.collection.appLocals.fetch();
            this.collection.dmcApps.fetch();
        },

        render: function () {
            var permission = this.model.user.hasCapability('dmc_deploy_apps') ? true: false;
            return AppView.prototype.render.apply(this, [permission]);
        },

        cloudRender: function(install_method) {
            var appId = this.model.appRemote.get('appid'),
                localApp = this.collection.appLocals.findByEntryName(appId),
                localAppUnfiltered = this.collection.appLocalsUnfiltered.findByEntryName(appId),
                dmcApp = this.collection.dmcApps.findByEntryName(appId),
                // SPL-132754: We also need to check that the localApp is not a "dummy" app
                // We can do this by determining if its version is defined
                // This is not a general solution per se, but it works for all apps that we
                // allow to be installed in the cloud.
                localAppUnfilteredVersion = localAppUnfiltered && localAppUnfiltered.entry.content.get('version'),
                supportedDeployments = ((this.model.appRemote.get('release') || {})['manifest'] || {})
                    ['supportedDeployments'];

            if (dmcApp && (dmcApp.hasUpdate() && dmcApp.canUpdate())) {
                // Add update button for DMC apps
                return this.getDmcAppUpdateButton(dmcApp);
            } else if (localApp && localApp.entry.links.has('update')) {
                // Add update button for non-DMC apps installed on the SH
                return AppView.prototype.cloudRender.apply(this, arguments);
            } else if (dmcApp && localApp) {
                // Add open button for DMC apps that are installed on the SH
                var appLink = route.prebuiltAppLink(this.model.application.get('root'), this.model.application.get('locale'), appId, '');
                return {
                    buttonText: _('Open App').t(),
                    link: appLink
                };
            } else if (localAppUnfilteredVersion && (localAppUnfiltered || dmcApp)) {
                // Add installed button for non-visible SH apps, or apps not installed on the SH
                return {
                    buttonText: _('Already Installed').t(),
                    buttonClass: 'disabled'
                };
            } else if (this.options.isSHC && supportedDeployments &&
                       !(_.contains(supportedDeployments, '*') ||
                         _.contains(supportedDeployments, '_search_head_clustering'))) {
                return {
                    buttonText: _('Not Compatible').t(),
                    buttonClass: 'disabled',
                    messageText: _('App does not support search head cluster deployments.').t()
                };
            } else {
                // Add install or request install button for remainder of the apps
                switch(install_method) { 

                    // This should never happen.
                    // If an app is ever flagged as "simple" in a AppManagement-Cloud
                    // environment, this means that this app should be installable,
                    // but only outside of AppManagement, therefore CloudOps needs to
                    // be involved --> we resolve this case to 'assisted' here.
                    case 'simple':
                        return AppView.prototype.cloudRender.call(this, 'assisted');

                    // This case is logically the 'simple' case, but specific to
                    // AppManagement-Cloud environments.
                    // This flag indicates that this app is installable by AppManagement
                    // cloud environments but not by other Cloud environments.
                    case 'appmgmt_phase':
                        return this.getDmcAppInstallButton();

                    default:
                        return AppView.prototype.cloudRender.apply(this, arguments);
                }
            }
        },

        localRender: function(appId, localApp) {
            var dmcApp = this.collection.dmcApps.findByEntryName(appId);

            if (dmcApp && (dmcApp.hasUpdate() && dmcApp.canUpdate())) {
                return this.getDmcAppUpdateButton(dmcApp);

            } else if (dmcApp && dmcApp.isPrivate()) {
                // SPL-143097 - if we have a private dmc app, we cannot know
                // that it is the same as the public app -> inform the user
                // of this by showing a warning.
                return {
                    messageText: _('You have a private app installed with the same id as this app. ' +
                        'Update your private app with a unique id to remove this conflict.').t(),
                    buttonText: _('App ID Conflict').t(),
                    buttonClass: 'disabled'
                };

            } else if (!dmcApp && localApp && !localApp.entry.content.get('version')) {
                // SPL-138787 - if app does not exist in DMC, but is invalid
                // (e.i. installed locally without a version) -> allow the
                // user to re-install the app.
                return this.getDmcAppInstallButton(dmcApp);

            } else {
                // SPL-138555 - if dmc does not have an update for app ->
                // unset the 'update' link on local app model so that users
                // are not asked to 'Request Update'
                localApp.entry.links.unset('update');
                return AppView.prototype.localRender.apply(this, arguments);
            }
        },

        getDmcAppUpdateButton: function(dmcApp) {
            if (dmcApp.canEdit()) {
                return {
                    buttonText: _('Update').t(),
                    buttonClass: 'update-button'
                };
            } else {
                return {
                    messageText: _('You do not have permission to update this app.').t(),
                    buttonText: _('Update').t(),
                    buttonClass: 'disabled'
                };
            }
        },

        getDmcAppInstallButton: function() {
            if (this.model.user.hasCapability('dmc_deploy_apps')) {
                return {
                    buttonText: _('Install').t(),
                    buttonClass: 'btn-primary install-button'
                };
            } else {
                return {
                    messageText: _('You do not have permission to install this app.').t(),
                    buttonText: _('Install').t(),
                    buttonClass: 'disabled'
                };
            }
        }
    });
});
