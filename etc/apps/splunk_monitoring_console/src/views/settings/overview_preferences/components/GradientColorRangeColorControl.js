define([
    'jquery',
    'underscore',
    'module',
    'backbone',
    'views/shared/controls/colors/ColorRangeColorControl',
    'splunk_monitoring_console/views/settings/overview_preferences/components/GradientColorRangeColorPicker',
    'util/color_utils'
],
function(
    $,
    _,
    module,
    Backbone,
    ColorRangeColorControl,
    GradientColorRangeColorPicker,
    colorUtils
    ) {

    return ColorRangeColorControl.extend({
        className: 'gradient-color-range-input-control',
        moduleId: module.id,
        
        _createColorPicker: function() {
            return new GradientColorRangeColorPicker({
                ignoreClasses: ["color-picker-container"],
                model: this.model,
                onHiddenRemove: true,
                paletteColors: this.options.paletteColors,
                rangeColors: this.options.rangeColors
            });
        }
        
    });

});