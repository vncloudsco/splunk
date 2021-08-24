define([
            'underscore',
            'views/shared/controls/SyntheticRadioControl',
            'views/shared/vizcontrols/custom_controls/GaugeAutoRangesControlGroup',
            'views/shared/vizcontrols/custom_controls/ColorRangesControlGroup',
            'util/validation',
            'util/math_utils',
            'splunk/palettes/ColorCodes',
            './shared_elements'
    ],
        function(
            _,
            SyntheticRadioControl,
            GaugeAutoRangesControlGroup,
            ColorRanges,
            validationUtils,
            mathUtils,
            ColorCodes,
            SharedChartElements
        ) {

    return ([
        {
            id: 'general',
            title: _('General').t(),
            formElements: [
                {
                    name: 'display.visualizations.charting.chart.style',
                    label: _('Style').t(),
                    defaultValue: 'shiny',
                    control: SyntheticRadioControl,
                    controlOptions: {
                        items: [
                            {
                                label: _('Minimal').t(),
                                value: 'minimal'
                            },
                            {
                                label: _('Shiny').t(),
                                value: 'shiny'
                            }
                        ]
                    }
                }
            ]
        },
        {
            id: 'ranges',
            title: _('Color Ranges').t(),
            formElements: [
                {
                    name: 'autoMode',
                    group: GaugeAutoRangesControlGroup
                },
                {
                    name: 'display.visualizations.charting.chart.rangeValues',
                    group: ColorRanges,
                    groupOptions: {
                        rangeColorsName: 'display.visualizations.charting.gaugeColors',
                        paletteColors: _.flatten([
                            ColorCodes.SEMANTIC,
                            '#ffffff',
                            ColorCodes.DARK_GREY
                        ]),
                        displayMinMaxLabels: false
                    },
                    visibleWhen: function(reportModel) {
                        return reportModel.get('autoMode') === '0';
                    },
                    validation: {
                        fn: validationUtils.validateRangeValues
                    }
                }
            ]
        }
    ]);

});
