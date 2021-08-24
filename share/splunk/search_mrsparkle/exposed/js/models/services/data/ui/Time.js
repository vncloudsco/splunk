define(
    [
        'jquery',
        'splunk.util',
        'models/SplunkDBase',
        'util/time'
    ],
    function($, splunkutil, SplunkDBaseModel, time_utils) {
        return SplunkDBaseModel.extend({
            url: "data/ui/times",
            initialize: function() {
                SplunkDBaseModel.prototype.initialize.apply(this, arguments);
            },
            // Filters out models that do not have a time range to prevent them from showing up in "Other"
            hasTimeRange: function () {
                if (this.isDisabled()) {
                    return false;
                }

                return this.entry.content.get("earliest_time") !== undefined || this.entry.content.get("latest_time") !== undefined;
            },
            isRealTime: function() {
                if (this.isDisabled()) {
                    return false;
                }
                return time_utils.isRealtime(this.entry.content.get("latest_time"));
            },
            isPeriod: function() {
                if (this.isDisabled()) {
                    return false;
                }

                var earliest =  this.entry.content.get("earliest_time");
                var latest =  this.entry.content.get("latest_time");

                if (earliest && (earliest.indexOf("@") != -1) && (earliest.indexOf("-") != 0)) return true; // Period to date
                if (earliest && latest && (earliest.indexOf("@") != -1) && (latest.indexOf("@") != -1)) return true;  // Previous period

                return false;
            },
            isLast: function() {
                if (this.isDisabled()) {
                    return false;
                }

                if (this.isPeriod()) {
                    return false;
                }

                var earliest =  this.entry.content.get("earliest_time");
                if (!earliest) {
                    return false;
                }
                return (earliest.indexOf("-") == 0);
            },
            isOther: function() {
                if (this.isDisabled()) {
                    return false;
                }

                return !this.isRealTime() && !this.isPeriod() && !this.isLast() && this.hasTimeRange();
            },
            isDisabled: function() {
                return this.entry.content.get("disabled");
            },
            isSettings: function () {
                return this.entry.get('name') === 'settings' || this.entry.content.get('name') === 'settings';
            }
        });
    }
);
