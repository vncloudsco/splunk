define(
    [
        'underscore',
        'jquery',
        'module',
        'views/Base',
        'views/shared/datasettable/resultsbody/Cell'
    ],
    function(
        _,
        $,
        module,
        BaseView,
        CellView
    ) {
        return BaseView.extend({
            moduleId: module.id,
            tagName: 'tr',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },

            cellsFromCollection: function() {
                return this.collection.cells.map(function(cellModel, idx) {
                    return new CellView({
                        model: {
                            dataset: this.model.dataset,
                            cell: cellModel,
                            state: this.model.state,
                            column: this.collection.columns.at(idx),
                            config: this.model.config
                        },
                        rowIdx: this.options.idx,
                        editingMode: this.options.editingMode
                    });
                }, this);
            },

            enableSelection: function(enable) {
                _(this.children.cells).each(function(cell) {
                    cell.enableSelection(enable);
                }, this);
            },

            render: function() {
                var rowNum = this.options.idx;
                
                if (_.isNumber(this.options.init_offset)) {
                    rowNum = this.options.init_offset + rowNum;
                }
                
                this.$el.html(this.compiledTemplate({
                    rowNum: rowNum
                }));

                this.children.cells = this.cellsFromCollection();
                _(this.children.cells).each(function(cell) {
                    cell.render().appendTo(this.$el);
                }, this);

                return this;
            },

            template: '' +
                '<td class="row-num">' +
                    '<%- rowNum %>' +
                '</td>'
        });
    }
);


