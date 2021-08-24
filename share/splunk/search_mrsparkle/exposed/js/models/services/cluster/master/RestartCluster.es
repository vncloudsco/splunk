import $ from 'jquery';
import Backbone from 'backbone';
import _ from 'underscore';
import SplunkDBaseModel from 'models/SplunkDBase';
import splunkdUtils from 'util/splunkd_utils';

export default SplunkDBaseModel.extend({
    /**
     * This model is used to call the rolling restart of index cluster.
     * The POST calls returns an empty payload. (this might change in future).
     */
    sync(method, model, options) {
        const defaults = {};
        const hasSiteOrder = _.has(model.attributes, 'site-order');
        if (method !== 'create' && method !== 'update') {
            throw new Error(`invalid method: ${method}`);
        }

        defaults.data = $.extend({}, {
            output_mode: 'json',
            'site-order': hasSiteOrder ? model.get('site-order') : undefined,
            'site-by-site': hasSiteOrder ? true : undefined,
        });

        this.url = `${splunkdUtils.fullpath('cluster/master/control/control/restart')}?` +
            `searchable=${model.get('searchable')}&force=${model.get('force')}`;
        defaults.processData = true;
        $.extend(true, defaults, options);
        return Backbone.sync.call(null, method, model, defaults);
    },
});