/**
 * Support CRUD operations on scripts.
 */
import ModSetupScriptsCollection from 'collections/modsetup/ModSetupScripts';
import ModSetupScriptModel from 'models/modsetup/ModSetupScript';
import $ from 'jquery';
import _ from 'underscore';
import ModSetupBaseType from './ModSetupBaseType';
import { TYPES } from './ModSetupTypes';

const NAME_ATTR = '@name';


export default class ModSetupScriptType extends ModSetupBaseType {

    constructor(...args) {
        super(...args);
        this.collectionsMap = {};
    }

    static getType() {
        return TYPES.SCRIPT;
    }

    getDefaultValues() {
        const defaults = {};
        _.each(_.values(this.collectionsMap), (collection) => {
            _.each(collection.models, (model) => {
                const attrs = model.entry.content.toJSON();
                attrs[NAME_ATTR] = model.entry.get('name');
                const prop = `${this.options.prefix}.${model.get('key')}`;
                if (defaults[prop]) {
                    defaults[prop].push(attrs);
                } else {
                    defaults[prop] = [attrs];
                }
            });
        });
        return defaults;
    }

    /**
     * For scripts always a collection is created and fetched.
     * @param data
     * @returns {Array}
     */
    create(data) {
        const deferreds = [];
        const collection = new ModSetupScriptsCollection();
        collection.bundleId = this.options.bundleId;
        collection.scriptUrl = data.script.url;
        const def = collection.fetch({}).done(() => {
            _.each(collection.models, (model) => {
                model.set({
                    key: data.name,
                });
            });
        });

        this.collectionsMap[data.name] = collection;
        deferreds.push(def); // LIST
        return deferreds;
    }

    addNew(collection, data) {
        const model = new ModSetupScriptModel();
        model.entry.set('name', data['@name']);
        const obj = $.extend(true, {}, data);
        model.bundleId = this.options.bundleId;
        model.scriptUrl = collection.scriptUrl;
        delete obj['@name'];
        model.entry.content.set(obj);
        return model;
    }

    /**
     * Save performs all the crud operations required for scripts
     * @param data
     * @param type
     * @returns {Array}
     */
    save(data) {
        const deferreds = [];
        _.each(_.keys(this.collectionsMap), (key) => {
            const collection = this.collectionsMap[key];
            const changes = data[`${this.options.prefix}.${key}`];
            _.each(changes, (change) => {
                const model = collection.find(m => m.entry.get('name') === change['@name']);
                if (model) {
                    // EDIT
                    const obj = $.extend(true, {}, change);
                    delete obj['@name'];
                    model.entry.content.set(obj);
                    deferreds.push(model.save({}));
                } else {
                    // CREATE
                    const newModel = this.addNew(collection, change);
                    deferreds.push(newModel.save({}));
                }
            });

            // Handle deletes
            const currentNames = _.pluck(changes, '@name');
            const deletModels = collection.filter(model => !_.contains(currentNames, model.entry.get('name')));

            _.each(deletModels, (model) => {
                deferreds.push(model.destroy());
            });
        });
        return deferreds;
    }
}
