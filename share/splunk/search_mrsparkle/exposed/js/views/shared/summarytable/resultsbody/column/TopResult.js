define(
    [
        'underscore',
        'jquery',
        'module',
        'models/datasets/commands/Base',
        'views/shared/datasettable/shared/TableCell'
    ],
    function(
        _,
        $,
        module,
        CommandModel,
        BaseTableCell
    ) {
        return BaseTableCell.extend({
            moduleId: module.id,
            className: 'top-results-cell',

            attributes: function() {
                return {
                    'data-field': this.model.cell.getValue(),
                    'data-col-index': this.model.cell.get('colIndex')
                };
            },

            initialize: function() {
                BaseTableCell.prototype.initialize.apply(this, arguments);
            },

            startListening: function() {
                this.listenTo(this.model.state, 'setValueSelection', this.setSelection);
                this.listenTo(this.model.state, 'cutSelection', this.handleCutSelection);
                this.listenTo(this.model.state, 'clearCutSelection', this.handleClearCutSelection);
            },

            setSelection: function(args) {
                var columnName = args.columnName,
                    selectedValue = args.selectedValue,
                    currentColumnIsSelected = this.model.column.get('name') === columnName,
                    currentCellIsSelected = selectedValue === this.model.cell.getValue();

                if (currentColumnIsSelected) {
                    if (currentCellIsSelected) {
                        // Is cell selection
                        this.$el.addClass('selected');
                    }
                }
            },

            enableSelection: function(enable) {
                if (enable) {
                    this.$el.removeClass('disabled');
                } else {
                    this.$el.addClass('disabled');
                }
            },

            handleCutSelection: function() {
                if (this.$el.hasClass('column-selected')) {
                    this.$el.addClass('column-cut');
                }
            },

            handleClearCutSelection: function() {
                this.$el.removeClass('column-cut');
            },

            // Do not allow text selection in Data Summary Mode
            isTextSelectable: function() {
                return false;
            },

            render: function() {
                var value = this.model.cell.getValue(),
                    percentage = this.model.cell.getScaledPercentage(),
                    width = Math.round(percentage) || 1,
                    isNull = this.model.cell.isNull(),
                    isEmpty = this.model.cell.isEmpty(),
                    shouldDisableSelection = true,
                    currentCommandModel;

                if (this.model.dataset.isTable() && this.options.editingMode) {
                    currentCommandModel = this.model.dataset.getCurrentCommandModel();
                    shouldDisableSelection = !currentCommandModel.isComplete() || !currentCommandModel.isValid();
                }

                this.$el.html(this.compiledTemplate({
                    _: _,
                    value: value,
                    percentage: percentage,
                    width: width,
                    isNull: isNull
                }));

                if (isNull) {
                    this.$('.result-bar').addClass('null');
                } else if (isEmpty) {
                    this.$('.result-bar').addClass('empty');
                } else if (this.model.cell.getTypeMismatchMessage()) {
                    this.$('.result-bar').addClass('mismatched');
                } else {
                    this.$('.result-bar').addClass('matched');
                }

                return this;
            },

            template: '' +
                '<span class="result-bar" style="width:<%- width %>%"></span>' +
                '<div class="result-field selection-container <%- isNull && "null-cell"%>">' +
                    '<div class="real-text-wrapper">' +
                        '<% if (isNull) { %>' +
                            'null' +
                        '<% } else { %>' +
                            '<span class="real-text">' +
                                '<%- value %>' +
                            '</span>' +
                        '<% } %>' +
                    '</div>' +
                '</div>' +
                '<span class="result-value"><%- percentage %>%</span>'
        });
    }
);


