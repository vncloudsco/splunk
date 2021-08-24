import _ from 'underscore';
import SplunkDBaseModel from 'models/SplunkDBase';
import splunkUtil from 'splunk.util';

export default SplunkDBaseModel.extend({
    urlRoot: 'services/workloads/categories',
    url: 'workloads/categories',

    getType() {
        return 'category';
    },
    getCategory() {
        return this.get('category');
    },
    getName() {
        return this.entry.get('name') || '';
    },
    getLabel() {
        return splunkUtil.sprintf(
            _('%s Category').t(),
            this.entry.get('name').charAt(0).toUpperCase() + this.entry.get('name').slice(1),
        );
    },
    getCpuAllocatedPercent() {
        const cpuAllocatedPercent = this.entry.content.get('cpu_allocated_percent') || 0;
        return cpuAllocatedPercent.toFixed(2);
    },
    getCpuWeight() {
        return this.entry.content.get('cpu_weight') || 0;
    },
    getCpuWeightSum() {
        return this.entry.content.get('cpu_weight_sum') || 0;
    },
    getMemWeight() {
        return this.entry.content.get('mem_weight') || 0;
    },
    getMemAllocatedPercent() {
        const memAllocatedPercent = this.entry.content.get('mem_allocated_percent') || 0;
        return memAllocatedPercent.toFixed(2);
    },
    setOrder(value) {
        this.entry.content.set('order', value);
    },
});
