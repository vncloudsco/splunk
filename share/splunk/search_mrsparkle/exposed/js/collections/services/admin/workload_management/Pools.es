/**
 *
 * Pools Collection for Workload Management
 */

import _ from 'underscore';
import Model from 'models/services/admin/workload_management/Pool';
import SplunkDsBaseCollection from 'collections/SplunkDsBase';
import generalUtils from 'util/general_utils';

export default SplunkDsBaseCollection.extend({
    url: 'workloads/pools',
    model: Model,

    initialize(...args) {
        this.model = this.model || {};
        SplunkDsBaseCollection.prototype.initialize.apply(this, args);
    },

    comparator(model) {
        return model.entry.content.get('order');
    },

    fetch(options = {}) {
        const extendedOptions = Object.assign(options, {});
        extendedOptions.data = Object.assign(options.data || {}, {
            count: -1,
        });

        return SplunkDsBaseCollection.prototype.fetch.call(this, options);
    },

    preparePools(selectedCategory) {
        if (this.length <= 0) {
            return [];
        }

        this.each((model) => {
            switch (model.getPoolCategory()) {
                case 'search':
                    model.setOrder(0);
                    break;
                case 'ingest':
                    model.setOrder(1);
                    break;
                case 'misc':
                    model.setOrder(2);
                    break;
                default:
                    model.setOrder(0);
                    break;
            }
        });

        this.sort();

        return this.filter((model) => {
            if (selectedCategory !== 'all') {
                return model.entry.content.get('category') === selectedCategory;
            }
            return true;
        });
    },

    updatePool(poolModel, data) {
        const model = _.isEmpty(poolModel) ? new Model() : poolModel;
        model.entry.content.clear();
        model.entry.content.set(data);

        return model.save();
    },

    deletePool(model) {
        return model.destroy();
    },

    filterOutIngestMisc() {
        return this.filter(model =>
            model.entry.content.get('category') !== 'ingest' &&
            model.entry.content.get('category') !== 'misc' &&
            model.entry.get('name') !== 'workload_rules_order',
        );
    },

    getDefaultPool(category) {
        return this.filter(model =>
            model.entry.content.get('category') === category &&
            generalUtils.normalizeBoolean(model.entry.content.get('default_category_pool')),
        )[0];
    },

    getPoolsByCategory(category) {
        return this.filter(model => model.entry.content.get('category') === category);
    },

    getDynamicAllocatedCpu(enteredCpuWeight, poolUpdateModalState, categoryCollection) {
        let cpuWeight = enteredCpuWeight;
        const categoryCpuWeightSum = categoryCollection.getCpuWeightSumByCategory(poolUpdateModalState.category);
        const categoryCpuWeight = categoryCollection.getCpuWeightByCategory(poolUpdateModalState.category);
        let allPoolCpuWeight = 0;
        _.each(this.getPoolsByCategory(poolUpdateModalState.category), (pool) => {
            if (poolUpdateModalState.name !== pool.getName()) {
                allPoolCpuWeight += pool.getCpuWeight();
            }
        });
        if (poolUpdateModalState.field === 'category') {
            cpuWeight = poolUpdateModalState.cpu_weight || 0;
        }

        const result = (cpuWeight / (allPoolCpuWeight + cpuWeight)) *
            (categoryCpuWeight / categoryCpuWeightSum) * 100;

        return (_.isNaN(result)) ? 0 : result.toFixed(2);
    },

    getDynamicAllocatedMem(poolUpdateModalState, categoryCollection) {
        const categoryMemWeight = categoryCollection.getMemWeightByCategory(poolUpdateModalState.category);
        const result = (poolUpdateModalState.mem_weight * categoryMemWeight) / 100;

        return (_.isNaN(result)) ? 0 : result.toFixed(2);
    },

});
