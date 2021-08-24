define([
        'jquery',
        'underscore',
        'module',
        'backbone',
        'views/shared/controls/Control',
        'views/shared/controls/colors/ColorRangeLabelControl',
        'bootstrap.tooltip'
    ],
    function(
        $,
        _,
        module,
        Backbone,
        Control,
        LabelControl,
        undefined
        ) {

        return LabelControl.extend({

            render: function() {
                this.$('.text-value').tooltip('destroy');
                this.$el.html(this.compiledTemplate({
                    value: parseInt(this.model.get('value'), 10) + 1,
                    label: this.options.label,
                    customClass: this.options.customClass || 'color-control-left-col'
                }));
                this.$('.text-value').tooltip({ animation: false, container: 'body' });
                return this;
            }
        });

    });