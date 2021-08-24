/**
 * Fetch a list of stanzas.
 */
import $ from 'jquery';
import _ from 'underscore';
import SplunkdUtils from 'util/splunkd_utils';
import ModSetupSplunkDConf from 'models/modsetup/ModSetupSplunkDConf';
import SplunkDsBaseCollections from 'collections/SplunkDsBase';

export default SplunkDsBaseCollections.extend({

    urlBase: 'configs/conf-',
    model: ModSetupSplunkDConf,
    url() {
        const path = this.urlBase + this.config.file;
        return SplunkdUtils.fullpath(path, {
            app: this.config.bundleId,
            owner: 'nobody',
        });
    },

    fetch(options) {
        let currentOptions = options;
        currentOptions = _.defaults(currentOptions || {}, { count: 0 });
        const defaults = {
            url: this.url(),
            data: _.defaults(currentOptions.data || {}, {
                count: -1,
            }),
        };

        // For regex a search string needs to be passed
        if (this.config.query) {
            defaults.data.search = this.config.query;
        }

        const updatedOptions = $.extend(true, defaults, currentOptions);
        return SplunkDsBaseCollections.prototype.fetch.call(this, updatedOptions);
    },
});