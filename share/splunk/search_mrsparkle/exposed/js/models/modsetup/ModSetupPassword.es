import $ from 'jquery';
import splunkdUtils from 'util/splunkd_utils';
import BaseModel from 'models/SplunkDBase';

export default BaseModel.extend({

    url() {
        const path = 'storage/passwords';
        return splunkdUtils.fullpath(path, {
            app: this.get('bundle'),
            owner: 'nobody',
        });
    },

    sync(method, model, options) {
        let defaults = {};
        switch (method) {
            case 'create':
                defaults = {
                    data: {
                        output_mode: 'json',
                        name: this.entry.get('name'),
                    },
                };
                break;
            case 'read':
                // Need to do this to avoid adding "_new" to requests
                defaults = {
                    url: `${this.url()}/${this.entry.get('name')}`,
                    data: {
                        output_mode: 'json',
                    },
                };
                break;
            default:
                break;
        }

        const newOptions = $.extend({}, defaults, options);
        return BaseModel.prototype.sync.call(this, method, model, newOptions);
    },
});
