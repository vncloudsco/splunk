define([
        'jquery',
        'underscore',
        'module',
        'backbone',
        'views/shared/controls/Control',
        'views/shared/controls/colors/ColorRangeLabelControl',
        'views/shared/controls/colors/ColorRangeInputControl',
        'views/shared/controls/colors/ColorRangeColorControl',
        'models/Base'
    ],
    function(
        $,
        _,
        module,
        Backbone,
        Control,
        LabelControl,
        InputControl,
        ColorControl,
        BaseModel
        ) {

        return Control.extend({
            moduleId: module.id,
            className: 'color-range-control-row',

            initialize: function() {
                Control.prototype.initialize.apply(this, arguments);
                this.model.to = this.model;
                this.model.from = this.options.fromModel;
                this.displayMinMaxLabels = this.options.displayMinMaxLabels;
                this.initRowComponents();
            },

            events: {
                'click .remove-range': function(e) {
                    this.trigger('removeRange', this.model);
                }
            },

            initRowComponents: function() {
                var i = this.collection.indexOf(this.model.to);
                if (this.model.to.get('value') === 'max') {
                    // Set row's right control to label 'max'
                    this.createLabelControl(this.model.from, 'min', 'from');
                    this.createLabelControl(this.model.to, 'max', 'to');
                    this.createColorControl(this.model.to);
                } else {
                    if (i === 0) {
                        // Set row's left control to label 'min'
                        this.createLabelControl(this.model.from, 'min', 'from');
                        this.createInputControl(this.model.to, 'max', 'to');
                    } else if (i === 1 && !this.displayMinMaxLabels) {
                        // Left control should be an input instead of a label
                        this.createInputControl(this.model.from, 'min', 'from');
                        this.createInputControl(this.model.to, 'max', 'to');
                    } else {
                        // Most range values get both label and input controls.
                        // Use previous range value to power label.
                        this.createLabelControl(this.model.from, 'min', 'from');
                        this.createInputControl(this.model.to, 'max', 'to', '');
                    }
                    this.createColorControl(this.model.to);
                }
            },

            createInputControl: function(model, id, label, customClass) {
                var inputView = this.children[id + 'View'] = new InputControl({
                    model: model,
                    label: _(label).t(),
                    customClass: customClass
                });
            },

            createLabelControl: function(model, id, label, customClass) {
                this.children[id + 'View'] = new LabelControl({
                    model: model,
                    label: _(label).t(),
                    customClass: customClass
                });
            },

            createColorControl: function(model) {
                if (model.get('color') && model.get('color').length > 0) {
                    this.children.colorView = new ColorControl({
                        model: model,
                        paletteColors: this.options.paletteColors,
                        className: 'color-range-color-control'
                    });
                }
            },

            render: function() {
                if (!this.el.innerHTML) {
                    this.el.innerHTML = this.compiledTemplate({
                        hideRemoveButton: this.options.hideRemoveButton
                    });

                    this.children.colorView.render().prependTo(this.$el);
                    this.children.maxView.render().prependTo(this.$el);
                    // minView requires an extra check, because the implementation of initRowCompoents in
                    // splunk monitoring console overview preferences' ColorRangeControlRow has a scenario where only 
                    // colorView and maxView are created; whereas in other cases, all 3 views are created. 
                    if (!_.isUndefined(this.children.minView)) {
                        this.children.minView.render().prependTo(this.$el);
                    }
                } else {
                    _(this.children).invoke('render');
                }
                return this;
            },
            template: '\
                <% if (!hideRemoveButton) { %>\
                    <a class="remove-range btn-pill btn-square" href="#">\
                        <i class="icon-x"></i>\
                    </a>\
                <% } %>\
            '

    });

    });
