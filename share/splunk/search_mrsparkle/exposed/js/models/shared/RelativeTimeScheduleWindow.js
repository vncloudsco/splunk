define(
    [   
        'underscore',
        'models/Base',
        'util/time'
    ],
    function(
        _,
        BaseModel,
        timeUtils
    ) {
        var ONE_DAY = '-1d',
            SEVEN_DAYS = '-1w',
            ONE_MONTH = '-1mon',
            THREE_MONTHS = '-3mon',
            ONE_YEAR = '-1y',
            ALL_TIME = '0',
            CUSTOM = 'custom';
        
        var RelativeTimeScheduleWindow = BaseModel.extend({
            initialize: function() {
                BaseModel.prototype.initialize.apply(this, arguments);
            },
            
            defaults: {
                schedule_window_option: ONE_DAY,
                custom_window: ONE_DAY
            },
            
            getScheduleWindow: function() {
                return this.isCustom() ? this.get('custom_window') : this.get('schedule_window_option');
            },
            
            getItems: function() {
                var valueMap = RelativeTimeScheduleWindow.getValueMap();
                return [
                    {label: valueMap[ONE_DAY], value: ONE_DAY},
                    {label: valueMap[SEVEN_DAYS], value: SEVEN_DAYS},
                    {label: valueMap[ONE_MONTH], value: ONE_MONTH},
                    {label: valueMap[THREE_MONTHS], value: THREE_MONTHS},
                    {label: valueMap[ONE_YEAR], value: ONE_YEAR},
                    {label: valueMap[ALL_TIME], value: ALL_TIME},
                    {label: _('Custom').t(), value: CUSTOM}
                ];
            },
            
            isCustom: function() {
                return this.get('schedule_window_option') === CUSTOM;
            },
            
            setScheduleWindow: function(schedule_window) {
                var valueMap = this.constructor.getValueMap();
                if (valueMap[schedule_window]) {
                    this.set({
                        schedule_window_option: schedule_window,
                        custom_window: schedule_window
                    });
                } else {
                    this.set({
                        schedule_window_option: CUSTOM,
                        custom_window: schedule_window
                    });
                }
            }
        
        }, 
        {
            ONE_DAY: ONE_DAY,
            SEVEN_DAYS: SEVEN_DAYS,
            ONE_MONTH: ONE_MONTH,
            THREE_MONTHS: THREE_MONTHS,
            ONE_YEAR: ONE_YEAR,
            ALL_TIME: ALL_TIME,
            CUSTOM: CUSTOM,
            
            getValueMap: function() {
                var valueMap = {};
                valueMap[ONE_DAY] = _('1 Day').t();
                valueMap[SEVEN_DAYS] = _('7 Days').t();
                valueMap[ONE_MONTH] = _('1 Month').t();
                valueMap[THREE_MONTHS] = _('3 Months').t();
                valueMap[ONE_YEAR] = _('1 Year').t();
                valueMap[ALL_TIME] = _('All Time').t();
                
                return valueMap;
            }
        });
        
        return RelativeTimeScheduleWindow;
    }
);
