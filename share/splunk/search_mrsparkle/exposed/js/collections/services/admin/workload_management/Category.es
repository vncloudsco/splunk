/**
 *
 * Category Collection for Workload Management
 */

import _ from 'underscore';
import Model from 'models/services/admin/workload_management/Category';
import SplunkDsBaseCollection from 'collections/SplunkDsBase';

export default SplunkDsBaseCollection.extend({
    url: 'workloads/categories',
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

    prepareCategories() {
        if (this.length <= 0) {
            return [];
        }

        this.each((model) => {
            switch (model.getName()) {
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

        return this.models;
    },

    getCpuWeightByCategory(category) {
        const categoryModel = this.findByEntryName(category);
        return (_.isUndefined(categoryModel)) ?
            0 : categoryModel.entry.content.get('cpu_weight');
    },

    getCpuWeightSumByCategory(category) {
        const categoryModel = this.findByEntryName(category);
        return (_.isUndefined(categoryModel)) ?
            0 : categoryModel.entry.content.get('cpu_weight_sum');
    },

    getMemWeightByCategory(category) {
        const categoryModel = this.findByEntryName(category);
        return (_.isUndefined(categoryModel)) ?
            0 : categoryModel.entry.content.get('mem_weight');
    },

    isCategoryAllocated(category) {
        return this.getMemWeightByCategory(category) > 0 || this.getCpuWeightByCategory(category) > 0;
    },

    getDynamicAllocatedCpu(enteredCpuWeight, category) {
        let allCategoryCpuWeight = 0;
        this.each((model) => {
            if (model.getName() !== category) {
                allCategoryCpuWeight += model.getCpuWeight();
            }
        });

        const result = 100 * (enteredCpuWeight / (allCategoryCpuWeight + enteredCpuWeight));

        return (_.isNaN(result)) ? 0 : result.toFixed(2);
    },

    getDynamicMemAllocatedPercent(enteredMemWeight) {
        return (_.isUndefined(enteredMemWeight)) ? 0 : enteredMemWeight.toFixed(2);
    },

    updateCategory(categoryModel, data) {
        const model = _.isEmpty(categoryModel) ? new Model() : categoryModel;
        model.entry.content.clear();
        model.entry.content.set(data);

        return model.save();
    },

});
