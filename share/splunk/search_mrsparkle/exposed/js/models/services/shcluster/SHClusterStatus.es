/**
 * @author stewarts
 * @date 02/14/17
 *
 * Search Head Cluster Status Model.
 */

import $ from 'jquery';
import Backbone from 'backbone';
import BaseModel from 'models/Base';
import splunkdUtils from 'util/splunkd_utils';

const POLLING_FREQUENCY = 10000;

export default BaseModel.extend({
    url: splunkdUtils.fullpath('shcluster/status'),

    sync(method, model, options = {}) {
        if (method !== 'read') {
            throw new Error(`invalid method: ${method}`);
        }

        const defaults = {
            data: {
                output_mode: 'json',
            },
        };
        $.extend(true, defaults, options);

        return Backbone.sync.call(this, method, model, defaults);
    },

    pollStatus() {
        // Get status initially, then poll on the interval
        this.fetchStatus();
        setInterval(this.fetchStatus.bind(this), POLLING_FREQUENCY);
    },

    fetchStatus() {
        const shClusterStatus = this;
        this.fetch()
        .done((response) => {
            const rollingRestartFlag = response.entry[0].content.captain.rolling_restart_flag;
            const serviceReadyFlag = response.entry[0].content.captain.service_ready_flag;

            shClusterStatus.trigger('serviceReadyUpdate', {
                serviceReady: serviceReadyFlag,
                rollingRestart: rollingRestartFlag,
            });
        })
        .fail(() => {
            shClusterStatus.trigger('serviceReadyUpdate');
        });
    },
});
