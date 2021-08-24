define([
        'jquery',
        'underscore',
        'module',
        'backbone',
        'views/shared/controls/Control',
        'bootstrap.tooltip'
    ],
    function(
        $,
        _,
        module,
        Backbone,
        Control,
        bootstrapTooltip
        ) {

        return Control.extend({
            className: 'color-range-label-control',
            moduleId: module.id,

            initialize: function() {
                Control.prototype.initialize.apply(this, arguments);
            },

            render: function() {
                this.$('.color-range-label-control-value').tooltip('destroy');
                this.$el.html(this.compiledTemplate({
                    value: this.options.value || this.model.get('value'),
                    label: this.options.label,
                    customClass: this.options.customClass || 'color-control-left-col'
                }));
                this.$('.color-range-label-control-value').tooltip({ animation: false, container: 'body' });
                return this;
            },

            remove: function() {
                this.$('.color-range-label-control-value').tooltip('destroy');
                return Control.prototype.remove.apply(this, arguments);
            },

            template: '\
                    <label class="color-range-label-control-label">\
                        <%- label %>\
                    </label>\
                    <span class="color-range-label-control-value"><%- value %></span>\
            '
        });

    });
