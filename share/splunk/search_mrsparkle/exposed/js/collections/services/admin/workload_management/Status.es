/**
 *
 * Status Collection for Workload Management
 */

import _ from 'underscore';
import SplunkDsBaseCollection from 'collections/SplunkDsBase';
import generalUtils from 'util/general_utils';
import splunkUtil from 'splunk.util';

export default SplunkDsBaseCollection.extend({
    url: 'workloads/status',
    getGeneral(attr) {
        if (_.isUndefined(this.models[0])) {
            if (attr === 'error_message') return _('error returning message').t();
            return false;
        }
        return this.models[0].entry.content.get('general')[attr];
    },
    getErrorMessage() {
        return this.getGeneral('error_message');
    },
    getShortErrorMessage() {
        const keyword = 'error=';
        let msg = this.getErrorMessage();
        if (msg.indexOf(keyword) > 0) {
            msg = msg.substr(msg.indexOf(keyword) + keyword.length);
            msg = msg.charAt(0).toUpperCase() + msg.slice(1);
        }
        return msg;
    },
    isEnabled() {
        return generalUtils.normalizeBoolean(this.getGeneral('enabled'));
    },
    isSupported() {
        return generalUtils.normalizeBoolean(this.getGeneral('isSupported'));
    },
    getDropdownOptions(includeEmptyOption = false) {
        this.workloadPoolOptions = [];
        if (_.isUndefined(this.models[0])) {
            return this.workloadPoolOptions;
        }
        if (includeEmptyOption) {
            this.workloadPoolOptions.push({
                label: _('Policy-Based Pool').t(),
                value: '',
                description: _('Based on assigned policy').t(),
            });
        }
        if (this.isEnabled()) {
            this.populatePoolOptions(
                this.workloadPoolOptions,
                this.models[0].entry.content.get('workload-category:search')['workload-pools'],
                this.getDefaultSearchPoolName(),
                'search',
            );
        }
        return this.workloadPoolOptions;
    },
    populatePoolOptions(poolOptions, pools, defaultPoolName, type) {
        _.each(pools, (model, key) => {
            const cpu = (!_.isUndefined(model.cpu_weight)) ? model.cpu_weight : '';
            const mem = (!_.isUndefined(model.mem_weight)) ? model.mem_weight : '';
            if (key === defaultPoolName) {
                poolOptions.push({
                    label: splunkUtil.sprintf(_('%s (%s default)').t(), key, type),
                    value: key,
                    description: splunkUtil.sprintf(_('CPU: %s%, Memory: %s%').t(), cpu, mem),
                });
            } else {
                poolOptions.push({
                    label: key,
                    value: key,
                    description: splunkUtil.sprintf(_('CPU: %s%, Memory: %s%').t(), cpu, mem),
                });
            }
        });
    },
    getDefaultSearchPoolName() {
        return this.models[0].entry.content.get('workload-category:search').search.default_category_pool;
    },
    getDefaultMiscPoolName() {
        return this.models[0].entry.content.get('workload-category:misc').misc.default_category_pool;
    },
    poolIdExists(poolID) {
        if (_.isUndefined(this.models[0]) ||
            _.isEmpty(this.models[0].entry.content.get('workload-category:search')['workload-pools'])) {
            return undefined;
        }
        return _.has(this.models[0].entry.content.get('workload-category:search')['workload-pools'], poolID) ||
            _.has(this.models[0].entry.content.get('workload-category:ingest')['workload-pools'], poolID);
    },
    bootstrapWorkloadManagementStatus(dfd) {
        if (dfd.state() !== 'resolved') {
            this.fetch({
                success() {
                    dfd.resolve();
                },
                error() {
                    dfd.resolve();
                },
            });
        }
    },
});

