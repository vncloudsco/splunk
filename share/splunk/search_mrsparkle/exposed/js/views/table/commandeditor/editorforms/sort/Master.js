define(
    [
        'jquery',
        'underscore',
        'module',
        'views/table/commandeditor/editorforms/BaseSortable',
        'views/table/commandeditor/editorforms/sort/FieldRow'
    ],
    function(
        $,
        _,
        module,
        BaseSortableEditorView,
        FieldRowView
    ) {
        return BaseSortableEditorView.extend({
            moduleId: module.id,
            className: BaseSortableEditorView.CLASS_NAME + ' commandeditor-form-sort',

            FieldRowView: FieldRowView,

            DEFAULT_ORDER: 'ascending',

            initialize: function() {
                BaseSortableEditorView.prototype.initialize.apply(this, arguments);
            },

            addNewRow: function(newRequiredGuid) {
                var rowView;

                this.model.command.editorValues.add({
                    order: this.DEFAULT_ORDER,
                    columnGuid: newRequiredGuid
                });

                if (!this.model.command.requiredColumns.get(newRequiredGuid)) {
                    this.model.command.requiredColumns.add({ id: newRequiredGuid });
                }

                rowView = this.createFieldRow(this.model.command.editorValues.last());
                rowView.render().appendTo(this.getSortableContainer());
            },

            render: function() {
                if (!this.$el.html()) {
                    $(BaseSortableEditorView.COMMANDEDITOR_SECTION).appendTo(this.$el);
                    this.$(BaseSortableEditorView.COMMANDEDITOR_SECTION_SELECTOR).html(this.compiledTemplate({
                        _: _
                    }));

                    _.each(this.children, function (rowView) {
                        rowView.render().appendTo(this.getSortableContainer());
                    }, this);

                    this.appendButtons();

                    this.setSortingOnContainer();
                }
                return this;
            },

            template: '\
                <div class="commandeditor-section commandeditor-section-scrolling commandeditor-section-sortable ui-sortable"></div>\
                <div class="commandeditor-section commandeditor-section-padded">\
                    <a class="add-field"><i class="icon-plus"></i> <%-_("Add sort field...").t()%></a>\
                </div>\
            '
        });
    }
);
