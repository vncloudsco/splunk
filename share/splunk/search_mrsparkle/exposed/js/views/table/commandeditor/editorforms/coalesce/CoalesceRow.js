define(
    [
        'underscore',
        'module',
        'views/Base',
        'views/shared/controls/TextControl',
        'views/table/commandeditor/listpicker/Control'
    ],
    function(
        _,
        module,
        BaseView,
        TextControl,
        ListPickerControl
        ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'commandeditor-group-sortable',
            attributes: function() {
                return {
                    'order-id': this.model.get('orderId')
                };
            },

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.fieldPicker = new ListPickerControl({
                    listOptions: {
                        items: this.options.fieldPickerItems,
                        selectedValues: [this.model.get('columnGuid')],
                        size: 'small',
                        multiselect: false,
                        selectMessage: _('Select a field...').t(),
                        required: true
                    },
                    model: this.model,
                    modelAttribute: 'columnGuid',
                    placeholder: _('Select a field...').t(),
                    toggleClassName: '',
                    className: ListPickerControl.prototype.className + ' commandeditor-group-label',
                    size: 'small'
                });

            },

            events: {
                'click .commandeditor-group-remove': function(e) {
                    e.preventDefault();
                    this.trigger('removeRow', { orderId: this.model.get('orderId') });
                }
            },

            render: function() {
                this.$el.html(this.compiledTemplate());

                this.children.fieldPicker.render().appendTo(this.$el);

                return this;
            },

            template: '\
                <a class="commandeditor-group-remove"><i class="icon-x"></i></a>\
            '
        });
    }
);
