import $ from 'jquery';
import splunkdUtils from 'util/splunkd_utils';
import BaseModel from 'models/SplunkDBase';


export default BaseModel.extend({

    url() {
        const path = `/services/apps/local/${this.get('bundleId')}/dependencies`;
        return splunkdUtils.fullpath(path, {
            app: this.get('bundleId'),
            owner: 'nobody',
        });
    },

    sync(method, model, options) {
        // Need to do this to avoid adding "_new" to requests
        const defaults = {
            url: this.url(),
            data: {
                output_mode: 'json',
            },
        };

        const newOptions = $.extend({}, defaults, options);
        return BaseModel.prototype.sync.call(this, method, model, newOptions);
    },
});
