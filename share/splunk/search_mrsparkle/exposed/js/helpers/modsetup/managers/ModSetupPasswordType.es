import ModSetupPasswordModel from 'models/modsetup/ModSetupPassword';
import _ from 'underscore';
import ModSetupBaseType from './ModSetupBaseType';
import { TYPES } from './ModSetupTypes';


export default class ModSetupPasswordType extends ModSetupBaseType {

    static getType() {
        return TYPES.PASSWORD;
    }

    getDefaultValues() {
        const defaults = {};
        _.each(this.models, (model) => {
            const clrPassword = model.entry.content.get('clear_password');
            if (clrPassword) {
                const data = JSON.parse(clrPassword);
                _.each(_.keys(data), (key) => {
                    defaults[`${this.options.prefix}.${key}`] = data[key];
                });
            }
        });

        return defaults;
    }

    /**
     * Create a password model and fetch . This would help load existing password configurations
     * Name would be the key user specified.
     * @param config
     * @returns {Number}
     */
    create(config) {
        const deferreds = [];
        const model = new ModSetupPasswordModel();
        model.set({
            name: config.name,
            fields: config.password.fields,
            bundle: this.options.bundleId,
        });

        model.entry.set({ name: config.password.key });
        this.models.push(model);
        deferreds.push(model.fetch());
        return deferreds;
    }

    /**
     * Save password. This would stringify the values of "fields" as store them as password.
     * The name would always be the key user specified.
     * @param data
     * @param key
     * @returns {Array}
     */
    save(d) {
        const data = d;
        const deferreds = [];
        _.each(this.models, (model) => {
            const passKey = {};
            _.each(model.get('fields'), (field) => {
                passKey[field] = data[`${this.options.prefix}.${field}`];
            });
            const obj = {
                name: model.get('key'),
                password: JSON.stringify(passKey),
            };
            model.entry.content.clear();
            model.entry.content.set(obj);
            deferreds.push(model.save({}));
        });

        return deferreds;
    }
}
