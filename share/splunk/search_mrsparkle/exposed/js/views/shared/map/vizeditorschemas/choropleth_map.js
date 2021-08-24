define([
            'underscore',
            'views/shared/controls/TextControl',
            'views/shared/controls/SyntheticRadioControl',
            'views/shared/controls/PercentTextControl',
            'views/shared/controls/SyntheticSelectControl',
            'views/shared/controls/BooleanRadioControl',
            'views/shared/controls/ColorPickerControl',
            'views/shared/vizcontrols/custom_controls/ChoroplethColorPreview',
            'views/shared/vizcontrols/custom_controls/ChoroplethColorModeControl',
            'util/validation',
            'splunk/palettes/ColorCodes',
            './shared_elements'
        ],
        function(
            _,
            TextControl,
            SyntheticRadioControl,
            PercentTextControl,
            SyntheticSelectControl,
            BooleanRadioControl,
            ColorPickerControl,
            ChoroplethColorPreview,
            ChoroplethColorModeControl,
            validationUtils,
            ColorCodes,
            SharedMapElements
        ) {

    var CHOROPLETH_COLOR_OPTIONS = _.flatten([
        ColorCodes.SEMANTIC, ColorCodes.DIVERGENT_PAIRS, '#FFFFFF', ColorCodes.DARK_GREY
    ]);

    var validateColor = function(value) {
        if (!value || value.indexOf('0x') !== 0 || _.isNaN(parseInt(value, 16))) {
            return 'invalid';
        }
    };

    var getComputedColorMode = function(reportModel) {
        var defaultColorMode = 'sequential';
        var userSpecifiedColorMode = reportModel.get('display.visualizations.mapping.choroplethLayer.colorMode') || defaultColorMode;
        return userSpecifiedColorMode === 'auto' ? (reportModel.get('autoDetectedColorMode') || defaultColorMode) : userSpecifiedColorMode;
    };

    return ([
        {
            id: 'general',
            title: _('General').t(),
            formElements: [
                SharedMapElements.SCROLL_ZOOM,
                {
                    name: 'display.visualizations.mapping.legend.placement',
                    label: _('Show Legend').t(),
                    defaultValue: 'bottomright',
                    control: SyntheticRadioControl,
                    controlOptions: {
                        items: [
                            {
                                label: _('Yes').t(),
                                value: 'bottomright'
                            },
                            {
                                label: _('No').t(),
                                value: 'none'
                            }
                        ]
                    }
                },
                '<div class="divider"></div>',
                SharedMapElements.CENTER_LAT,
                SharedMapElements.CENTER_LON,
                SharedMapElements.ZOOM,
                SharedMapElements.POPULATE_CENTER_ZOOM
            ]
        },
        {
            id: 'colors',
            title: _('Colors').t(),
            formElements: [
                {
                    name: 'choropleth-color-preview',
                    group: ChoroplethColorPreview
                },
                {
                    name: 'display.visualizations.mapping.choroplethLayer.colorMode',
                    label: _('Color Mode').t(),
                    defaultValue: 'auto',
                    control: ChoroplethColorModeControl,
                    controlOptions: {
                        toggleClassName: 'btn'
                    },
                    validation: {
                        oneOf: ['auto', 'sequential', 'divergent', 'categorical'],
                        required: true
                    }
                },
                {
                    name: 'display.visualizations.mapping.choroplethLayer.maximumColor',
                    label: _('Maximum Color').t(),
                    defaultValue: '0xAF575A',
                    control: ColorPickerControl,
                    controlOptions: {
                        className: 'min-max-color-control control',
                        paletteColors: CHOROPLETH_COLOR_OPTIONS
                    },
                    validation: {
                        fn: validateColor,
                        required: true,
                        msg: _('Maximum Color must be a valid hexadecimal color.').t()
                    },
                    visibleWhen: function(reportModel) {
                        return (getComputedColorMode(reportModel) in { divergent: true, sequential: true });
                    }
                },
                {
                    name: 'display.visualizations.mapping.choroplethLayer.minimumColor',
                    label: _('Minimum Color').t(),
                    defaultValue: '0x2F25BA',
                    control: ColorPickerControl,
                    controlOptions: {
                        className: 'min-max-color-control control',
                        paletteColors: CHOROPLETH_COLOR_OPTIONS
                    },
                    visibleWhen: function(reportModel) {
                        return getComputedColorMode(reportModel) === 'divergent';
                    },
                    validation: {
                        fn: validateColor,
                        required: true,
                        msg: _('Minimum Color must be a valid hexadecimal color.').t()
                    }
                },
                {
                    name: 'display.visualizations.mapping.choroplethLayer.colorBins',
                    label: _('Number of Bins').t(),
                    defaultValue: '5',
                    control: SyntheticSelectControl,
                    controlOptions: {
                        items: [
                            {
                                label: _('3').t(),
                                value: '3'
                            },
                            {
                                label: _('4').t(),
                                value: '4'
                            },
                            {
                                label: _('5').t(),
                                value: '5'
                            },
                            {
                                label: _('6').t(),
                                value: '6'
                            },
                            {
                                label: _('7').t(),
                                value: '7'
                            },
                            {
                                label: _('8').t(),
                                value: '8'
                            },
                            {
                                label: _('9').t(),
                                value: '9'
                            }
                        ],
                        toggleClassName: 'btn',
                        menuWidth: 'narrow'
                    },
                    visibleWhen: function(reportModel) {
                        return (getComputedColorMode(reportModel) in { divergent: true, sequential: true });
                    }
                },
                {
                    name: 'display.visualizations.mapping.choroplethLayer.neutralPoint',
                    label: _('Neutral Point').t(),
                    defaultValue: '0',
                    control: TextControl,
                    controlOptions: {
                        inputClassName: 'input-medium'
                    },
                    visibleWhen: function(reportModel) {
                        return getComputedColorMode(reportModel) === 'divergent';
                    },
                    validation: {
                        pattern: 'number',
                        required: true,
                        msg: _('Neutral Point must be a number.').t()
                    }
                }
            ]
        },
        {
            id: 'shapes',
            title: _('Shapes').t(),
            formElements: [
                {
                    name: 'display.visualizations.mapping.choroplethLayer.shapeOpacity',
                    label: _('Shape Opacity').t(),
                    defaultValue: '0.75',
                    control: PercentTextControl
                },
                {
                    name: 'display.visualizations.mapping.choroplethLayer.showBorder',
                    label: _('Show Borders').t(),
                    defaultValue: '1',
                    control: BooleanRadioControl
                }
            ]
        },
        {
            id: 'tiles',
            title: _('Tiles').t(),
            formElements: [
                SharedMapElements.SHOW_TILES,
                SharedMapElements.TILE_OPACITY,
                SharedMapElements.TILE_URL,
                SharedMapElements.MIN_ZOOM,
                SharedMapElements.MAX_ZOOM,
                SharedMapElements.TILE_PRESETS
            ]
        }
    ]);

});
