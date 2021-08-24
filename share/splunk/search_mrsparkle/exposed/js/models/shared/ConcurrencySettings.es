import $ from 'jquery';
import SplunkDBaseModel from 'models/SplunkDBase';
import Backbone from 'backbone';
import splunkdUtils from 'util/splunkd_utils';

export default SplunkDBaseModel.extend({
    url: splunkdUtils.fullpath('search/concurrency-settings'),
    sync(method, model, options) {
        const defaults = {};

        defaults.data = {
            output_mode: 'json',
        };
        defaults.processData = true;
        $.extend(true, defaults, options);

        return Backbone.sync.call(null, method, model, defaults);
    },
    getMaxSearchesPerc() {
        if (this.entry.content.has('max_searches_perc')) {
            return this.entry.content.get('max_searches_perc');
        }
        return 'unknown';
    },
    getAutoSummaryPerc() {
        if (this.entry.content.has('auto_summary_perc')) {
            return this.entry.content.get('auto_summary_perc');
        }
        return 'unknown';
    },
});
