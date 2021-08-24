import $ from 'jquery';
import _ from 'underscore';
import splunkdUtils from 'util/splunkd_utils';
import SplunkDBase from 'models/SplunkDBase';

export default SplunkDBase.extend({

    urlBase: 'configs/conf-',

    url() {
        const path = this.urlBase + this.get('type');
        return splunkdUtils.fullpath(path, {
            app: this.get('bundle'),
            owner: 'nobody',
        });
    },

    sync(method, model, options) {
        const defaults = {
            url: this.url(),
            data: {
            },
        };

        switch (method) {
            case 'create':
                defaults.data.name = this.entry.get('name');
                this.updateAllProperties(defaults);
                break;
            case 'update':
                defaults.url = `${defaults.url}/${this.entry.get('name')}`;
                this.updateAllProperties(defaults);
                break;
            case 'delete':
                // In case of delete the default constructed url should work
                delete defaults.url;
                break;
            default:
                defaults.url = `${defaults.url}/${this.entry.get('name')}`;
        }


        const newOptions = $.extend(true, defaults, options);
        return SplunkDBase.prototype.sync.call(this, method, model, newOptions);
    },

    updateAllProperties(defaults) {
        this.allProperties = this.get('allProperties') || [];
        $.extend(true, defaults.data, _.pick(this.entry.content.toJSON(), ...this.allProperties));
    },

    reloadAppConfigurations() {
        const url = splunkdUtils.fullpath(`/services/apps/local/${this.get('bundle')}/_reload`);
        return $.ajax({
            url,
            data: {
                output_mode: 'json',
            },
        });
    },

});
