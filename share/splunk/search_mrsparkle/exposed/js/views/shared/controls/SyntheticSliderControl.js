define(
    [
        'jquery',
        'underscore',
        'module',
        'views/shared/controls/Control',
        'util/general_utils',
        'util/keyboard',
        './SyntheticSliderControl.pcss'
    ],
    function($, _, module, Control, util, keyboard, css) {
        /**
         * @constructor
         * @memberOf views
         * @name SyntheticSliderControl
         * @extends {views.Control}
         *
         * @param {Object} options
         * @param {Backbone.Model} options.model The model to operate on
         * @param {String} options.modelAttribute The attribute on the model to observe and update
         * on selection
         * @param {Number} [options.min = 1] The minimum value selectable on the slider
         * @param {Number} [options.max = 5] The maximum value selectable on the slider
         * @param {Number} [options.step = 1] The step interval amount between selectable values on
         * the slider
         * @param {Array} [options.steps] Allows every step of the slider to be explicitly defined.
         * If this option is defined, it will override any previously defined min, max, and step
         * settings.
         *
         * Each array element should be one of the following:
         *
         * - {String/Number} If the element is a string or number, the element will be used
         * as both he slider step's label and value.
         *
         * - {Object of format { label: String, value: String/Number }} If the element is
         * of the above object format, the element's label property will be used
         * as the slider step's label and the element's value property will be used as the
         * slider's value.
         *
         * Example: ['Low', 'Medium', { label: 'High', value: 10000 }]
         * @param {Boolean} [options.enableStepLabels = true] If a steps array (as defined above) is
         * provided, this determines whether or not to display step labels in the UI as the slider
         * is moved.
         * @param {Number} [options.value = options.min] The default value selected on the slider
         * @param {Number} [options.width = 256] The width of the slider bar in pixels
         * @param {Number} [options.minLabel] The text label displayed next to the minimum slider
         * end
         * @param {Number} [options.maxLabel] The text label displayed next to the maximum slider
         * end
         */
        return Control.extend(/** @lends views.SyntheticSliderControl.prototype */{
            className: 'control slider-control',
            moduleId: module.id,
            initialize: function() {
                var defaults = {
                    min: 1,
                    max: 5,
                    step: 1,
                    steps: [],
                    enableStepLabels: true,
                    width: 256
                };
                _.defaults(this.options, defaults);
                this.setSyntheticSteps();
                this.syncFromModel();
                this.setStyles();
                Control.prototype.initialize.call(this, this.options);
            },
            syntheticStepsMode: false,
            value: 0,
            selected: false,
            notches: 0,
            styles: {
                slider: {
                    height: 0
                },
                sliderBar: {
                    width: 0,
                    height: 0,
                    top: 0,
                    borderRadius: 0
                },
                sliderHandle: {
                    width: 0,
                    height: 0,
                    top: 0,
                    left: 0,
                    borderRadius: 0
                },
                sliderNotch: {
                    height: 0
                }
            },
            setSyntheticSteps: function() {
                if (this.options.steps.length) {
                    this.syntheticStepsMode = true;
                    this.options.min = 0;
                    this.options.max = this.options.steps.length - 1;
                    this.options.step = 1;
                    if (this.options.value !== undefined) {
                        this.options.value = this.syntheticToInternalValue(this.options.value);
                    }
                }
            },
            syntheticValueAt: function(index) {
                var syntheticStep = this.options.steps[index];
                return syntheticStep.value || syntheticStep;
            },
            syntheticLabelAt: function(index) {
                var syntheticStep = this.options.steps[index];
                return syntheticStep.label || syntheticStep;
            },
            syntheticToInternalValue: function(syntheticValue) {
                var numSteps = this.options.steps.length;
                for (var i = 0; i < numSteps; i++) {
                    if (this.syntheticValueAt(i) == syntheticValue) {
                        return i;
                    }
                }
                return 0;
            },
            setStyles: function() {
                this.styles.slider.height = this.options.width / 5;
                // Set bar styles
                this.styles.sliderBar.width = this.options.width;
                this.styles.sliderBar.height = this.styles.sliderBar.width / 50;
                this.styles.sliderBar.top = (this.styles.slider.height - this.styles.sliderBar.height) / 2;
                this.styles.sliderBar.borderRadius = this.styles.sliderBar.height / 2;
                // Set handle styles
                this.styles.sliderHandle.width = 18;
                this.styles.sliderHandle.height = 18;
                this.styles.sliderHandle.top = (this.styles.slider.height - this.styles.sliderHandle.height) / 2 - 1;
                this.styles.sliderHandle.borderRadius = this.styles.sliderHandle.width / 2 + 1;
                // Set notch styles
                this.notches = Math.round((this.options.max - this.options.min) / this.options.step);
                this.styles.sliderNotch.height = this.styles.sliderBar.height;
            },
            activate: function() {
                Control.prototype.activate.apply(this, arguments);
                if (this.options.modelAttribute) {
                    this.syncFromModel();
                }
            },
            startListening: function() {
                Control.prototype.startListening.apply(this, arguments);
                if (this.options.modelAttribute) {
                    this.listenTo(this.options.model, 'change:' + this.options.modelAttribute, this.syncFromModel);
                }
            },
            events: {
                'mousedown .slider': function(e) {
                    this.select();
                    this.update(e);
                    $('body').addClass('text-highlight-disabled');

                    $(window).on('mousemove.slider', function(e) {
                        this.update(e);
                        this.$el.find('.slider-handle').focus();
                    }.bind(this));

                    $(window).on('mouseup.slider', function() {
                        this.deselect();
                        $('body').removeClass('text-highlight-disabled');
                        $(window).off('.slider');
                    }.bind(this));
                    this.$el.find('.slider-handle').focus();
                },
                'mousemove .slider': function(e) {
                    this.update(e);
                },
                'keydown .slider-handle': function(e) {
                    if (e.which == keyboard.KEYS.LEFT_ARROW || e.which == keyboard.KEYS.RIGHT_ARROW) {
                        e.preventDefault();
                        this.select();
                        var delta = e.which == keyboard.KEYS.LEFT_ARROW ? -this.options.step : this.options.step;
                        this.value = this.snapToValue(this.value + delta);
                        this.delayedDeselect();
                        this.render();
                        this.$el.find('.slider-handle').focus();
                    }
                }
            },
            delayedDeselect: function() {
                if (!this._delayedDeselect) {
                    this._delayedDeselect = _.debounce(function() {
                        this.deselect();
                    }, 750);
                }
                this._delayedDeselect.apply(this, arguments);
            },
            syncFromModel: function() {
                var modelValue = this.options.model.get(this.options.modelAttribute);
                if (modelValue !== undefined) {
                    var oldValue = this.value;
                    this.value = this.syntheticStepsMode ? this.syntheticToInternalValue(modelValue) : this.snapToValue(parseFloat(modelValue));
                    if (oldValue != this.value) {
                        this.syncToModel();
                    }
                    this.render();
                } else {
                    this.value = this.options.value !== undefined ? this.snapToValue(this.options.value) : this.options.min;
                }
            },
            syncToModel: function() {
                var modelValue = this.options.model.get(this.options.modelAttribute),
                    newModelValue = this.getFormattedValue(this.value);
                if (this.syntheticStepsMode) {
                    if (modelValue === undefined || modelValue != newModelValue) {
                        this.setValue(newModelValue);
                    }
                } else {
                    if (modelValue === undefined || this.snapToValue(parseFloat(modelValue)).toFixed(3) != newModelValue) {
                        this.setValue(newModelValue);
                    }
                }
            },
            getFormattedValue: function(value) {
                var modelValue;
                if (this.syntheticStepsMode) {
                    modelValue = this.syntheticValueAt(value);
                } else {
                    modelValue = value.toFixed(3);
                }
                return modelValue;
            },
            select: function() {
                this.selected = true;
                this.render();
            },
            deselect: function() {
                this.selected = false;
                this.syncToModel();
                this.render();
            },
            snapToValue: function(value) {
                var exactValue = Math.min(Math.max(value, this.options.min), this.options.max);
                return Math.round(exactValue / this.options.step) * this.options.step;
            },
            offsetToValue: function(offset) {
                var position = offset / this.styles.sliderBar.width;
                var trueRange = this.options.max - this.options.min;
                var desiredValue = this.options.min + position * trueRange;
                return this.snapToValue(desiredValue);
            },
            valueToOffset: function(value) {
                var position = this.valueToPosition(value);
                return (position * this.styles.sliderBar.width);
            },
            update: function(e) {
                if (this.selected) {
                    var offset = e.clientX - this.$el.find('.slider-bar').offset().left;
                    var newValue = this.offsetToValue(offset);
                    if (newValue !== this.value) {
                        this.value = newValue;
                        this.render();
                    }
                }
            },
            valueToPosition: function(value) {
                return (value - this.options.min) / (this.options.max - this.options.min);
            },
            render: function() {
                var currentLabel = this.syntheticStepsMode && this.options.enableStepLabels ? this.syntheticLabelAt(this.value) : undefined;
                var position = this.valueToPosition(this.value);
                this.styles.sliderHandle.left = this.valueToOffset(this.value) - 9;
                var modelValue = this.getFormattedValue(this.value);
                
                this.$el.html(_.template(this.template, {
                    currentLabel: currentLabel,
                    width: this.options.width,
                    notches: this.notches,
                    notchWidth: this.options.width / this.notches,
                    styles: this.styles,
                    position: position,
                    selected: this.selected,
                    sliderHandleClass: this.selected ? 'slider-handle-moving' : '',
                    sliderHandleTooltipClass: this.selected && currentLabel ? 'slider-handle-tooltip' : '',
                    minLabel: this.options.minLabel,
                    maxLabel: this.options.maxLabel,
                    ariaLabel: this.options.ariaLabel,
                    ariaValueMin: this.options.min,
                    ariaValueMax: this.options.max,
                    ariaValueNow: this.value,
                    ariaValueText: modelValue
                }));
                return this;
            },
            template: '\
                <div class="slider-container">\
                    <% if (minLabel) { %>\
                        <div class="slider-min-label"><%= minLabel %></div>\
                    <% } %>\
                    <div class="slider" style="width:<%= styles.sliderBar.width %>px;height:<%= styles.slider.height %>px;">\
                        <div class="slider-bar" style="width:<%= styles.sliderBar.width %>px;height:<%= styles.sliderBar.height %>px;top:<%= styles.sliderBar.top %>px;border-radius:<%= styles.sliderBar.borderRadius %>px; background: linear-gradient(to right, #5c6773, #5c6773 <%= position * 100 %>%, #c3cbd4 <%= position * 100 %>%, #c3cbd4)">\
                            <% if (selected) { %>\
                                <% for (var i = 0; i < notches; i++) { %>\
                                    <div class="slider-notch <%= i <= position * notches ? "left-of-handle" : "right-of-handle" %>" style="height:<%= styles.sliderNotch.height %>px;left:<%= i * notchWidth %>px;"></div>\
                                <% } %>\
                            <% } %>\
                        </div>\
                        <button aria-label="<%= ariaLabel %>" aria-valuetext="<%= ariaValueText %>"aria-valuenow="<%= ariaValueNow %>" aria-valuemin="<%= ariaValueMin %>"  aria-valuemax="<%= ariaValueMax %>" role="slider" class="slider-handle <%= sliderHandleTooltipClass %> <%= sliderHandleClass %>" tabindex="0" style="width:<%= styles.sliderHandle.width %>px;height:<%= styles.sliderHandle.height %>px;top:<%= styles.sliderHandle.top %>px;left:<%= styles.sliderHandle.left %>px;border-radius:<%= styles.sliderHandle.borderRadius %>px" data-label="<%- currentLabel %>"></button>\
                    </div>\
                    <% if (maxLabel) { %>\
                        <div class="slider-max-label"><%= maxLabel %></div>\
                    <% } %>\
                </div>\
            '
        });
    }
);
