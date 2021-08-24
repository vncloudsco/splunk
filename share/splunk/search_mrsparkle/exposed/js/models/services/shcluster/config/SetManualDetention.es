import Backbone from 'backbone';
import $ from 'jquery';
import SplunkDBaseModel from 'models/SplunkDBase';
import splunkdUtils from 'util/splunkd_utils';

export default SplunkDBaseModel.extend({
    url: splunkdUtils.fullpath('shcluster/config/config'),
    sync(method, model, options) {
        const defaults = {};
        if (method !== 'create' && method !== 'update') {
            throw new Error(`invalid method: ${method}`);
        }

        defaults.data = {
            output_mode: options.output_mode,
            manual_detention: model.entry.content.get('manual_detention'),
            target_uri: model.entry.content.get('mgmt_uri'),
        };
        defaults.processData = true;
        $.extend(true, defaults, options);

        return Backbone.sync.call(null, method, model, defaults);
    },
});
