define(
    [
        'jquery',
        'underscore',
        'module',
        'models/Base',
        'models/datasets/commands/Base',
        'views/shared/controls/ControlGroup',
        'views/table/commandeditor/editorforms/BaseSortable',
        'views/table/commandeditor/editorforms/concatenate/ConcatenateRow'
    ],
    function(
        $,
        _,
        module,
        BaseModel,
        BaseCommandModel,
        ControlGroup,
        BaseSortableEditorView,
        ConcatenateRowView
    ) {
        return BaseSortableEditorView.extend({
            moduleId: module.id,
            className: BaseSortableEditorView.CLASS_NAME + ' commandeditor-form-concatenate',

            FieldRowView: ConcatenateRowView,

            initialize: function() {
                BaseSortableEditorView.prototype.initialize.apply(this, arguments);

                this.children.fieldName = new ControlGroup({
                    controlType: 'Text',
                    size: 'small',
                    label: _('New field name').t(),

                    controlOptions: {
                        model: this.model.command,
                        modelAttribute: 'newFieldName',
                        updateOnKeyUp: true
                    }
                });
            },

            events: $.extend({}, BaseSortableEditorView.prototype.events, {
                'click .add-string': function(e) {
                    e.preventDefault();

                    var rowView;

                    this.model.command.editorValues.add({ text: '' });
                    rowView = this.createFieldRow(this.model.command.editorValues.last());
                    rowView.render().appendTo(this.getSortableContainer());
                }
            }),

            render: function() {
                if (!this.$el.html()) {
                    $(BaseSortableEditorView.COMMANDEDITOR_SECTION).appendTo(this.$el);
                    this.$(BaseSortableEditorView.COMMANDEDITOR_SECTION_SELECTOR).html(this.compiledTemplate({
                        _: _
                    }));

                    this.children.fieldName.render().appendTo(this.$('.commandeditor-section-field-name'));
                    _.each(this.children, function(rowView) {
                        // Need to ignore the render of fieldName
                        if (rowView.model) {
                            rowView.render().appendTo(this.getSortableContainer());
                        }
                    }, this);

                    this.appendButtons();
                    this.appendAdvancedEditorLink();
                    this.setSortingOnContainer();

                }
                return this;
            },

            template: '\
                <div class="commandeditor-section commandeditor-section-padded commandeditor-section-field-name"></div>\
                <div class="commandeditor-section commandeditor-section-scrolling commandeditor-section-sortable ui-sortable"></div>\
                <div class="commandeditor-section commandeditor-section-padded">\
                    <div>\
                        <a class="add-field">\
                            <i class="icon-plus"></i>\
                            <%- _("Add field...").t()%>\
                        </a>\
                    </div>\
                    <div>\
                        <a class="add-string">\
                            <i class="icon-plus"></i>\
                            <%- _("Add string...").t()%>\
                        </a>\
                    </div>\
                </div>\
            '
        });
    }
);
