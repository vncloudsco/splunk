import $ from 'jquery';
import _ from 'underscore';
import { TYPES, getHelperForType } from 'helpers/modsetup/managers/ModSetupTypes';


export default class ModSetupDataHelper {

    constructor(bundleId, prefix, isDMCEnabled) {
        this.bundleId = bundleId;
        this.prefix = prefix;
        this.isDMCEnabled = isDMCEnabled;

        this.typeMap = {};
        _.each(_.keys(TYPES), (type) => {
            this.typeMap[TYPES[type]] = getHelperForType(type, this.isDMCEnabled, this.bundleId, this.prefix);
        });
    }

    /**
     * Create models and collections based on the configuration provided by the user. This would also
     * fetch the models/collections for initial default values.
     * @param properties - setup.json values
     * @param html - setup.html
     * @returns {*}
     */
    manageConfigurations(properties, html) {
        const setupProperties = this.constructValidConfiguration(properties, html);
        // eslint-disable-next-line new-cap
        const fecheDeferred = $.Deferred();
        let deferreds = [];

        _.each(setupProperties.setup, (config) => {
            deferreds = deferreds.concat(this.create(config));
        });

        let count = 0;
        _.each(deferreds, (def) => {
            def.always(() => {
                count += 1;
                if (count === deferreds.length) {
                    fecheDeferred.resolve();
                }
            });
        });

        return fecheDeferred;
    }

    /**
     * Save the models/collections.
     * The changes that the user has made are applied to all the models/collections and then saved. In case
     * of error the deferred is rejected.
     * @param data - Object holding all the changes user made
     * @returns {*}
     */
    save(data) {
        let deferreds = [];
        let errors = [];
        let count = 0;
        // eslint-disable-next-line new-cap
        const saveDeferred = $.Deferred();

        const handleSaveState = () => {
            count += 1;
            if (count === deferreds.length) {
                if (errors.length > 0) {
                    saveDeferred.reject(errors);
                } else {
                    saveDeferred.resolve();
                }
            }
        };
        _.each(_.keys(this.typeMap), (type) => {
            deferreds = deferreds.concat(this.typeMap[type].save(data, type));
        });

        _.each(deferreds, (def) => {
            def.fail((resp) => {
                if (resp.responseText) {
                    const parsedResp = JSON.parse(resp.responseText);
                    if (parsedResp.messages) {
                        errors = errors.concat(parsedResp.messages);
                    }
                }
            }).always(() => {
                handleSaveState();
            });
        });

        return saveDeferred;
    }

    /**
     * Loads the default values for all the types.
     * @returns {{}}
     */
    getDefaultValues() {
        let defaults = {};
        _.each(_.values(this.typeMap), (type) => {
            defaults = _.extend({}, defaults, type.getDefaultValues());
        });

        return defaults;
    }

    /**
     * Read the type of the confiuration. If no valid configuration has been provided a error will be thrown.
     * @param config
     * @returns {*}
     */
    // eslint-disable-next-line class-methods-use-this
    setType(config) {
        const newConfig = config;
        const matchedType = _.intersection(_.keys(newConfig), _.values(TYPES));
        if (matchedType.length > 0) {
            newConfig.type = matchedType[0];
            return newConfig;
        }

        throw new Error('Invalid type');
    }

    /**
     * Create models/collections for the config based on type.
     * @param config
     * @returns {Array}
     * @private
     */
    create(config) {
        let deferreds = [];
        const props = ['name', 'isList'];

        // If config is list, Create models/collections for each item in the list.
        if (config.isList && config.types) {
            _.each(_.keys(config.types), (key) => {
                let cfg = _.pick(config, ...props);
                cfg[key] = config.types[key];
                cfg = this.setType(cfg);
                deferreds = deferreds.concat(this.typeMap[key].create(cfg));
            });
        } else {
            const newConfig = this.setType(config);
            deferreds = deferreds.concat(this.typeMap[config.type].create(newConfig));
        }
        return deferreds;
    }

    /**
     * Removes all the the configurations for which there is no assiciated field in the setup.html
     * @param properties
     * @param html
     * @returns {{setup: Array}}
     * @private
     */
    constructValidConfiguration(properties, html) {
        const $el = $(html);
        const names = [];
        const newProperties = { setup: [] };

        $el.find('[name]').each((index, element) => {
            names.push($(element).attr('name').substr(this.prefix.length + 1));
        });

        _.each(properties.setup, (config) => {
            if (_.contains(names, config.name)) {
                newProperties.setup.push(config);
            }
        });
        return newProperties;
    }
}
