define(
    [
        'underscore',
        'jquery',
        'module',
        'collections/datasets/Cells',
        'models/datasets/Column',
        'views/Base',
        'views/shared/summarytable/resultsbody/column/Metrics',
        'views/shared/summarytable/resultsbody/column/TopResult',
        'models/datasets/Column'
    ],
    function(
        _,
        $,
        module,
        CellsCollection,
        ColumnModel,
        BaseView,
        MetricsResultsView,
        TopResultsView
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'summary-table-column',

            attributes: function() {
                return {
                    'data-col-index': this.options.colIndex
                };
            },

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.collection = this.collection || {};
            },

            createCellsCollection: function(options) {
                options = options || {};
                this.collection.cells = new CellsCollection();

                var results = this.model.summary.extractTopResults(this.model.column.get('name')),
                    extractedMetrics = options.extractedMetrics,
                    columnType = this.model.column.get('type'),
                    columnName = this.model.column.get('name'),
                    columnIndex = this.options.colIndex,
                    nullValues, nullValuesPercentage;

                if (extractedMetrics && extractedMetrics.length) {
                    nullValues = _.where(extractedMetrics, { key: 'NullValues' })[0];
                    // If extractedMetrics doesn't contain 'NullValues' object, then it has no NullValues, so default to zero
                    nullValuesPercentage = (nullValues && parseFloat(nullValues.value, 10)) || 0;
                    if (nullValuesPercentage > 0) {
                        this.collection.cells.addCell({
                            columnType: columnType,
                            field: columnName,
                            colIndex: columnIndex,
                            nullValueMetric: nullValues,
                            values: []
                        });
                    }
                }

                _.each(results, function(result) {
                    this.collection.cells.addCell({
                        columnType: columnType,
                        colIndex: columnIndex,
                        field: columnName,
                        nullValueMetric: nullValues,
                        values: [ result.name ],
                        unscaledPercentage: result.percentage
                    });
                }, this);
            },

            topResultsViewsFromCollection: function() {
                return this.collection.cells.map(function(cellModel) {
                    return new TopResultsView({
                        model: {
                            cell: cellModel,
                            column: this.model.column,
                            dataset: this.model.dataset,
                            state: this.model.state
                        },
                        editingMode: this.options.editingMode
                    });
                }, this);
            },

            shouldRenderTopResults: function() {
                // It does not make sense to display top results for _raw and timestamp fields
                return !this.model.column.isSplunkTime()
                    && (this.model.column.get('type') !== ColumnModel.TYPES._RAW);
            },

            enableSelection: function(enable) {
                this.children.metricsResultsView && this.children.metricsResultsView.enableSelection(enable);
                _.each(this.children.topResultsViews, function(resultView) {
                    resultView.enableSelection(enable);
                }, this);
            },

            render: function() {
                var columnWidth = this.model.column.get('display.width'),
                    results = this.model.summary.extractTopResults(this.model.column.get('name')),
                    extractedMetrics = this.model.resultJsonRows.extractMetrics(this.model.column, results),
                    shouldDisableSelection = true,
                    valueBeingEdited, newEditValue, currentCommandModel;

                if (columnWidth) {
                    this.$el.css('width', columnWidth + 'px');
                }
                this.$el.attr('data-col-index', this.options.index);
                this.$el.addClass('column-' + this.model.column.get('name'));

                if (this.model.dataset.isTable() && this.options.editingMode) {
                    currentCommandModel = this.model.dataset.getCurrentCommandModel();
                    shouldDisableSelection = !currentCommandModel.isComplete() || !currentCommandModel.isValid();
                }

                // Metrics View
                if (this.children.metricsResultsView) {
                    this.children.metricsResultsView.deactivate({deep: true}).remove();
                    delete this.children.metricsResultsView;
                }
                this.children.metricsResultsView = new MetricsResultsView({
                    model: {
                        dataset: this.model.dataset,
                        timeline: this.model.timeline,
                        resultJsonRows: this.model.resultJsonRows,
                        column: this.model.column,
                        state: this.model.state,
                        dataSummaryJob: this.model.dataSummaryJob
                    },
                    colIndex: this.options.colIndex,
                    extractedMetrics: extractedMetrics,
                    editingMode: this.options.editingMode
                });
                this.children.metricsResultsView.activate({deep: true}).render().appendTo(this.$el);

                // Top Results Views
                if (this.shouldRenderTopResults()) {
                    _.each(this.children.topResultsViews, function(resultView, i) {
                        if (resultView.$('input.cell-value-input').length) {
                            // There is a direct rename textbox in this cell, so we must re-render the textbox when we
                            // re-render using renderValueInput() below, with these preserved values.
                            newEditValue = resultView.$('input.cell-value-input').val();
                            valueBeingEdited = resultView.model.cell.getValue();
                        }
                        resultView.deactivate({deep: true}).remove();
                        delete this.children.topResultsViews[i];
                    }, this);

                    this.createCellsCollection({ extractedMetrics: extractedMetrics });
                    this.children.topResultsViews = this.topResultsViewsFromCollection();

                    _.each(this.children.topResultsViews, function(resultView) {
                        resultView.render().activate({deep: true}).appendTo(this.$el);
                        if (!_.isUndefined(valueBeingEdited) && resultView.model.cell.getValue() === valueBeingEdited) {
                            resultView.renderValueInput(valueBeingEdited, newEditValue);
                        }
                    }, this);
                }

                return this;
            }
        });
    }
);


