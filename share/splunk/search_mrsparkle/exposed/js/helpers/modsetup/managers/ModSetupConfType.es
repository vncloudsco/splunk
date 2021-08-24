import ModSetupConfModel from 'models/modsetup/ModSetupSplunkDConf';
import ModSetupConfCollection from 'collections/modsetup/ModSetupSplunkDConfs';
import _ from 'underscore';
import ModSetupBaseType from './ModSetupBaseType';
import { TYPES } from './ModSetupTypes';


const GLOBAL_CONFIG_PROPS = ['name', 'isList', 'viewConfig'];
const NAME_ATTR = '@name';
const CONFIG_KEY = '@config';

export default class ModSetupConfType extends ModSetupBaseType {

    constructor(...args) {
        super(...args);

        // Stores the map of key(ui element ) to the models associated
        this.dataMap = {};
        // stores the map of key to collections
        this.listMap = {};
    }

    static getType() {
        return TYPES.CONF;
    }

    /**
     * Fetch the default values.
     * For non-list conf properties the first value is considered as a default value
     * For list a array of values (each values being the model.toJSON()) is returned
     * @returns {{}}
     */
    getDefaultValues() {
        const defaults = {};
        const prefix = this.options.prefix || '';

        _.each(_.keys(this.dataMap), (key) => {
            if (this.dataMap[key] && this.dataMap[key].length > 0) {
                const model = this.dataMap[key][0];
                const properties = model.get('properties') || [];
                const attrs = _.pick(model.entry.content.toJSON(), ...properties);
                // fetching the first property should be fine as all the props will have the same value after edit
                const prop = properties[0];
                if (attrs[prop]) {
                    defaults[`${prefix}.${key}`] = attrs[prop];
                }
            }
        });

        _.each(_.keys(this.listMap), (key) => {
            defaults[`${this.options.prefix}.${key}`] = this.getDefaultDataForList(this.listMap[key]);
        });

        return defaults;
    }

    /**
     * Fetch default values for collections
     * @param items
     * @returns {Array}
     * @private
     */
    // eslint-disable-next-line class-methods-use-this
    getDefaultDataForList(items) {
        const data = {};
        _.each(items, (item) => {
            const config = item.config;
            if (config.viewConfig) {
                data[CONFIG_KEY] = { [CONFIG_KEY]: config.viewConfig };
            }
            item.each((model) => {
                if (_.isArray(config.stanzas) && !_.contains(config.stanzas, model.entry.get('name'))) {
                    return;
                }

                const properties = model.get('properties') || [];
                const obj = _.pick(model.entry.content.toJSON(), ...properties);
                const keyValue = model.entry.get('name');
                if (data[keyValue]) {
                    data[keyValue] = _.extend({}, data[keyValue], obj);
                } else {
                    obj[NAME_ATTR] = model.entry.get('name');
                    data[keyValue] = obj;
                }
            });
        });
        return _.values(data);
    }

    /**
     * Create Models
     */
    create(config) {
        let deferreds = [];
        const confs = config.conf;
        _.each(confs, (val) => {
            let value = val;
            value = _.extend({}, value, _.pick(config, ...GLOBAL_CONFIG_PROPS));
            if (config.isList) {
                deferreds = deferreds.concat(this.handleListConf(value));
            } else {
                deferreds = deferreds.concat(this.handleSingleConf(value));
            }
        });
        return deferreds;
    }

    /**
     * Create collection in case of list
     * @param config
     * @returns {Array}
     * @private
     */
    handleListConf(config) {
        const deferreds = [];
        let item = null;

        item = new ModSetupConfCollection();
        item.config = config;
        this.constructFetchQuery(item);
        const def = item.fetch().done(() => {
            _.each(item.models, (model) => {
                this.updateModelProperties(model, config);
            }, this);

            this.updateMap(this.dataMap, config.name, item.models);
            this.addModelToList(item.models);
            this.updateMap(this.listMap, config.name, [item]);
        });
        deferreds.push(def);
        return deferreds;
    }

    /**
     * For non list properties create model
     * @param config
     * @returns {Array}
     * @private
     */
    handleSingleConf(config) {
        const deferreds = [];

        if (_.isArray(config.stanzas)) {
            _.each(config.stanzas, (stanza) => {
                let item = null;
                if (_.isString(stanza)) {
                    // create model to fetch the stanza
                    item = new ModSetupConfModel();
                    this.updateModelProperties(item, config);
                    item.entry.set('name', stanza);
                }

                // Fetch the item (collection/ model) and add the model/models to the dataMap;
                const def = item.fetch().done(() => {
                    this.updateMap(this.dataMap, config.name, [item]);
                    this.addModelToList([item]);
                });

                deferreds.push(def);
            });
        } else if (_.isObject(config.stanzas) && config.stanzas.pattern) {
            const item = new ModSetupConfCollection();
            item.config = config;
            this.constructFetchQuery(item);

            // Fetch the item (collection/ model) and add the model/models to the dataMap;
            const def = item.fetch().done(() => {
                _.each(item.models, (model) => {
                    this.updateModelProperties(model, config);
                }, this);
                this.updateMap(this.dataMap, config.name, item.models);
                this.addModelToList(item.models);
            });

            deferreds.push(def);
        }

        return deferreds;
    }

