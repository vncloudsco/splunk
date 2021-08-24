define(
[
    'jquery',
    'underscore',
    'module',
    'models/Base',
    'views/Base',
    'views/indexes/shared/rollup/js/Select',
    'views/shared/Number',
    'views/indexes/shared/rollup/js/DeleteExceptionButton',
    'views/indexes/shared/rollup/ExceptionPolicy.pcss'
],
function(
    $,
    _,
    module,
    BaseModel,
    BaseView,
    Select,
    NumberControl,
    DeleteExceptionButton,
    css
){
    return BaseView.extend( /** @lends views.ExceptionPolicy.prototype */ {
        moduleId: module.id,
        className: 'exception-policy',
        /**
         * @constructor
         * @memberOf views
         * @name ExceptionPolicy
         * @extends {views.BaseView}
         * @description View for an exception policy for a specific metric
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         * @param {Object} options.collection The model supplied to this class
         */
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);
            var tab = this.getSelectedTab(this.model);
            tab.exceptionItems = this.updateAvailableMetrics(tab);
            tab.aggregationItems = this.updateAvailableAggregations(tab);
            this.model.exceptionModel = new BaseModel({
                tabBarLabel: tab.tabBarLabel,
                label: tab.label,
                exceptionMetric: tab.exceptionMetric,
                aggregation: tab.aggregation,
                exceptionItems: tab.exceptionItems,
                aggregationItems: tab.aggregationItems,
                aggregationValue: tab.aggregationValue,
                validMetric: tab.validMetric,
                validAgg: tab.validAgg,
                validAggValue: tab.validAggValue
            });
            this.children.deleteExceptionButton = new DeleteExceptionButton({
                model: {
                    content: this.model.content,
                    rollup: this.model.rollup
                },
                style: { 'float': 'none' }
            });
            this.children.exceptionDropdown = new Select({
                className: 'metric-filtered-select',
                model: {
                    rollup: this.model.rollup
                },
                filter: true,
                placeholder: _('Select Metric').t(),
                items: tab.exceptionItems,
                defaultValue: tab.exceptionMetric.length ? tab.exceptionMetric : null,
                onChange: this.handleChangedExceptionMetric.bind(this),
                error: !tab.validMetric
            });
            this.children.aggregationDropdown = new Select({
                className: 'aggregation-filtered-select',
                model: {
                    rollup: this.model.rollup
                },
                filter: true,
                placeholder: _('Select Aggregation').t(),
                items: tab.aggregationItems,
                defaultValue: tab.aggregation.length ? tab.aggregation : null,
                onChange: this.handleChangedAggregation.bind(this),
                error: !tab.validAgg
            });
            this.children.aggregationValueNumberControl = new NumberControl({
                inline: true,
                min: 1,
                max: 99,
                roundTo: 0,
                onChange: this.handleChangedAggregationValue.bind(this),
                defaultValue: tab.aggregationValue,
                error: !tab.validAggValue
            });
            this.setAriaAttributes();
            this.startListening();
        },
        setAriaAttributes: function() {
            this.$el.attr({
                role: 'group',
                'aria-label': _('Exception policy').t()
            });
        },
        startListening: function() {
            this.listenTo(this.model.exceptionModel, 'change:exceptionMetric', function(e, value) {
                this.updateModel(false);
            });
            this.listenTo(this.model.exceptionModel, 'change:aggregation', function(e, value) {
                this.updateModel(false);
                this.renderAggregationInputView();
            });
            this.listenTo(this.model.exceptionModel, 'change:aggregationValue', function(e, value) {
                this.updateModel(false);
            });
            this.listenTo(this.model.content, 'change:tabIndex', this.handleTabChange);
        },
        handleChangedExceptionMetric: function(e, value) {
            var exceptionMetric = value.value;
            this.model.exceptionModel.set({
                exceptionMetric: exceptionMetric,
                validMetric: exceptionMetric.length > 0
            });
        },
        handleChangedAggregation: function(e, value) {
            var aggregation = value.value;
            var validAggValue = this.model.exceptionModel.get('validAggValue');
            var aggRequiresValue = aggregation === 'perc' || aggregation === 'upperperc';
            if (!validAggValue && !aggRequiresValue) {
                validAggValue = true;
            }
            this.model.exceptionModel.set({
                aggregation: aggregation,
                validAgg: aggregation.length > 0,
                validAggValue: validAggValue
            });
        },
        handleChangedAggregationValue: function(e, value) {
            var aggregationValue = value.value;
            this.model.exceptionModel.set({
                aggregationValue: aggregationValue,
                validAggValue: aggregationValue !== undefined
            }, { silent: true });
            this.updateModel(true);
            this.children.aggregationValueNumberControl.options.error = aggregationValue === undefined;
            this.renderAggregationValueNumberControl();
        },
        updateAvailableMetrics: function(currentTab) {
            var metrics = this.collection.metrics.getItems();
            var metricsCopy = $.extend(true, [], metrics);
            var currentMetric = currentTab.exceptionMetric;
            var allTabs = this.model.rollup.get('tabs');
            for (var i = 1; i < allTabs.length; i++) {
                var tab = allTabs[i];
                var selectedMetric = tab.exceptionMetric;
                if (selectedMetric !== currentMetric && selectedMetric.length) {
                    var index = metricsCopy.findIndex(function(metric) {
                        return metric.value === selectedMetric;
                    });
                    if (index >= 0) {
                        metricsCopy.splice(index, 1);
                    }
                }
            }
            return metricsCopy;
        },
        updateAvailableAggregations: function(currentTab) {
            var defaultAggregation = this.model.rollup.get('tabs')[0].aggregation;
            return currentTab.aggregationItems.filter(function(agg) {
                return agg.value !== defaultAggregation;
            });
        },
        getSelectedTab: function(model) {
            var tabIndex = model.content.get('tabIndex');
            var tabs = model.rollup.get('tabs');
            return tabs[parseInt(tabIndex)];
        },
        getLabelForMetric: function(exceptionMetric) {
            var metrics = this.collection.metrics.getItems();
            var filteredMetrics = metrics.filter(function(metric) {
                return metric.value === exceptionMetric;
            });
            return metrics.length ? filteredMetrics[0].label : null;
        },
        updateModel: function(silent) {
            var tabs = $.extend(true, [], this.model.rollup.get('tabs'));
            var tabIndex = this.model.content.get('tabIndex');
            var exceptionMetric = this.model.exceptionModel.get('exceptionMetric');
            var tabBarLabel = exceptionMetric.length
                ? this.getLabelForMetric(exceptionMetric)
                : _('Select Metric').t();
            var label = exceptionMetric.length
                ? this.getLabelForMetric(exceptionMetric) + _(' Exception Rule').t()
                : _('Exception Rule').t();
            tabs[tabIndex] = {
                label: label,
                tabBarLabel: tabBarLabel,
                exceptionMetric: this.model.exceptionModel.get('exceptionMetric'),
                aggregation: this.model.exceptionModel.get('aggregation'),
                exceptionItems: this.model.exceptionModel.get('exceptionItems'),
                aggregationItems: this.model.exceptionModel.get('aggregationItems'),
                aggregationValue: this.model.exceptionModel.get('aggregationValue'),
                validMetric: this.model.exceptionModel.get('validMetric'),
                validAgg: this.model.exceptionModel.get('validAgg'),
                validAggValue: this.model.exceptionModel.get('validAggValue'),
            };
            this.model.rollup.set({ 'tabs': tabs }, { silent: silent });
            if (exceptionMetric) {
                $('.exception-title').text(label);
            }
        },
        handleTabChange: function() {
            var tab = this.getSelectedTab(this.model);
            this.model.exceptionModel.set({
                tabBarLabel: tab.tabBarLabel,
                label: tab.label,
                exceptionMetric: tab.exceptionMetric,
                aggregation: tab.aggregation,
                exceptionItems: tab.exceptionItems,
                aggregationItems: tab.aggregationItems,
                aggregationValue: tab.aggregationValue,
                validMetric: tab.validMetric,
                validAgg: tab.validAgg,
                validAggValue: tab.validAggValue
            }, { silent: true });
            $('.exception-title').text(tab.label);
        },
        renderAggregationInputView: function() {
            var selectedAgg = this.model.exceptionModel.get('aggregation');
            var showInput = selectedAgg === 'upperperc' || selectedAgg === 'perc';
            if (showInput) {
                this.$('.aggregtion-parameter-placeholder').show();
            } else {
                this.$('.aggregtion-parameter-placeholder').hide();
            }
        },
        renderAggregationValueNumberControl: function() {
            // necessary in order to reflect proper error highlighting
            this.$(".aggregtion-parameter-placeholder").empty();
            this.children.aggregationValueNumberControl.render().appendTo(this.$(".aggregtion-parameter-placeholder"));
            this.$('.aggregtion-parameter-placeholder input')[0].focus();
        },
        render: function() {
            if (!this.el.innerHTML) {
                var exceptionMetric = this.model.exceptionModel.get('exceptionMetric');
                var validAggValue = this.model.exceptionModel.get('validAggValue');
                var aggregationErrorText = _("Percentile parameter field cannot be empty.").t();
                var template = _.template(this.template, {
                    _: _,
                    label: exceptionMetric.length ? this.model.exceptionModel.get('label') : _("Exception Rule").t(),
                    defaultAggregation: this.model.rollup.get('tabs')[0].aggregation,
                    aggregationErrorText: validAggValue ? undefined : aggregationErrorText
                });
                this.$el.html(template);
            }
            this.children.deleteExceptionButton.render().appendTo(this.$(".delete-exception-placeholder"));
            this.children.exceptionDropdown.render().appendTo(this.$(".metric-dropdown-placeholder"));
            this.children.aggregationDropdown.render().appendTo(this.$(".aggregation-dropdown-placeholder"));
            this.children.aggregationValueNumberControl.render().appendTo(this.$(".aggregtion-parameter-placeholder"));

            this.renderAggregationInputView();
            return this;
        },
        template: '\
            <div class="exception-policy-container">\
                <div>\
                    <h3 class="exception-title"><%- label %></h3>\
                    <span class="delete-exception-placeholder"></span>\
                </div>\
                <span class="rollup-help-text"><%- _("Override the default rollup aggregation (" + defaultAggregation + ") for a metric.").t() %></span>\
                <p class="exception-header exception-metric-header"><%- _("Exception Metric:").t() %></p>\
                <span class="rollup-help-text metric-help-text"><%- _("Lists metrics indexed over the last 24 hours.").t() %></span>\
                <div class="metric-dropdown-placeholder"></div>\
                <p class="exception-header aggregation-header"><%- _("Aggregation:").t() %></p>\
                <div class="aggregation-dropdown-placeholder"></div>\
                <span class="aggregtion-parameter-placeholder"></span>\
                <div class="aggregation-value-error"><%- aggregationErrorText %></div>\
            </div>\
        '
    });
});
