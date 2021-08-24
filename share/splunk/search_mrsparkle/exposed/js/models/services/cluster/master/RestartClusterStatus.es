import $ from 'jquery';
import Backbone from 'backbone';
import SplunkDBaseModel from 'models/SplunkDBase';
import splunkdUtils from 'util/splunkd_utils';

export default SplunkDBaseModel.extend({
    /**
     * This model is used to get the rolling restart status of index cluster.
     */
    url: splunkdUtils.fullpath('cluster/master/status'),
    initialize(...args) {
        SplunkDBaseModel.prototype.initialize.apply(this, args);
    },
    sync(method, model, options) {
        const defaults = {
            data: {
                output_mode: 'json',
            },
            processData: true,
        };
        $.extend(true, defaults, options);
        return Backbone.sync.call(null, method, model, defaults);
    },
});