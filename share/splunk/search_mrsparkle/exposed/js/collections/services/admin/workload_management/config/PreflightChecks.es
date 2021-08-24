/**
 *
 * Config Collection for Workload Management
 */

import _ from 'underscore';
import SplunkDsBaseCollection from 'collections/SplunkDsBase';
import generalUtils from 'util/general_utils';

export default SplunkDsBaseCollection.extend({
    url: 'workloads/config/preflight-checks',
    allPreflightChecksPass() {
        if (_.isUndefined(this.models[0])) {
            // preflight-checks endpoint is gaurded by [edit,list]_workload_pool capability
            return true;
        }
        return generalUtils.normalizeBoolean(this.models[0].entry.content.get('general').preflight_checks_status);
    },
    getPreflightChecks() {
        this.checks = [];
        if (_.isUndefined(this.models[0])) {
            return this.checks;
        }
        _.each(this.models[0].entry.content.attributes, (model, key) => {
            if (key !== 'general' && key !== 'eai:acl') {
                this.checks.push({
                    id: key,
                    title: model.title,
                    preflight_check_status: generalUtils.normalizeBoolean(model.preflight_check_status),
                    mitigation: model.mitigation,
                });
            }
        });
        return this.checks;
    },
});
