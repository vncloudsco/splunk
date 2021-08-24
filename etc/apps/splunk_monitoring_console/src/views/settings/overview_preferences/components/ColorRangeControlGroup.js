define([
    'underscore',
    'module',
    'views/shared/controls/ControlGroup',
    'views/shared/controls/Control',
    'splunk_monitoring_console/views/settings/overview_preferences/components/ColorRangeControlMaster',
    'views/shared/vizcontrols/custom_controls/ColorRangesControlGroup'
], function(
    _,
    module,
    ControlGroup,
    Control,
    ColorRangeControlMaster,
    ColorRangesControlGroup
) {

    return ColorRangesControlGroup.extend({
        moduleId: module.id,
        initialize: function() {
            var colorRangesControl = new ColorRangeControlMaster({
                className: Control.prototype.className,
                model: this.model,
                modelAttribute: this.options.modelAttribute,
                rangeColorsName: this.options.rangeColorsName,
                inputClassName: this.options.inputClassName,
                defaultColors: this.options.defaultColors,
                defaultRangeValues: this.options.defaultRangeValues,
                displayMinMaxLabels: this.options.displayMinMaxLabels,
                paletteColors: this.options.paletteColors,
                rangesGradient: this.options.rangesGradient,
                rangesEditable: this.options.rangesEditable,
                rangesRational: this.options.rangesRational
            });
            
            this.options.label = _('Mappings').t();
            this.options.controlClass = 'controls-block';
            this.options.controls = [ colorRangesControl ];
            ControlGroup.prototype.initialize.call(this, this.options);
        }
    });

});
