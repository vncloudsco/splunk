import $ from 'jquery';
import BaseModel from 'models/SplunkDBase';
import splunkdUtils from 'util/splunkd_utils';

export default BaseModel.extend({

    url() {
        const base = '';
        return splunkdUtils.fullpath(base + this.scriptUrl, {
            app: this.bundleId,
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
            default:
                break;
        }

        const newOptions = $.extend({}, defaults, options);
        return BaseModel.prototype.sync.call(this, method, model, newOptions);
    },

});