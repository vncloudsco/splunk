define(
    [
        'underscore',
        'jquery',
        'module',
        'collections/datasets/Columns',
        'models/datasets/Column',
        'views/Base',
        'views/shared/datasettable/TableHeader',
        'views/shared/datasettable/resultsbody/Master',
        'views/shared/delegates/TableDock',
        'views/shared/waitspinner/Master',
        'util/dataset_utils',
        './Master.pcss'
    ],
    function(
        _,
        $,
        module,
        ColumnsCollection,
        ColumnModel,
        BaseView,
        TableHeadView,
        ResultsBodyView,
        TableDock,
        WaitSpinnerView,
        datasetUtils,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'table-wrapper',

            initialize: function(options) {
                BaseView.prototype.initialize.apply(this, arguments);
                this.tableId = this.cid + '-table';

                this.collection = this.collection || {};
                this.collection.columns = new ColumnsCollection();

                this.children.resultsBody = new ResultsBodyView({
                    model: {
                        dataset: this.model.dataset,
                        resultJsonRows: this.model.resultJsonRows,
                        state: this.model.state,
                        config: this.model.config
                    },
                    collection: {
                        columns: this.collection.columns
                    },
                    editingMode: this.options.editingMode
                });

                this.children.thead = new TableHeadView({
                    model: {
                        dataset: this.model.dataset,
                        resultJsonRows: this.model.resultJsonRows,
                        state: this.model.state,
                        ast: this.model.ast
                    },
                    collection: {
                        columns: this.collection.columns
                    },
                    editingMode: this.options.editingMode,
                    resultsTable: this.children.resultsBody
                });

                this.children.waitSpinner = new WaitSpinnerView({
                    color: 'green',
                    size: 'medium',
                    frameWidth: 19
                });
            },

            startListening: function(options) {
                this.listenTo(this.model.state, 'clearSelection', function() {
                    this.model.dataset.clearSelections();
                });
                this.listenTo(this.model.state, 'setSelectedColumn', function(colIndex) {
                    this.model.dataset.setSelectedColumn(colIndex);
                });
                this.listenTo(this.model.resultJsonRows, 'change:fields', this.updateColumnsCollection);
                this.listenTo(this.model.resultJsonRows, 'change', this.render);
                this.listenTo(this.model.state, 'restoreScrollPosition', this.restoreScrollPosition);

                this.listenTo(this.model.state, 'change:tableEnabled', function() {
                    var enable = this.model.state.get('tableEnabled');
                    this.children.thead.enableSelection(enable);
                    this.children.resultsBody.enableSelection(enable);
                }, this);

                this.listenTo(this.model.state, 'disableTableEditing', function() {
                    this.disableTable();
                });

                this.listenTo(this.model.state, 'enableTableEditing', function() {
                    this.enableTable();
                });
            },

            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }

                this.bindDOMListeners();

                this.updateColumnsCollection();

                BaseView.prototype.activate.apply(this, arguments);

                this.enableTable();

                return this;
            },

            deactivate: function(options) {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }
                BaseView.prototype.deactivate.apply(this, arguments);

                this.disableTable();

                this.$getScrollTableWrapper().off('scroll');

                return this;
            },

            enableTable: function() {
                var shouldEnableSelection = false,
                    currentCommandModel;

                if (this.$el.hasClass('disabled')) {
                    this.children.waitSpinner.stop();
                    this.children.waitSpinner.$el.hide();
                    this.$el.removeClass('disabled');
                }

                if (this.model.dataset.isTable() && this.options.editingMode) {
                    currentCommandModel = this.model.dataset.getCurrentCommandModel();
                    shouldEnableSelection = currentCommandModel.isComplete() && currentCommandModel.isValid();
                }

                this.model.state.set('tableEnabled', shouldEnableSelection);
            },

            disableTable: function() {
                if (!this.$el.hasClass('disabled')) {
                    this.children.waitSpinner.$el.show();
                    !this.children.waitSpinner.active && this.children.waitSpinner.start();
                    this.$el.addClass('disabled');
                }

                this.model.state.set('tableEnabled', false);
            },

            $getScrollTableWrapper: function() {
                return this.$('.scroll-table-wrapper');
            },

            onAddedToDocument: function(options) {
                this.restoreScrollPosition();

                return BaseView.prototype.onAddedToDocument.apply(this, arguments);
            },

            handleContainerScroll: function() {
                this.saveScrollPosition();
                this.model.state.trigger('destroyContextualMenus');
            },

            restoreScrollPosition: function() {
                var scrollLeft = this.model.dataset.entry.content.get('dataset.display.scrollLeft');

                scrollLeft && this.$getScrollTableWrapper().scrollLeft(scrollLeft);
                // We need to make sure the table was scrolled, so only use what the actual table scroll is
                scrollLeft = this.$getScrollTableWrapper().scrollLeft();
                this.setScrollPositionOnTableHeader(scrollLeft);
            },

            onScrollChange: function() {
                var scrollLeft = this.$getScrollTableWrapper().scrollLeft();
                this.model.dataset.entry.content.set('dataset.display.scrollLeft', scrollLeft);
                this.setScrollPositionOnTableHeader(scrollLeft);
                this.model.state.trigger('destroyContextualMenus');

                this.children.tableDock && this.children.tableDock.handleContainerScroll();
            },

            setScrollPositionOnTableHeader: function(scrollLeft) {
                scrollLeft = scrollLeft || 0;
                this.$('.dataset-table-head').css('margin-left', -scrollLeft + 'px');
            },

            saveScrollPosition: function() {
                var scrollLeft = this.$('.scroll-table-wrapper').scrollLeft();

                if (scrollLeft !== null) {
                    this.model.dataset.entry.content.set('dataset.display.scrollLeft', scrollLeft);
                }
            },

            bindDOMListeners: function() {
                if (this.$el.html()) {
                    var $scrollTableWrapper = this.$getScrollTableWrapper();
                    if ($scrollTableWrapper.length) {
                        $scrollTableWrapper.off('scroll').on('scroll', _.bind(this.onScrollChange, this));
                    }
                }
            },

            updateColumnsCollection: function() {
                var columnsData = [],
                    lastSafeCommand,
                    fields = this.model.resultJsonRows.get('fields') || [];

                // We only respect the command indices if told to.
                if (this.model.dataset.isTable() && this.options.respectCommandIndex) {
                    lastSafeCommand = this.model.dataset.getLastSafeCommandForCommandIndex();

                    if (lastSafeCommand) {
                        columnsData = lastSafeCommand.columns.toJSON();
                    }
                } else {
                    columnsData = this.model.dataset.getTypedFields({ withoutUnfixed: true });
                }

                if (!columnsData.length) {
                    // TODO: Lookup Table Files (e.g.| from inputlookup:"geo_attr_countries.csv") currently do not get fields
                    // back from their EAI endpoint, so we need to look at resultJsonRows to get field information.
                    _(fields).each(function(field) {
                        columnsData.push({
                            name: field
                        });
                    }, this);
                }

                // Initial data uses this flag to auto type columns
                if (this.options.autoTypeColumns) {
                    this.guessColumnTypes(columnsData, lastSafeCommand);
                }
                this.collection.columns.reset(columnsData);
            },

            guessColumnTypes: function(columnsData, command) {
                var rows = this.model.resultJsonRows.get('rows') || [],
                    fields = this.model.resultJsonRows.get('fields') || [],
                    matchedTypeCountObj,
                    i,
                    j,
                    value,
                    columnObj,
                    threshold;

                for (i = 0; i < fields.length; i++) {
                    matchedTypeCountObj = {
                        ip: 0,
                        bool: 0,
                        number: 0
                    };
                    columnObj = _.find(columnsData, function(columnObj) {
                        return columnObj.name === fields[i];
                    }.bind(this));

                    if (columnObj && (columnObj.type === ColumnModel.TYPES.STRING)) {
                        for (j = 0; j < rows.length; j++) {
                            value = rows[j][i];
                            threshold = rows.length / 2;

                            if (datasetUtils.isIPV4(value)) {
                                matchedTypeCountObj.ip++;

                                if (matchedTypeCountObj.ip > threshold) {
                                    columnObj.type = ColumnModel.TYPES.IPV4;
                                    break;
                                }
                            } else if (datasetUtils.isBoolean(value)) {
                                matchedTypeCountObj.bool++;

                                if (matchedTypeCountObj.bool > threshold) {
                                    columnObj.type = ColumnModel.TYPES.BOOLEAN;
                                    break;
                                }
                            } else if (datasetUtils.isNumber(value)) {
                                matchedTypeCountObj.number++;

                                if (matchedTypeCountObj.number > threshold) {
                                    columnObj.type = ColumnModel.TYPES.NUMBER;
                                    break;
                                }
                            }
                        }
                    }
                }

                // Save the type information to the actual table
                if (command) {
                    command.columns.reset(columnsData);
                }
            },

            render: function() {
                var resultRows = this.model.resultJsonRows.get('rows');

                this.$el.html(this.compiledTemplate({
                    tableId: this.tableId
                }));

                this.children.waitSpinner.render().prependTo(this.$el).$el.hide();

                if (resultRows && resultRows.length) {
                    this.children.thead.render().prependTo(this.$('.table-preview'));
                    this.children.resultsBody.render().appendTo(this.$('.table-results'));

                    this.updateColumnsCollection();

                    this.bindDOMListeners();
                    this.restoreScrollPosition();

                    if (this.options.useDock) {
                        if (this.children.tableDock) {
                            this.children.tableDock.remove();
                        }
                        this.children.tableDock = new TableDock({
                            el: this.el,
                            offset: 37,
                            defaultLayout: 'fixed',
                            tableSelector: '.scroll-table-wrapper > .table-preview',
                            theadSelector: '.shared-datasettable-tableheader',
                            thSelector: '.shared-datasettable-tableheader > .dataset-table-head > .col-header',
                            containerDOM: '<div class="docked-tableheader-container"></div>',
                            containerSelector: '.docked-tableheader-container',
                            scrollContainerSelector: '.scroll-table-wrapper',
                            dockScrollBar: true
                        });
                        this.$el.addClass('shared-datasettable-docking-header');
                    }
                }

                if (!this.options.editingMode) {
                    this.children.thead.enableSelection(false);
                    this.children.resultsBody.enableSelection(false);
                }

                return this;
            },

            template: '\
                <div class="scroll-table-wrapper">\
                    <div class="table table-preview">\
                        <table class="table table-results" id="<%= tableId %>"></table>\
                    </div>\
                </div>\
            '
        });
    }
);
