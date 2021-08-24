define(
    [
        'jquery',
        'underscore',
        'models/Base',
        'models/SplunkDBase',
        'util/indexes/RollupUtils',
        'util/indexes/TimeConfigUtils'
    ],
    function(
        $,
        _,
        BaseModel,
        SplunkDBaseModel,
        RollupUtils,
        TimeConfigUtils
    ) {
        return SplunkDBaseModel.extend({
            url: 'catalog/metricstore/rollup',
            exists: function() {
                var tabs = this.get('tabs');
                return tabs && tabs.length;
            },
            updateErrors: function(options) {
                options = options || {};
                _.defaults(options, {
                    setRollupAttrOpts: {},
                    resetDuplicateSummaryOpts: {silent: true},
                });
                var tabs = $.extend(true, [], this.get('tabs'));
                var generalPolicyError = false;
                var summaries = tabs[0].summaries;
                var duplicateSummaryError = RollupUtils.getDuplicateSummaryError(summaries);
                this.set({'duplicateSummaryError': false}, options.resetDuplicateSummaryOpts);
                if (duplicateSummaryError) {
                    this.set({'duplicateSummaryError': true}, options.setRollupAttrOpts);
                    return 0;
                }
                for (var i = 0; i < summaries.length; i++) {
                    var summary = summaries[i];
                    summary.timeError = TimeConfigUtils.getTimeErrorForSummary({
                        minSpanAllowed: this.get('minSpanAllowed'),
                        timeType: summary.timeType,
                        timeValue: summary.timeValue
                    });
                    summary.metricError = !summary.targetIndex;
                    generalPolicyError = generalPolicyError || summary.metricError || summary.timeError;
                }
                if (generalPolicyError) {
                    this.set({'tabs': tabs}, options.setRollupAttrOpts);
                    return 0;
                }
                var exceptionErrorTab = null;
                for (var j = 1; j < tabs.length; j++) {
                    var tab = tabs[j];
                    var isEmptyTab = !tab.exceptionMetric.length && !tab.aggregation.length;
                    if (isEmptyTab) {
                        continue;
                    }
                    tab.validMetric = tab.exceptionMetric.length;
                    tab.validAgg = this.getValidAgg(j);
                    tab.validAggValue = tab.aggregation === 'perc' || tab.aggregation === 'upperperc'
                        ? this.isValidAggregationValue(j)
                        : true;
                    if (!tab.validMetric || !tab.validAgg || !tab.validAggValue) {
                        exceptionErrorTab = j;
                        break;
                    }
                }
                this.set({'tabs': tabs}, options.setRollupAttrOpts);
                return exceptionErrorTab;
            },
            getValidAgg: function(tabIndex) {
                var tab = this.get('tabs')[tabIndex];
                if (!tab) {
                    return false;
                }
                var defaultAggregation = tab.aggregation.length ? tab.aggregation : null;
                var generalPolicyTab = this.get('tabs')[0];
                // if default aggregation was changed in .conf to match a previous value aggregation is invalid
                return defaultAggregation && defaultAggregation !== generalPolicyTab.aggregation;
            },
            sanitizeTabs: function() {
                var model = $.extend(true, {}, this);
                var tabs = model.get('tabs');
                return tabs.filter(function(tab, i) {
                    return !i || tab.exceptionMetric.length || tab.aggregation.length;
                }.bind(this));
            },
            updateRollupMetrics: function(metrics) {
                var rollupModels = metrics.filter(function(model) {
                    return model.entry.get('name').indexOf('_mrollup_') < 0;
                });
                metrics.models = rollupModels;
                metrics.length = metrics.models.length;
                var metricNames = metrics.map(function(model) {
                    return model.entry.get('name');
                });
                var tabs = $.extend(true, [], this.get('tabs'));
                if (!tabs || !tabs.length) {
                    return;
                }
                var existingMetrics = tabs
                    .map(function(tab) { return tab.exceptionMetric; })
                    .filter(function(metric) { return metric !== undefined; });
                if (!existingMetrics) {
                    return;
                }
                existingMetrics.forEach(function(metric) {
                    if (metricNames.indexOf(metric) < 0) {
                        var model = new BaseModel();
                        model.entry = new BaseModel();
                        model.entry.set('name', metric);
                        metrics.models.push(model);
                        metrics.length += 1;
                    }
                });
            },
            updateRollupDimensions: function(dimensions) {
                var rollupDimensions = dimensions.filter(function(model) {
                    return RollupUtils.IGNORED_DIMENSIONS.indexOf(model.entry.get('name')) < 0;
                });
                dimensions.models = rollupDimensions;
                dimensions.length = dimensions.models.length;
                var dimensionNames = dimensions.map(function(model) {
                    return model.entry.get('name');
                });
                var tabs = this.get('tabs');
                if (!tabs || !tabs.length) {
                    return;
                }
                var existingDimensions = tabs[0].selectedItems;
                if (!existingDimensions) {
                    return;
                }
                existingDimensions.forEach(function(dimension) {
                    if (dimensionNames.indexOf(dimension) < 0) {
                        var model = new BaseModel();
                        model.entry = new BaseModel();
                        model.entry.set('name', dimension);
                        dimensions.models.push(model);
                        dimensions.length += 1;
                    }
                });
            },
            updateRollupIndexes: function(indexes, options) {
                options = options || {};
                _.defaults(options, {
                    setRollupAttrOpts: {silent: true}
                });
                var indexNames = indexes.map(function(model) {
                    return model.entry.get('name');
                });
                var tabs = $.extend(true, [], this.get('tabs'));
                var summaries = tabs[0].summaries;
                summaries.forEach(function(summary) {
                    if (indexNames.indexOf(summary.targetIndex) < 0) {
                        summary.targetIndex = "";
                    }
                });
                this.set({'tabs': tabs}, options.setRollupAttrOpts);
            },
            updateRollupCollections: function(props, options) {
                options = options || {};
                var collection = props.collection;
                if (this.exists()) {
                    this.updateRollupIndexes(collection.indexes, options);
                }
                this.updateRollupDimensions(collection.dimensions);
                this.updateRollupMetrics(collection.metrics);
            },
            isValidAggregationValue: function(tabIndex) {
                var tab = this.get('tabs')[tabIndex];
                if (!tab) {
                    return false;
                }
                var aggValue = tab.aggregationValue;
                if (!isFinite(aggValue)) {
                    return false;
                }
                return Number(aggValue) >= 1 && Number(aggValue) <= 99;
            },
            getAggregation: function(tabIndex) {
                var tab = this.get('tabs')[tabIndex];
                if (!tab) {
                    return undefined;
                }
                var aggregation = tab.aggregation;
                if (aggregation === 'perc' || aggregation === 'upperperc') {
                    return aggregation + tab.aggregationValue;
                }
                return aggregation;
            },
            setProps: function(isUpdate, options) {
                options = options || {};
                var attrs = this.attributes;
                var props = {};
                if (!isUpdate && attrs.name) {
                    props.name = attrs.name;
                }
                if (attrs.tabs && attrs.tabs.length) {
                    var tabs = attrs.tabs;
                    var generalPolicy = tabs[0];
                    if (generalPolicy.listType) {
                        props.dimension_list_type = generalPolicy.listType;
                        if (generalPolicy.selectedItems && generalPolicy.selectedItems.length) {
                            props.dimension_list = generalPolicy.selectedItems.join(',');
                        }
                    } else {
                        props.dimension_list_type = 'excluded';
                    }
                    if (generalPolicy.summaries) {
                        props.summaries = generalPolicy.summaries.map(function(summary) {
                            return summary.timeValue + summary.timeType + '|' + summary.targetIndex;
                        }).join(',');
                    }
                    if (tabs.length > 1) {
                        var exceptionTabs = tabs.slice(1);
                        props.metric_overrides = exceptionTabs.map(function(tab, i) {
                            var aggregation = this.getAggregation(i + 1);
                            return tab.exceptionMetric + '|' + aggregation;
                        }.bind(this)).join(',');
                    }
                }
                this.entry.content.set(props, options);
            },
            destroy: function(options) {
                this.set({'id': this.url + '/' + this.get('name')}, options);
                return SplunkDBaseModel.prototype.destroy.apply(this, arguments);
            },
            update: function(key, val, options) {
                this.entry.content.clear(options);
                this.set({'id': this.url + '/' + this.get('name')}, options);
                var isUpdate = true;
                this.setProps(isUpdate, options);
                return SplunkDBaseModel.prototype.save.apply(this, arguments);
            },
            save: function(key, val, options) {
                this.entry.content.clear(options);
                this.set({'id': undefined}, options);
                var isUpdate = false;
                this.setProps(isUpdate, options);
                return SplunkDBaseModel.prototype.save.apply(this, arguments);
            }
        });
    }
);
