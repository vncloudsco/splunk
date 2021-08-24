define(
    [   
        'underscore',
        'models/shared/RelativeTimeScheduleWindow',
        'util/validation'
    ],
    function(
        _,
        RelativeTimeScheduleWindow,
        validationUtils
    ) {
        var ONE_HOUR = 3600;
        
        var MaxTimeScheduleWindow = RelativeTimeScheduleWindow.extend({
            initialize: function() {
                RelativeTimeScheduleWindow.prototype.initialize.apply(this, arguments);
            },
            
            validation: {
                custom_window: {
                    fn: 'validateCustomWindow'
                }
            },
            
            validateCustomWindow: function(value, attr, computedState) {
                var error = _('Custom window must be a positive integer').t();
                
                if (computedState.schedule_window_option === RelativeTimeScheduleWindow.CUSTOM) {
                    if (_.isNumber(value)) {
                        if (!_.isFinite(value) || !(value >= 0)) {
                            return error;
                        }
                    } else {
                        if (!validationUtils.isNonNegValidInteger(value)) {
                            return error;
                        }
                    }
                }
            },
            
            defaults: {
                schedule_window_option: ONE_HOUR,
                custom_window: ONE_HOUR
            },
            
            getItems: function() {
                var valueMap = MaxTimeScheduleWindow.getValueMap();
                return [
                    {label: valueMap[ONE_HOUR], value: ONE_HOUR},
                    {label: _('Custom').t(), value: RelativeTimeScheduleWindow.CUSTOM}
                ];
            }
        }, 
        {
            ONE_HOUR: ONE_HOUR,
            getValueMap: function() {
                var valueMap = {};
                valueMap[ONE_HOUR] = _('1 Hour').t();
                
                return valueMap;
            }
        });
        
        return MaxTimeScheduleWindow;
    }
);
