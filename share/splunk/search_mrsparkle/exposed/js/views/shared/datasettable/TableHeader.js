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
            shouldFastRouteOnColumnDrop: false, // Whole table should re-render when drag and drop of column is complete

            initialize: function(options) {
                TableHeaderView.prototype.initialize.apply(this, arguments);
            },

            events: $.extend({}, TableHeaderView.prototype.events, {
                'mousedown .col-header:not(":first-child"):not(".disabled")': function(e) {
                    var isLeftClick = (e.which === 1);

                    if (isLeftClick && $(e.target).hasClass('resize') &&
                            (this.$('.field-name-input').length === 0 || !$(this.$('.field-name-input')).is(':visible'))) {
                        this.handleColumnResizeDragStart(e);
                    }
                },
                'dblclick .col-header:not(":first-child"):not(".disabled")': function(e) {
                    var $target = $(e.target),
                        isCtrlClick = e.metaKey || e.ctrlKey || false,
                        isShiftClick = e.shiftKey || false;
                    if (this.model.dataset.isTable() && this.options.editingMode
                            && $target && !$target.is('span.resize') && !$target.is('i.field-type')
                            && !isCtrlClick && !isShiftClick) {
                        this.handleDirectRename(e);
                    }
                }
            }),

            startListening: function(options) {
                TableHeaderView.prototype.startListening.apply(this, arguments);
                this.listenTo(this.model.state, 'cutSelection', this.handleCutSelection);
                this.listenTo(this.model.state, 'clearCutSelection', this.handleClearCutSelection);
                this.listenTo(this.model.state, 'destroyContextualMenus', function() {
                    this.children.typeMenu && this.children.typeMenu.deactivate({ deep: true }).remove();
                    delete this.children.typeMenu;
                });
            },

            handleTableSelect: function($allThs) {
                $allThs.not(':last-child').addClass('column-selected');
                $allThs.filter(':last-child').addClass('column-selected-end');

                TableHeaderView.prototype.handleTableSelect.apply(this, arguments);
            },

            addSelectedColumn: function($column) {
                var columnIndex = $column.data('col-index'),
                    $previousColumn = this.$('.col-header[data-col-index=' + (columnIndex-1) +']'),
                    $nextColumn = this.$('.col-header[data-col-index=' + (columnIndex+1) +']');


                // We need to check with the previous and next columns' selection states in order to ensure the
                // selection border doesn't appear between two adjacent items.
                if ($previousColumn.hasClass('column-selected-end')) {
                    // The previous column used to be an end, and now it needs to not be an end, since we're selected
                    $previousColumn.removeClass('column-selected-end').addClass('column-selected');
                    this.model.state.trigger('columnInteraction', columnIndex-1, 'column-selected-end', false);
                    this.model.state.trigger('columnInteraction', columnIndex-1, 'column-selected', true);
                }
                if ($nextColumn.hasClass('column-selected') || $nextColumn.hasClass('column-selected-end')) {
                    // The next column is selected, so we're not the end
                    $column.addClass('column-selected');
                    this.model.state.trigger('columnInteraction', columnIndex, 'column-selected', true);
                } else {
                    // Otherwise, we are the new end
                    $column.addClass('column-selected-end');
                    this.model.state.trigger('columnInteraction', columnIndex, 'column-selected-end', true);
                }
            },

            removeSelectedColumn: function($column) {
                var columnIndex = $column.data('col-index'),
                    $previousColumn = this.$('.col-header[data-col-index=' + (columnIndex-1) +']');

                // We're essentially going to reverse the work done in addSelectedColumn for the previous column.
                if ($previousColumn.hasClass('column-selected')) {
                    // The previous column becomes an end now
                    $previousColumn.removeClass('column-selected').addClass('column-selected-end');
                    this.model.state.trigger('columnInteraction', columnIndex-1, 'column-selected', false);
                    this.model.state.trigger('columnInteraction', columnIndex-1, 'column-selected-end', true);
                }
                if ($column.hasClass('column-selected')) {
                    $column.removeClass('column-selected');
                    this.model.state.trigger('columnInteraction', columnIndex, 'column-selected', false);
                } else if ($column.hasClass('column-selected-end')) {
                    $column.removeClass('column-selected-end');
                    this.model.state.trigger('columnInteraction', columnIndex, 'column-selected-end', false);
                }
            },

            handleColumnResizeDragStart: function(e) {
                e.preventDefault();

                this.resizeStartPosition = e.pageX;
                this.$resultsTable = this.options.resultsTable.$el;
                this.$colHeader = $(e.currentTarget).closest('.col-header');

                this.resizeStartColWidth = $(this.$colHeader[0]).width();
                this.resizeStartTableWidth = this.$resultsTable[0].clientWidth;
                this.resizeMinChange = this.options.minColumnWidth - this.resizeStartColWidth;

                $('html').on('mousemove.resize', this.handleColumnResizeDrag.bind(this));
                $('html').on('mouseup.resize', this.handleColumnResizeDragEnd.bind(this));
            },

            handleColumnResizeDrag: function(e) {
                var change = Math.max(e.pageX - this.resizeStartPosition, this.resizeMinChange),
                    $realTable = this.$el.closest('.table-results'),
                    $realHeading = this.$getColHeader(this.$colHeader.data('field')),
                    currentCommandModel = this.model.dataset.getCurrentCommandModel(),
                    currentColumns = currentCommandModel.columns,
                    columnToModify = currentColumns.find(function(column) {
                        return column.get('name') === this.$colHeader.data('field');
                    }, this),
                    columnIsSelected = this.$colHeader.hasClass('column-selected-end') || this.$colHeader.hasClass('column-selected'),
                    columnWidth;

                this.$colHeader.width(this.resizeStartColWidth + change);
                this.$resultsTable.width(this.resizeStartTableWidth + change);
                $realHeading.width(this.resizeStartColWidth + change);
                $realTable.width(this.resizeStartTableWidth + change);

                columnWidth = this.$colHeader[0].clientWidth;

                // Compensate for selection borders, which are not calculated as part of the client width but should be
                if (columnIsSelected) {
                    columnWidth += 4;
                }

                columnToModify.set({
                    'display.width': columnWidth
                });

                this.model.state.trigger('updateColumnWidth', columnToModify);
            },

            handleColumnResizeDragEnd: function(e) {
                var currentCommandModel = this.model.dataset.getCurrentCommandModel();

                $('html').off('.resize');

                // Use the fastRoute to not re-render the entire UI when we update the size of a column
                this.model.state.set('fastRoute', true);
                this.model.dataset.trigger('applyAction', currentCommandModel, this.model.dataset.commands);
            },

            handleCutSelection: function() {
                this.$('.col-header.column-selected').addClass('column-cut');
                this.$('.col-header.column-selected-end').addClass('column-cut-end');
            },

            handleClearCutSelection: function() {
                this.$('.col-header.column-cut, .col-header.column-cut-end').removeClass('column-cut column-cut-end');
            },

            clearSelection: function() {
                this.$lastColumn = null;
                this.$('.col-header.column-selected, .col-header.column-selected-end').removeClass('column-selected column-selected-end');
            },

            // Always happens after render to ensure elements are in the DOM
            setSelection: function() {
                var selectedColumns = this.model.dataset.selectedColumns,
                    selectedColumnInColumnsCollection,
                    selectionType = this.model.dataset.entry.content.get('dataset.display.selectionType'),
                    currentCommandIndex = this.model.dataset.getCurrentCommandIdx(),
                    currentCommand = this.model.dataset.commands.at(currentCommandIndex),
                    $target;

                if (selectionType === 'column' || selectionType === 'cell' || selectionType === 'text') {
                    selectedColumns.each(function(selectedColumn, idx) {
                        selectedColumnInColumnsCollection = currentCommand.columns.get(selectedColumn.id);

                        // It's possible that the selected column doesn't exist in the table anymore
                        if (selectedColumnInColumnsCollection) {
                            $target = this.$getColHeader(selectedColumnInColumnsCollection.get('name'));
                            this.addSelectedColumn($target);
                            this.$lastColumn = $target;

                            $target.attr("draggable", true);

                            // SPL-116067: If it's a cell/text selection, then preview table highlights that column,
                            // because there is no way to select the cell/text reliably. As such,
                            // we must modify the actual selection attributes to reflect the column highlight state.
                            if (selectionType === 'cell' || selectionType === 'text') {
                                this.model.dataset.setSelectionTypeToColumn();
                            }
                        }
                    }, this);
                } else if (selectionType === 'table') {
                    $target = this.$('.col-header');
                    this.handleTableSelect($target);
                    this.$lastColumn = $target.last();
                }
            },

            enableSelection: function(enable) {
                if (enable) {
                    this.$('.col-header').removeClass('disabled');
                    this.$('span.name').after($('<span class="resize"></span>'));
                } else {
                    this.$('.col-header').addClass('disabled');
                    this.$('.resize').remove();
                }
            },

            render: function() {
                TableHeaderView.prototype.render.apply(this, arguments);

                this.$el.html(this.compiledTemplate({
                    ColumnModel: ColumnModel,
                    columns: this.collection.columns
                }));

                this.delegateEvents();
                this.enableSelection(this.model.state.get('tableEnabled'));

                $.when(this.model.state.rowsRenderedDfd).always(function() {
                    if (this.hasFields() && this.options.editingMode) {
                        this.highlightFields();
                        this.setSelection();
                    }
                }.bind(this));

                return this;
            },

            template: '\
                 <div class="dataset-table-head">\
                    <% if (columns.length > 0) { %>\
                        <div class="col-header all">*</div>\
                    <% } else { %>\
                        <div class="col-header placeholder">&nbsp;</div>\
                    <% } %>\
                    <% columns.each(function(column, index) { %>\
                        <div class="col-header field type-<%- column.get("type") %>" data-col-index="<%- index %>" data-field="<%- column.get("name") %>" title="<%- column.get("name") %>" style="<%- column.get("display.width") ? "width: " + column.get("display.width") + "px;" : "" %>">\
                            <i class="icon-<%- ColumnModel.ICONS[column.get("type")] %> field-type" data-type="<%- column.get("type") %>"></i>\
                            <span class="name"><%- column.get("name") %></span>\
                        </div>\
                    <% }, this); %>\
                </div>\
            '
        });
    }
);
