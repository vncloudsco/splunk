/**
 * @author stewarts
 * @date 11/28/16
 *
 * Members Collection for Search Head Clustering
 */

import $ from 'jquery';
import Backbone from 'backbone';
import _ from 'underscore';
import Model from 'models/services/cluster/searchhead/Member';
import SplunkDsBaseCollection from 'collections/SplunkDsBase';
import SplunkDBaseModel from 'models/SplunkDBase';
import SHClusterStatusModel from 'models/services/shcluster/SHClusterStatus';
import splunkdUtils from 'util/splunkd_utils';

const POLLING_FREQUENCY = 10000;

function poll(fn, interval) {
    function checkCondition(resolve, reject) {
        const result = fn();
        if (result) {
            resolve(result);
        } else {
            setTimeout(checkCondition, interval, resolve, reject);
        }
    }
    return new Promise(checkCondition);
}

/**
 *  Private Class Rolling Restart Model for initiating
 *  a rolling restart
 */
const RollingRestartModel = SplunkDBaseModel.extend({
    url: splunkdUtils.fullpath('shcluster/captain/control/control/restart'),

    service_ready_flag: true,

    rolling_restart_flag: false,

    sync(method, model, options) {
        const defaults = {};
        if (method !== 'create' && method !== 'update') {
            throw new Error(`invalid method: ${method}`);
        }

        defaults.data = {
            output_mode: options.output_mode,
        };
        defaults.processData = true;
        $.extend(true, defaults, options);

        this.url += `?searchable=${model.get('searchable')}&force=${model.get('force')}`;
        return Backbone.sync.call(null, method, model, defaults);
    },

    pollRollingRestartReady() {
        const SHClusterStatusInstance = new SHClusterStatusModel();
        this.service_ready_flag = false;

        return poll(() => {
            SHClusterStatusInstance.fetch()
                .done((response) => {
                    this.service_ready_flag = response.entry[0].content.captain.service_ready_flag;
                    this.rolling_restart_flag = response.entry[0].content.captain.rolling_restart_flag;
                });

            // service ready and rolling restart complete
            return this.service_ready_flag && !this.rolling_restart_flag;
        }, POLLING_FREQUENCY);
    },
});

/**
 *  Private Class Captain Model for inititiating a
 *  captain transfer
 */
const CaptainModel = SplunkDBaseModel.extend({
    url: splunkdUtils.fullpath('shcluster/member/consensus/foo/transfer_captaincy'),

    service_ready_flag: true,

    sync(method, model, options) {
        const defaults = {};
        if (method !== 'create' && method !== 'update') {
            throw new Error(`invalid method: ${method}`);
        }
        if (!options.mgmt_uri) {
            throw new Error('mgmt_uri is required.');
        }

        defaults.data = {
            mgmt_uri: options.mgmt_uri,
            output_mode: options.output_mode,
        };
        defaults.processData = true;
        $.extend(true, defaults, options);

        return Backbone.sync.call(null, method, model, defaults);
    },

    pollServiceReady() {
        const SHClusterStatusInstance = new SHClusterStatusModel();
        this.service_ready_flag = false;

        return poll(() => {
            SHClusterStatusInstance.fetch()
                .done((response) => {
                    if (response.entry[0].content.captain.service_ready_flag) {
                        this.service_ready_flag = true;
                    }
                });

            return this.service_ready_flag;
        }, POLLING_FREQUENCY);
    },
});

/**
 *  Members Collection
 */
export default SplunkDsBaseCollection.extend({
    url: 'shcluster/member/members',
    model: Model,

    initialize(...args) {
        this.model = this.model || {};
        this.model.captainInstance = new CaptainModel();
        this.model.rollingRestartInstance = new RollingRestartModel();

        SplunkDsBaseCollection.prototype.initialize.apply(this, args);
        this.listenTo(this.model.captainInstance, 'serverValidated', this.handleValidationError);
        this.listenTo(this.model.rollingRestartInstance, 'serverValidated', this.handleValidationError);
    },

    comparator(member) {
        return !member.isCaptain();
    },

    getCurrentCaptain() {
        return this.find(model => model.isCaptain());
    },

    transferCaptain(targetCaptain) {
        if (!targetCaptain) {
            throw new Error(`targetCaptain parameter required. Current targetCaptain: ${targetCaptain}`);
        }
        const targetCaptainUri = targetCaptain.getMgmtUri();
        // eslint-disable-next-line new-cap
        const $captainTransferPromise = $.Deferred();

        this.model.captainInstance.save({}, {
            mgmt_uri: targetCaptainUri,
            output_mode: 'json',
            type: 'POST',
        })
        .done(null, () => {
            this.model.captainInstance.pollServiceReady()
            .then(() => { $captainTransferPromise.resolve(); });
        })
        .error(null, () => {
            $captainTransferPromise.reject();
        });

        return $captainTransferPromise;
    },

    beginRollingRestart(workingModel) {
        const $rollingRestartPromise = $.Deferred();

        this.model.rollingRestartInstance.save({
            searchable: workingModel.get('searchable'),
            force: workingModel.get('force'),
        }, {
            output_mode: 'json',
            type: 'POST',
        })
        .done(null, (response) => {
            const responseContent = _.isUndefined(response.entry[0]) ? {} : response.entry[0].content;
            if (responseContent.success) {
                this.model.rollingRestartInstance.pollRollingRestartReady()
                .then(() => { $rollingRestartPromise.resolve(); });
            } else {
                $rollingRestartPromise.reject(responseContent);
            }
        })
        .error(null, () => {
            $rollingRestartPromise.reject();
        });

        return $rollingRestartPromise;
    },

    handleValidationError(hasError, model, messages) {
        this.trigger('serverValidated', hasError, model, messages);
    },
});
