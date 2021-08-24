import SplunkDBaseModel from 'models/SplunkDBase';
import generalUtils from 'util/general_utils';
import _ from 'underscore';

export default SplunkDBaseModel.extend({
    urlRoot: 'services/workloads/pools',
    url: 'workloads/pools',

    getType() {
        return 'pool';
    },
    getCpuWeight() {
        return this.entry.content.get('cpu_weight') || 0;
    },
    getCpuAllocatedPercent() {
        return this.entry.content.get('cpu_allocated_percent') || 0;
    },
    getMemWeight() {
        return this.entry.content.get('mem_weight') || 0;
    },
    getMemAllocatedPercent() {
        return this.entry.content.get('mem_allocated_percent') || 0;
    },
    getPoolCategory() {
        return this.entry.content.get('category');
    },
    getName() {
        return this.entry.get('name');
    },
    isDefaultPool() {
        return generalUtils.normalizeBoolean(this.entry.content.get('default_category_pool')) || false;
    },
    isIngestPool() {
        return this.get('isIngestPool');
    },
    isApplied() {
        return this.get('isApplied');
    },
    setOrder(value) {
        this.entry.content.set('order', value);
    },
    setDefaultPool(poolModel) {
        if (!_.isEmpty(poolModel)) {
            this.entry.content.set('default_category_pool', poolModel.entry.get('name'));
        }
    },
});
