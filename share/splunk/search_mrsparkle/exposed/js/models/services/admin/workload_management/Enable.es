import $ from 'jquery';
import SplunkDBaseModel from 'models/SplunkDBase';
import Backbone from 'backbone';
import splunkdUtils from 'util/splunkd_utils';

export default SplunkDBaseModel.extend({
    url: splunkdUtils.fullpath('workloads/config/enable'),
    sync(method, model, options) {
        const defaults = {};

        defaults.data = {
            output_mode: 'json',
        };
        defaults.processData = true;
        $.extend(true, defaults, options);

        return Backbone.sync.call(null, method, model, defaults);
    },
});
