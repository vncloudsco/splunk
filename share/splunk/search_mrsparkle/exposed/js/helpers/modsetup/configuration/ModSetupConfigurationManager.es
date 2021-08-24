/**
 * Manage configurations of all the associated apps
 */
import $ from 'jquery';
import _ from 'underscore';
import ModSetupConfiguration from './ModSetupConfigurationHelper';

export default class ModSetupConfigurationManager {

    constructor(options) {
        this.options = options;
        this.configurations = {};

        this.isEditAll = this.options.isEditAll || false;
        this.mainApp = this.options.app;
        this.appsSetupDeferreds = [];
        this.appsFetchDeferred = $.Deferred();
    }

    createConfiguration(app) {
        this.configurations[app] = new ModSetupConfiguration({
            bundleId: app,
            isDMCEnabled: this.options.isDMCEnabled,
        });
        return this.configurations[app];
    }

    // Returnes true if apps have setup
    requiresSetup() {
        const configs = _.values(this.configurations);
        return configs.some(config => config.hasSetup);
    }

    checkDeferredsStatus() {
        let allAppsFetchResolved = true;
        _.each(this.appsSetupDeferreds, (deferred) => {
            if (deferred.state() === 'pending') {
                allAppsFetchResolved = false;
            }
        });

        if (allAppsFetchResolved) {
            this.appsFetchDeferred.resolve();
        }
    }

    fetchConfigAppsList(app) {
        const configuration = this.createConfiguration(app);
        const deferred = configuration.getSetup();
        this.appsSetupDeferreds.push(deferred);

        // check status after complete
        $.when(deferred).always(() => {
            const dependencies = configuration.dependencies;
            if (!_.isEmpty(dependencies)) {
                _.each(dependencies, (dep) => {
                    this.fetchConfigAppsList(dep);
                });
            }
            this.checkDeferredsStatus();
        });

        return this.appsFetchDeferred;
    }

    get apps() {
        const appsList = [];

        _.each(_.keys(this.configurations), (name) => {
            if (this.configurations[name].getNeedsConfiguration(this.isEditAll)) {
                appsList.push({
                    label: this.configurations[name].label,
                    value: name,
                    parentApp: this.mainApp === name,
                    hasSetup: this.configurations[name].hasSetup,
                });
            }
        });

        return appsList;
    }
}
