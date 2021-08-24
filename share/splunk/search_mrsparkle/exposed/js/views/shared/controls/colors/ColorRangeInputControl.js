define([
        'jquery',
        'underscore',
        'module',
        'backbone',
        'views/shared/controls/Control'
    ],
    function(
        $,
        _,
        module,
        Backbone,
        Control
        ) {

        return Control.extend({
            className: 'color-range-input-control',
            moduleId: module.id,

            initialize: function() {
                Control.prototype.initialize.apply(this, arguments);
            },

            events: {
                'keyup .color-range-label-control-value': function(e) {
                    e.preventDefault();
                    if (!this._handleInputChange) {
                        this._handleInputChange = _.debounce(function(e) {
                            var $target = $(e.currentTarget),
                                value = $.trim($target.val());
                            if (!isNaN(value) && value !== "") {
                                value = parseFloat(value);
                            }
                            this.model.set('value', value);
                        },300);
                    }
                    this._handleInputChange.apply(this, arguments);
                }
            },

            render: function() {
                if (!this.$el.html()) {
                    this.$el.html(this.compiledTemplate({
                        label: this.options.label
                    }));
                }
                this.$('.color-range-label-control-value').val(this.model.get('value'));
                return this;
            },

            template: '\
                <label class="color-range-label-control-label">\
                    <%- label %>\
                </label>\
                <input class="color-range-label-control-value" type="text">\
            '
        });

    });
