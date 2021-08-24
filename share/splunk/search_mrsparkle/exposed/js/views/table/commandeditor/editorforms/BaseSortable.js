define(
    [
        'jquery',
        'underscore',
        'module',
        'views/table/commandeditor/editorforms/Base',
        'views/table/commandeditor/listpicker/Overlay',
        'jquery.ui.sortable'
    ],
    function(
        $,
        _,
        module,
        BaseEditorView,
        ListPickerOverlay,
        undefined
    ) {
        var CLASS_NAME = BaseEditorView.CLASS_NAME + ' commandeditor-form-sortable';

        return BaseEditorView.extend({
            moduleId: module.id,
            className: CLASS_NAME,

            initialize: function() {
                BaseEditorView.prototype.initialize.apply(this, arguments);

                this.model.command.editorValues.each(function(editorValue) {
                    this.createFieldRow(editorValue);
                }, this);
            },

            events: $.extend({}, BaseEditorView.prototype.events, {
                'click .add-field': function(e) {
                    e.preventDefault();
                    this.openFieldsPicker();
                }
            }),

            updateFieldOrder: function(e, ui) {
                var idArray = this.getSortableContainer().sortable('toArray', { attribute: 'order-id' }),
                    orderId = ui.item.length && ui.item[0].getAttribute('order-id'),
                    newIndex = idArray.indexOf(orderId),
                    modelToMove = this.model.command.editorValues.find(function(editorValue) {
                        return editorValue.get('orderId') === orderId;
                    }, this);
                this.model.command.editorValues.remove(modelToMove);
                this.model.command.editorValues.add(modelToMove, { at: newIndex });
            },

            createFieldRow: function(editorValue) {
                var editorValueId = this.model.command.getUniqueEditorValueId(),
                    rowView;

                editorValue.set('orderId', editorValueId);

                rowView = this.children[editorValue.get('orderId')] = new this.FieldRowView({
                    model: editorValue,
                    fieldPickerItems: this.getFieldPickerItems()
                });

                this.listenTo(rowView, 'removeRow', function(options) {
                    this.removeRow(options.orderId);
                });
                return rowView;
            },

            addNewRow: function(newRequiredGuid) {
                var rowView;

                this.model.command.editorValues.add({ columnGuid: newRequiredGuid });

                if (!this.model.command.requiredColumns.get(newRequiredGuid)) {
                    this.model.command.requiredColumns.add({ id: newRequiredGuid });
                }
                rowView = this.createFieldRow(this.model.command.editorValues.last());
                rowView.render().appendTo(this.getSortableContainer());
            },

            removeRow: function(orderId) {
                var modelToRemove = this.model.command.editorValues.find(function(editorValue) {
                    return editorValue.get('orderId') === orderId;
                }, this);

                // If this is the last row that uses a particular columnGuid, then it gets removed from requiredColumns
                if (this.model.command.editorValues.where({ columnGuid: modelToRemove.get('columnGuid') }).length === 1) {
                    this.model.command.requiredColumns.remove({ id: modelToRemove.get('columnGuid') });
                }

                this.model.command.editorValues.remove(modelToRemove);
                this.children[orderId].remove();
                delete this.children[orderId];
            },

            openFieldsPicker: function() {
                var requiredValues = this.model.command.requiredColumns.pluck('id');

                if (this.children.fieldsPickerOverlay) {
                    this.children.fieldsPickerOverlay.deactivate({deep: true}).remove();
                }

                this.children.fieldsPickerOverlay = new ListPickerOverlay({
                    items: this.getFieldPickerItems(),
                    selectedValues: requiredValues,
                    selectMessage: _('Select a field...').t(),
                    multiselect: false,
                    required: true
                });

                this.children.fieldsPickerOverlay.render().appendTo(this.$el);
                this.children.fieldsPickerOverlay.slideIn();

                this.listenTo(this.children.fieldsPickerOverlay, 'selectionDidChange', function() {
                    var requiredValues = this.model.command.requiredColumns.pluck('id'),
                        newRequiredGuid = _.difference(this.children.fieldsPickerOverlay.getSelectedValues(), requiredValues)[0];

                    this.addNewRow(newRequiredGuid);
                });
            },

            getSortableContainer: function() {
                return this.$('.commandeditor-section-sortable');
            },

            setSortingOnContainer: function() {
                this.getSortableContainer().sortable(
                    {
                        axis: "y",
                        stop: _.bind(function(e, ui) {
                            this.updateFieldOrder(e, ui);
                        }, this)
                    }
                );
            },
            handleApply: function(options) {
                // Always make sure requiredColumns is in sync with updated editorValues
                this.model.command.resetRequiredColumns(this.model.command.editorValues.pluck('columnGuid'));
                this.addNewField();
                BaseEditorView.prototype.handleApply.apply(this, arguments);
            }
        }, {
            CLASS_NAME: CLASS_NAME
        });
    }
);
