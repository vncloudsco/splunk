define([
        'underscore',
        'splunk',
        'views/shared/controls/BooleanRadioControl',
        'views/shared/controls/SyntheticRadioControl',
        'views/shared/controls/SyntheticSelectControl',
        'views/shared/controls/SyntheticCheckboxControl',
        'views/shared/viz/controls/SplitFieldsControlGroup'
    ],
    function (_,
              Splunk,
              BooleanRadioControl,
              SyntheticRadioControl,
              SyntheticSelectControl,
              SyntheticCheckboxControl,
              SplitFieldsControlGroup) {
        return ({

            TRELLIS_SIZE: {
                name: 'display.visualizations.trellis.size',
                label: _('Size').t(),
                defaultValue: 'medium',
                control: SyntheticRadioControl,
                controlOptions: {
                    additionalClassNames: 'locale-responsive-layout',
                    items: [
                        {
                            label: _('Small').t(),
                            value: 'small'
                        },
                        {
                            label: _('Medium').t(),
                            value: 'medium'
                        },
                        {
                            label: _('Large').t(),
                            value: 'large'
                        }
                    ]
                },
                enabledWhen: function (reportContent) {
                   return Splunk.util.normalizeBoolean(reportContent.get('display.visualizations.trellis.enabled'));
                }
            },

            TRELLIS_ENABLED: {
                name: 'display.visualizations.trellis.enabled',
                label: _('Use Trellis Layout').t(),
                defaultValue: false,
                control: SyntheticCheckboxControl
            },

            TRELLIS_SPLIT_FIELD: {
                name: 'display.visualizations.trellis.splitBy',
                label: _('Split By').t(),
                group: SplitFieldsControlGroup,
                enabledWhen: function (reportContent) {
                    return Splunk.util.normalizeBoolean(reportContent.get('display.visualizations.trellis.enabled'));
                }
            },

            TRELLIS_AXIS_SHARED: {
                name: 'display.visualizations.trellis.scales.shared',
                label: _('Scale').t(),
                defaultValue: '1',
                control: BooleanRadioControl,
                controlOptions: {
                    trueLabel: _('Shared').t(),
                    falseLabel: _('Independent').t()
                },
                enabledWhen: function (reportContent) {
                    return Splunk.util.normalizeBoolean(reportContent.get('display.visualizations.trellis.enabled'));
                },
                visibleWhen: function(reportModel) {
                    var shareCharts = ['line', 'column', 'bar', 'area'];
                    var isShareChart = reportModel.get('display.visualizations.type') === 'charting'
                        && _.contains(shareCharts, reportModel.get('display.visualizations.charting.chart'));
                    var isShareMap = reportModel.get('display.visualizations.type') === 'mapping'
                        && reportModel.get('display.visualizations.mapping.type') === 'choropleth'
                        && reportModel.get('display.visualizations.mapping.choroplethLayer.colorMode') !== 'categorical';

                    return isShareChart || isShareMap;
                }
            }
        });
    });
