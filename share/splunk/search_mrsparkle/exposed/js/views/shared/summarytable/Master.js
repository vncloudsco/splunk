define(
    [
        'underscore',
        'jquery',
        'module',
        'collections/datasets/Columns',
        'views/Base',
        'views/shared/summarytable/TableHeader',
        'views/shared/summarytable/resultsbody/Master',
        'views/shared/delegates/TableDock',
        'views/shared/waitspinner/Master',
        './Master.pcss'
    ],
    function(
        _,
        $,
        module,
        ColumnsCollection,
        BaseView,
        TableHeaderView,
        ResultsBodyView,
        TableDock,
        WaitSpinnerView,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'table-wrapper',

            initialize: function(options) {
                BaseView.prototype.initialize.apply(this, arguments);

                this.collection = this.collection || {};
                this.collection.columns = this.collection.columns || new ColumnsCollection();

                this.children.thead = new TableHeaderView({
                    model: {
                        dataset: this.model.dataset,
                        resultJsonRows: this.model.resultJsonRows,
                        state: this.model.state,
                        summary: this.model.summary,
                        ast: this.model.ast
                    },
                    collection: {
                        columns: this.collection.columns
                    },
                    editingMode: this.options.editingMode
                });

                this.children.resultsBody = new ResultsBodyView({
                    model: {
                        dataset: this.model.dataset,
                        resultJsonRows: this.model.resultJsonRows,
                        summary: this.model.summary,
                        state: this.model.state,
                        timeline: this.model.timeline,
                        dataSummaryJob: this.model.dataSummaryJob
                    },
                    collection: {
                        columns: this.collection.columns
                    },
                    editingMode: this.options.editingMode
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
                this.listenTo(this.model.resultJsonRows, 'sync', this.debouncedRender);
                this.listenTo(this.model.summary, 'sync', this.debouncedRender);
                this.listenTo(this.model.state, 'change:tableEnabled', function() {
                    var enable = this.model.state.get('tableEnabled');
                    this.children.thead.enableSelection(enable);
                    this.children.resultsBody.enableSelection(enable);
                }, this);
            },

            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }

                this.children.waitSpinner.stop();
                this.children.waitSpinner.$el.hide();
                this.$el.removeClass('disabled');

                this.bindDOMListeners();

                this.updateColumnsCollection();

                this.children.tableDock && this.children.tableDock.update();

                return BaseView.prototype.activate.apply(this, arguments);
            },

            // Because binding the listener relies on render having been called already, we must
            // check that this view has HTML in the DOM
            bindDOMListeners: function() {
                if (this.$el.html()) {
                    var scrollTableWrapper = this.$getScrollTableWrapper();
                    if (scrollTableWrapper.length) {
                        scrollTableWrapper.off('scroll').on('scroll', _.bind(this.onScrollChange, this));
                    }
                }
            },

            deactivate: function(options) {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }

                BaseView.prototype.deactivate.apply(this, arguments);

                this.children.waitSpinner.$el.show();
                !this.children.waitSpinner.active && this.children.waitSpinner.start();
                this.$el.addClass('disabled');

                this.$getScrollTableWrapper().off('scroll');

                return this;
            },

            $getScrollTableWrapper: function() {
                return this.$('.scroll-table-wrapper');
            },

            onAddedToDocument: function(options) {
                this.bindDOMListeners();
                this.restoreScrollPosition();

                BaseView.prototype.onAddedToDocument.apply(this, arguments);
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

            updateColumnsCollection: function() {
                var columnsData = [],
                    lastSafeCommand;

                // We only respect the command indices if told to.
                if (this.model.dataset.isTable() && this.options.respectCommandIndex) {
                    lastSafeCommand = this.model.dataset.getLastSafeCommandForCommandIndex();

                    if (lastSafeCommand) {
                        columnsData = lastSafeCommand.columns.toJSON();
                    }
                } else {
                    columnsData = this.model.dataset.getTypedFields({ withoutUnfixed: true });
                }

                // Record whether the columns changed before resetting columns collection, so that
                // the summary table knows to re-render its columns in render().
                this.columnsAreDifferent = !_.isEqual(columnsData, this.collection.columns.toJSON());

                this.collection.columns.reset(columnsData);
            },

            /*
            Summary endpoint only returns events if there are external (non-underscore) fields in the search.
            If there are only internal fields OR it is a lookup dataset (which has no summary) and there are results from the Results endpoint,
            we still want to show the table (albeit without summary events).
            */
            shouldRenderTable: function() {
                return (this.model.summary.getEventCount() > 0 || this.model.resultJsonRows.hasRows());
            },

            render: function() {
                var renderOptions = { columnsAreDifferent: this.columnsAreDifferent },
                    shouldDisableSelection = true,
                    currentCommandModel;

                if (this.shouldRenderTable()) {
                    if (!this.$el.html()) {
                        this.$el.html(this.compiledTemplate({}));
                    }

                    this.children.waitSpinner.render().prependTo(this.$el).$el.hide();

                    this.$el.removeClass('summary-table-no-results');

                    if (!this.$('.summary-table-results').length) {
                        // First render where results are present
                        this.children.thead.render(renderOptions).appendTo(this.$('.table-summary'));
                        this.children.resultsBody.render(renderOptions).appendTo(this.$('.table-summary'));

                        if (this.options.useDock) {
                            if (this.children.tableDock) {
                                this.children.tableDock.remove();
                            }
                            // Must initialize once in render() as TableDock calls activate on its initialize,
                            // which uses the scroll-table-wrapper element (which is only in the DOM when this view is rendered)
                            this.children.tableDock = new TableDock({
                                el: this.el,
                                offset: 37,
                                defaultLayout: 'fixed',
                                tableSelector: '.scroll-table-wrapper > .table-summary',
                                theadSelector: '.shared-summarytable-tableheader',
                                thSelector: '.shared-summarytable-tableheader > .dataset-table-head > .col-header',
                                containerDOM: '<div class="docked-tableheader-container"></div>',
                                containerSelector: '.docked-tableheader-container',
                                scrollContainerSelector: '.scroll-table-wrapper',
                                dockScrollBar: true
                            });
                            this.$el.addClass('shared-summarytable-docking-header');
                        }
                    } else {
                        // Every other render where results are present
                        this.children.thead.render(renderOptions);
                        this.children.resultsBody.render(renderOptions);

                        // Must update coverage bars' appearance every time new results come in, as the CSS is not copied over on tabledock's update
                        if (this.children.tableDock) {
                            this.collection.columns.each(function(column) {
                                var colName = column.get("name");
                                var metrics = this.model.resultJsonRows.extractMetrics(column, this.model.summary.extractTopResults(colName));
                                var $column = this.children.tableDock.$('.col-header[data-field="' + colName + '"]');

                                this.children.thead.toggleBarVisibility($column, metrics, 'MatchedType', 'match');
                                this.children.thead.toggleBarVisibility($column, metrics, 'MismatchedType', 'mismatch');
                                this.children.thead.toggleBarVisibility($column, metrics, 'NullOrEmptyValues', 'null-or-empty');
                                this.children.thead.toggleBarVisibility($column, metrics, undefined, 'loading');
                            }, this);
                        }
                    }
                    // Reset flag
                    this.columnsAreDifferent = false;

                    this.bindDOMListeners();
                    this.restoreScrollPosition();

                    // Reset selection and highlight manually because template does not get fully cleared out every render.
                    this.children.thead.clearSelection();
                    this.children.resultsBody.clearSelection();
                    this.children.thead.clearHighlight();

                    if (this.model.dataset.isTable() && this.options.editingMode) {
                        currentCommandModel = this.model.dataset.getCurrentCommandModel();
                        shouldDisableSelection = !currentCommandModel.isComplete() || !currentCommandModel.isValid();

                        this.children.thead.setSelection();
                        this.children.thead.highlightFields();
                    }

                    this.children.thead.enableSelection(!shouldDisableSelection);
                    this.children.resultsBody.enableSelection(!shouldDisableSelection);

                    // Disable drag and drop until job is done, so that table does not get into a weird state.
                    if (!this.model.dataSummaryJob.isDone()) {
                        this.children.thead.clearDragability();
                    }
                } else {
                    this.$el.html(this.compiledTemplate({}));
                    this.$el.addClass('summary-table-no-results');
                }

                // Data summary is pretty good about not rendering itself repeatedly if it doesn't need to.
                // That means that cut selections can linger for longer than they should. Remove here.
                this.model.state.trigger('clearCutSelection');

                return this;
            },

            template: '\
                <div class="scroll-table-wrapper">\
                    <div class="table table-summary">\
                    </div>\
                </div>\
            '
        });
    }
);
