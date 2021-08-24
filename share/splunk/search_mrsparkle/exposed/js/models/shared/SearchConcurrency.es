import $ from 'jquery';
import SplunkDBaseModel from 'models/SplunkDBase';
import Backbone from 'backbone';
import splunkdUtils from 'util/splunkd_utils';

export default SplunkDBaseModel.extend({
    url: splunkdUtils.fullpath('server/status/limits/search-concurrency'),
    sync(method, model, options) {
        const defaults = {};

        defaults.data = {
            output_mode: 'json',
        };
        defaults.processData = true;
        $.extend(true, defaults, options);

        return Backbone.sync.call(null, method, model, defaults);
    },
    getMaxHistScheduledSearches() {
        if (this.entry.content.has('max_hist_scheduled_searches')) {
            return this.entry.content.get('max_hist_scheduled_searches');
        }
        return 'unknown';
    },
    getMaxAutoSummarySearches() {
        if (this.entry.content.has('max_auto_summary_searches')) {
            return this.entry.content.get('max_auto_summary_searches');
        }
        return 'unknown';
    },
});