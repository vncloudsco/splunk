/**
 * Responsible for loading configurations for app
 */
import AppDependenciesInfoModel from 'models/modsetup/AppDependenciesInfo';
import ModSetupConfCollection from 'collections/modsetup/ModSetupSplunkDConfs';
import $ from 'jquery';
import _ from 'underscore';
import SplunkUtil from 'splunk.util';
import SplunkDUtils from 'util/splunkd_utils';
import { TYPES } from 'helpers/modsetup/managers/ModSetupTypes';

const REQUIRED_CONF_PROPERTIES = ['file', 'stanzas', 'properties'];

export default class ModSetupConfigurationHelper {

    constructor(options) {
        this.options = options;
    }

    /**
     * Fetch all the configuration (setup.json and setup.html) for the app
     * @returns {*}
     */
    getSetup() {
        // eslint-disable-next-line new-cap
        const fetchDefered = $.Deferred();
        const deferreds = this.fetchConfiguration();
        let count = 0;

        _.each(deferreds, (def) => {
            def.always(() => {
                if (this.json && this.html) {
                    this.hasSetup = true;
                }
                count += 1;
                if (count === deferreds.length) {
                    fetchDefered.resolve();
                }
            });
        });

        return fetchDefered;
    }


    fetchConfiguration() {
        const deferreds = [];

        if (this.options.isDMCEnabled) {
            // For now throw new error when DMC is enabled
            throw new Error('Not supported');
        } else {
            const jsonUrl = `/static/app/${this.options.bundleId}/setup.json`;
            deferreds.push(this.fetchConfigJson(jsonUrl));

            const htmlUrl = `/static/app/${this.options.bundleId}/setup.html`;
            deferreds.push(this.fetchConfigHtml(htmlUrl));

            deferreds.push(this.fetchDependencies());
            deferreds.push(this.fetchAppInfo());
        }

        return deferreds;
    }

    fetchConfigJson(url) {
        return $.get(SplunkDUtils.fullpath(url)).then((response) => {
            this.json = ModSetupConfigurationHelper.parseJson(response);
        });
    }

    fetchConfigHtml(url) {
        return $.get(SplunkDUtils.fullpath(url)).then((response) => {
            this.html = response;
        });
    }

    fetchDependencies() {
        const model = new AppDependenciesInfoModel();
        model.set('bundleId', this.options.bundleId);
        return model.fetch().then(() => {
            // Need to omit the 'eai:acl as backend cannot create a nested structure under content.
            this.dependencies = _.filter(model.entry.content.keys(), key => !(/^eai:/i.test(key)));
        }).fail(() => {
            this.dependencies = [];
        });
    }

    fetchAppInfo() {
        const stanzas = ['ui', 'install'];
        const config = {
            file: 'app',
            stanzas,
            bundleId: this.options.bundleId,
            query: stanzas.map(x => `name=${x}`).join(' OR '),
        };
        this.appCollection = new ModSetupConfCollection();
        this.appCollection.config = config;
        return this.appCollection.fetch().then(() => {
            this.isConfiguredModel = this.appCollection.find(m => m.entry.get('name') === 'install');
            this.appUiModel = this.appCollection.find(m => m.entry.get('name') === 'ui');
        });
    }

    getNeedsConfiguration(editMode) {
        if (!editMode) {
            return !this.isConfigured;
        }
        return true;
    }

    static parseJson(config) {
        try {
            const isValid = ModSetupConfigurationHelper.validateSetup(config.setup);
            if (isValid) {
                _.each(config.setup, (item) => {
                    if (item.conf) {
                        ModSetupConfigurationHelper.formatConf(item);
                    }

                    if (item.types && item.types.conf) {
                        ModSetupConfigurationHelper.formatConf(item.types);
                    }
                });
                return config;
            }
            return null;
        } catch (e) {
            window.console.log(e);
            return null;
        }
    }

    /**
     * Format setup.json
     * @param config
     * @private
     */
    static formatConf(config) {
        const item = config;
        if (item.conf && !_.isArray(item.conf)) {
            item.conf = [item.conf];
        }
        if (item.conf) {
            _.each(item.conf, (c) => {
                const conf = c;
                if (conf.stanzas && _.isString(conf.stanzas)) {
                    conf.stanzas = [conf.stanzas];
                }

                if (conf.properties && !_.isArray(conf.properties)) {
                    conf.properties = [conf.properties];
                }
            });
        }
    }

    /**
     * Validate configurations specified in setup.json
     * @param setup
     * @returns {boolean}
     * @private
     */
    static validateSetup(setup) {
        if (_.isEmpty(setup) || !_.isArray(setup)) {
            throw new Error('No setup configuration provided');
        }
        _.each(setup, (config) => {
            const matchedType = _.intersection(_.keys(config), _.values(TYPES));
            if (matchedType.length !== 1) {
                throw new Error(`Invalid Config type ${JSON.stringify(config)}`);
            }

            if (matchedType[0] === 'conf') {
                if (_.isArray(config.conf)) {
                    _.each(config.conf, (conf) => {
                        ModSetupConfigurationHelper.validateConf(conf);
                    });
                } else {
                    ModSetupConfigurationHelper.validateConf(config.conf);
                }
            }

            if (matchedType[0] === 'password') {
                if (_.isEmpty(config.password.key)) {
                    throw new Error(`Invalid Password configuration : ${JSON.stringify(config)}`);
                }
            }

            if (matchedType[0] === 'script') {
                if (_.isEmpty(config.script.url)) {
                    throw new Error(`Invalid script configuration ${JSON.stringify(config)}`);
                }
            }
        });
        return true;
    }

    static validateConf(config) {
        const keys = _.keys(config);
        const hasAllProperties =
            REQUIRED_CONF_PROPERTIES.every(item => keys.indexOf(item) > -1 && !_.isEmpty(config[item]));

        if (!hasAllProperties) {
            throw new Error(`Conf does not have all required properties
             (${REQUIRED_CONF_PROPERTIES.join(',')}) : ${JSON.stringify(config)}`);
        }
    }

    get isDMCEnabled() {
        return this.options.isDMCEnabled;
    }

    get label() {
        return this.appUiModel.entry.content.get('label');
    }

    get isConfigured() {
        return SplunkUtil.normalizeBoolean(this.isConfiguredModel.entry.content.get('is_configured'));
    }
}