    /**
     * IN case of regular expressions , A query is constructed
     * @param i
     * @private
     */
    constructFetchQuery(i) {
        const item = i;
        const config = item.config;
        let query = {};
        item.config.bundleId = this.options.bundleId;
        if (_.isObject(config.stanzas) && config.stanzas.pattern) {
            query = `name=${config.stanzas.pattern}`;
        } else if (_.isArray(config.stanzas)) {
            query = config.stanzas.map(name => `name=${name}`).join(' OR ');
        } else {
            query = config.stanzas;
        }
        item.config.query = query;
    }

    /**
     * A local map of every unique model is maintained. This is done to avoid overriding conf changes when multiple
     * setup.json properties try to update the same stanzas/properties
     *
     * On save all the changes are written to this unique models/collections and save.
     * @param m
     * @param key
     * @param items
     * @private
     */
    // eslint-disable-next-line class-methods-use-this
    updateMap(m, key, items) {
        const map = m;
        if (map[key]) {
            map[key] = map[key].concat(items);
        } else {
            map[key] = items;
        }
    }

    // Store metadata on model
    updateModelProperties(model, config) {
        model.set({
            bundle: this.options.bundleId,
            type: config.file,

            key: config.name,
            properties: config.properties,
            allProperties: config.properties,
        });
    }

    /**
     * Add the fetched models to the base collection. Need to do this to avoid duplicate models .
     * @private
     */
    addModelToList(models) {
        _.each(models, (model) => {
            const baseModel = this.findInModelsList(model);

            if (!baseModel) {
                this.models.push(model);
            } else {
                baseModel.set('allProperties', _.union(baseModel.get('allProperties'), model.get('properties')));
            }
        });
    }

    /**
     * Save DMC models
     */
    save(data) {
        let deferreds = [];
        _.each(_.keys(data), (key) => {
            const content = data[key];
            if (_.isString(content)) {
                this.saveStringValues(key, data);
            } else if (_.isArray(content)) {
                deferreds = deferreds.concat(this.saveListValues(key, content));
            }
        });

        _.each(this.models, (model) => {
            if (model.dirty && !model.delete) {
                deferreds.push(model.save({}));
            }
        });

        return deferreds;
    }

    saveStringValues(key, data) {
        const keyWithoutPrefix = key.substr(this.options.prefix.length + 1);
        const models = this.dataMap[keyWithoutPrefix];

        // handle string values
        _.each(models, (model) => {
            const objs = [];
            _.each(model.get('properties'), (property) => {
                const obj = [property];
                const prop = `${this.options.prefix}.${model.get('key')}`;
                if (prop in data) {
                    obj.push(data[prop]);
                    objs.push(obj);
                }
            });

            this.saveModelWithProperties(model, data, objs);
        });
    }

    saveListValues(key, content) {
        const keyWithoutPrefix = key.substr(this.options.prefix.length + 1);
        const deferreds = [];
        const currentNames = _.pluck(content, NAME_ATTR);

        let deleteList = [];
        let allModelds = [];

        // TO-DO handle patterns
        const collections = this.listMap[keyWithoutPrefix];
        _.each(content, (item) => {
            const models = this.findInCollections(collections, item);
            if (models && models.length > 0) {
                _.each(models, (model) => {
                    const objs = [];
                    _.each(model.get('properties'), (property) => {
                        const obj = [property];
                        if (property in item) {
                            obj.push(item[property]);
                            objs.push(obj);
                        }
                    });
                    this.saveModelWithProperties(model, item, objs);
                });
            } else {
                _.each(collections, (collection) => {
                    const model = new ModSetupConfModel();
                    const objs = [];
                    model.set({
                        bundle: this.options.bundleId,
                        type: collection.config.file,
                        name: item[NAME_ATTR],
                    });
                    model.entry.set('name', item[NAME_ATTR]);
                    _.each(collection.config.properties, (property) => {
                        const obj = [property];
                        if (item[property]) {
                            obj.push(item[property]);
                            objs.push(obj);
                        }
                    });
                    objs.push([NAME_ATTR, item[NAME_ATTR]]);
                    model.set('allProperties', collection.config.properties);
                    model.entry.content.set(_.object(objs));
                    deferreds.push(model.save({}));
                });
            }
        });

        _.each(collections, (collection) => {
            allModelds = allModelds.concat(collection.models);
        });
        deleteList = _.filter(allModelds, model => !_.contains(currentNames, model.entry.get('name')));

        _.each(deleteList, (model) => {
            const baseModel = this.findInModelsList(model);
            if (baseModel) {
                baseModel.delete = true;
                deferreds.push(baseModel.destroy());
            } else {
                deferreds.push(model.destroy());
            }
        });
        return deferreds;
    }

    saveModelWithProperties(model, data, properties) {
        const baseModel = this.findInModelsList(model);
        baseModel.entry.content.set(_.object(properties));
        baseModel.dirty = true;
    }

    // eslint-disable-next-line class-methods-use-this
    findInCollections(collections, item) {
        let models = [];
        _.each(collections, (collection) => {
            models = models.concat(collection.filter(model => model.entry.get('name') === item[NAME_ATTR]));
        });

        return models;
    }


    findInModelsList(model) {
        return _.find(this.models, (item) => {
            if (item.entry.get('name') === model.entry.get('name') &&
                   item.get('type') === model.get('type')) {
                return true;
            }
            return false;
        });
    }

}
