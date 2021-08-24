define(
    [
        'underscore',
        'jquery',
        'module',
        'models/datasets/Column',
        'views/Base',
        'views/shared/datasettable/shared/TableHeader'
    ],
    function(
        _,
        $,
        module,
        ColumnModel,
        BaseView,
        TableHeaderView
    ) {
        return TableHeaderView.extend({
            moduleId: module.id,
            shouldFastRouteOnColumnDrop: true, //Whole table should not re-render when drag and drop of column is complete

            initialize: function(options) {
                TableHeaderView.prototype.initialize.apply(this, arguments);
            },

            events: $.extend({}, TableHeaderView.prototype.events, {
                'dblclick .col-header:not(":first-child"):not(".disabled")': function(e) {
                    var $target = $(e.target),
                        isCtrlClick = e.metaKey || e.ctrlKey || false,
                        isShiftClick = e.shiftKey || false;
                    if ($target && !$target.is('span.resize') && !$target.is('i.field-type')
                            && !isCtrlClick && !isShiftClick) {
                        this.handleDirectRename(e);
                    }
                }
            }),

            startListening: function(options) {
                TableHeaderView.prototype.startListening.apply(this, arguments);
                this.listenTo(this.model.state, 'cutSelection', this.handleCutSelection);
                this.listenTo(this.model.state, 'clearCutSelection', this.handleClearCutSelection);
                this.listenTo(this.model.state, 'columnInteraction', this.toggleClassForColumn);
                this.listenTo(this.model.state, 'columnSelection', this.handleColumnSelect);
                this.listenTo(this.model.state, 'destroyContextualMenus', function() {
                    this.children.typeMenu && this.children.typeMenu.deactivate({ deep: true }).remove();
                    delete this.children.typeMenu;
                });
            },

            toggleClassForColumn: function(index, className, add) {
                var $column = this.$('div[data-col-index=' + index + ']');

                if (add) {
                    $column.addClass(className);
                } else {
                    $column.removeClass(className);
                }
            },

            handleTableSelect: function($allColsSelected) {
                $allColsSelected.addClass('column-selected');

                TableHeaderView.prototype.handleTableSelect.apply(this, arguments);
            },

            addSelectedColumn: function($column) {
                var columnIndex = $column.data('col-index');

                $column.addClass('column-selected');
                this.model.state.trigger('columnInteraction', columnIndex, 'column-selected', true);
            },

            removeSelectedColumn: function($column) {
                var columnIndex = $column.data('col-index');

                if ($column.hasClass('column-selected')) {
                    $column.removeClass('column-selected');
                    this.model.state.trigger('columnInteraction', columnIndex, 'column-selected', false);
                }
            },

            handleCutSelection: function() {
                this.$('.col-header.column-selected').addClass('column-cut');
            },

            handleClearCutSelection: function() {
                this.$('.col-header.column-cut').removeClass('column-cut');
            },

            clearSelection: function() {
                this.$('.column-selected').removeClass('column-selected');
            },

            clearHighlight: function() {
                this.$('.column-highlighted').removeClass('column-highlighted');
            },

            // Always happens after render to ensure elements are in the DOM
            setSelection: function() {
                var selectedColumns = this.model.dataset.selectedColumns,
                    selectedColumnInColumnsCollection,
                    selectedValueString,
                    selectedValue,
                    selectedColumnId,
                    selectedColumn,
                    selectedColumnTopValues,
                    selectionType = this.model.dataset.entry.content.get('dataset.display.selectionType'),
                    selectedText = this.model.dataset.entry.content.get('dataset.display.selectedText'),
                    currentCommandIndex = this.model.dataset.getCurrentCommandIdx(),
                    currentCommand = this.model.dataset.commands.at(currentCommandIndex),
                    $target,
                    triggerArgs;

                if (selectionType === 'column') {
                    selectedColumns.each(function (selectedColumn) {
                        selectedColumnInColumnsCollection = currentCommand.columns.get(selectedColumn.id);

                        // It's possible that the selected column doesn't exist in the table anymore
                        if (selectedColumnInColumnsCollection) {
                            $target = this.$getColHeader(selectedColumnInColumnsCollection.get('name'));
                            this.addSelectedColumn($target);
                            $target.attr("draggable", true);
                        }

                    }, this);

                } else if ((selectionType === 'cell') || (selectionType === 'text')) {
                    // If selected value is present in the summary top results, then tell TopResults view to
                    // render it as selected via the state model
                    selectedValueString = this.model.dataset.entry.content.get('dataset.display.selectedColumnValue');
                    selectedColumnId = selectedColumns && selectedColumns.length > 0 && selectedColumns.first().id;
                    selectedColumn = this.collection.columns.get(selectedColumnId);
                    selectedColumnTopValues = selectedColumn && this.model.summary.extractTopResults(selectedColumn.get('name'));
                    selectedValue = _.where(selectedColumnTopValues, { name: selectedValueString }) || [];

                    if (selectedValue.length === 1) {
                        triggerArgs = {
                            columnName: selectedColumn.get('name'),
                            selectedValue : selectedValueString
                        };
                        if (selectionType === 'text') {
                            // Is Text selection
                            _.extend(triggerArgs, {
                                selectedText: selectedText,
                                startIndex: this.model.dataset.entry.content.get('dataset.display.selectedStart'),
                                endIndex: this.model.dataset.entry.content.get('dataset.display.selectedEnd')
                            });
                        }

                        this.model.state.trigger('setValueSelection', triggerArgs);

                    } else {
                        // selected value is not present in top results. just select the column instead
                        $target = this.$getColHeader(selectedColumn.get('name'));
                        this.addSelectedColumn($target);
                    }
                } else if (selectionType === 'table') {
                    $target = this.$('.col-header');
                    this.handleTableSelect($target);
                }
            },

            toggleBarVisibility: function($column, metrics, metricName, barClass) {
                var $bar = $column.find('.' + barClass),
                    metric = _.findWhere(metrics, { key: metricName }),
                    showMetric = metric && !metric.isZero,
                    barWidth = metric && metric.value;

                if (metrics.length) {
                    if (barClass === 'loading') {
                        this._toggle$BarVisibility($bar, false);
                    } else {
                        this._toggle$BarVisibility($bar, showMetric, barWidth);
                    }
                } else {
                    if (barClass === 'loading') {
                        this._toggle$BarVisibility($bar, true, '0');
                    } else {
                        this._toggle$BarVisibility($bar, false);
                    }
                }
            },

            _toggle$BarVisibility: function($bar, showMetric, barWidth) {
                if (showMetric) {
                    $bar.show();
                    $bar.css('flex', '1 1 ' + barWidth + '%');
                    // If any bar is shown, hide the empty bar
                    this.$('.bar.empty').hide();
                } else {
                    $bar.hide();
                }
            },

            enableSelection: function(enable) {
                if (enable) {
                    this.$('.col-header').removeClass('disabled');
                } else {
                    this.$('.col-header').addClass('disabled');
                }
            },

            render: function(options) {
                TableHeaderView.prototype.render.apply(this, arguments);

                var currentCommandModel,
                    shouldDisableSelection = true,
                    metrics, colName, $column;

                if (this.model.dataset.isTable() && this.options.editingMode) {
                    currentCommandModel = this.model.dataset.getCurrentCommandModel();
                    shouldDisableSelection = !currentCommandModel.isComplete() || !currentCommandModel.isValid();
                }

                if (!this.$el.html() || (options && options.columnsAreDifferent)) {
                    this.$el.html(this.compiledTemplate({
                        ColumnModel: ColumnModel,
                        columns: this.collection.columns
                    }));
                }

                this.collection.columns.each(function(column) {
                    colName = column.get("name");
                    metrics = this.model.resultJsonRows.extractMetrics(column, this.model.summary.extractTopResults(colName));
                    $column = this.$getColHeader(colName);
                    this.toggleBarVisibility($column, metrics, 'MatchedType', 'match');
                    this.toggleBarVisibility($column, metrics, 'MismatchedType', 'mismatch');
                    this.toggleBarVisibility($column, metrics, 'NullOrEmptyValues', 'null-or-empty');
                    this.toggleBarVisibility($column, metrics, undefined, 'loading');
                }, this);

                this.delegateEvents();

                return this;
            },

            template: '\
                <div class="dataset-table-head">\
                    <% if (columns.length > 0) { %>\
                        <div class="col-header all"><span class="name all">*</span></div>\
                    <% } else { %>\
                        <div class="col-header placeholder">&nbsp;</th>\
                    <% } %>\
                    <% columns.each(function(column, index) { %>\
                        <% var colName = column.get("name"); %>\
                        <div class="col-header field type-<%- column.get("type") %>" data-col-index="<%- index %>" data-field="<%- colName %>" style="<%- column.get("display.width") ? "width: " + column.get("display.width") + "px; min-width: " + Math.max(column.get("display.width"), 200) + "px;": "" %>">\
                            <i class="icon-<%- ColumnModel.ICONS[column.get("type")] %> field-type" data-type="<%- column.get("type") %>"></i>\
                            <span class="name" title="<%- colName %>"><%- colName %></span>\
                            <div class="coverage" data-field="<%- colName %>">\
                                <div class="bar match"></div>\
                                <div class="bar mismatch"></div>\
                                <div class="bar null-or-empty"></div>\
                                <div class="bar loading"></div>\
                            </div>\
                        </div>\
                    <% }, this); %>\
                </div>\
            '
        });
    }
);
