define(
    [   
        'underscore',
        'jquery',
        'models/shared/RelativeTimeScheduleWindow'
    ],
    function(
        _,
        $,
        RelativeTimeScheduleWindow
    ) {
        var EMPTY = '';
        
        var BackfillTimeScheduleWindow = RelativeTimeScheduleWindow.extend({
            initialize: function() {
                RelativeTimeScheduleWindow.prototype.initialize.apply(this, arguments);
            },
            
            defaults: {
                schedule_window_option: EMPTY,
                custom_window: EMPTY
            },
            
            getItems: function() {
                var valueMap = BackfillTimeScheduleWindow.getValueMap();
                return [
                    {label: valueMap[EMPTY], value: EMPTY},
                    {label: valueMap[RelativeTimeScheduleWindow.ONE_DAY], value: RelativeTimeScheduleWindow.ONE_DAY},
                    {label: valueMap[RelativeTimeScheduleWindow.SEVEN_DAYS], value: RelativeTimeScheduleWindow.SEVEN_DAYS},
                    {label: valueMap[RelativeTimeScheduleWindow.ONE_MONTH], value: RelativeTimeScheduleWindow.ONE_MONTH},
                    {label: valueMap[RelativeTimeScheduleWindow.THREE_MONTHS], value: RelativeTimeScheduleWindow.THREE_MONTHS},
                    {label: valueMap[RelativeTimeScheduleWindow.ONE_YEAR], value: RelativeTimeScheduleWindow.ONE_YEAR},
                    {label: valueMap[RelativeTimeScheduleWindow.ALL_TIME], value: RelativeTimeScheduleWindow.ALL_TIME},
                    {label: _('Custom').t(), value: RelativeTimeScheduleWindow.CUSTOM}
                ];
            }
        }, 
        {
            EMPTY: EMPTY,
            getValueMap: function() {
                var valueMap = RelativeTimeScheduleWindow.getValueMap();
                valueMap[EMPTY] = _('Match Summary Range').t();
                
                return valueMap;
            }
        });
        
        return BackfillTimeScheduleWindow;
    }
);
