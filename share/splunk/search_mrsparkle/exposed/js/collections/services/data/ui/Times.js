define(
    [
        'util/general_utils',
        'models/services/data/ui/Time',
        'collections/SplunkDsBase'
    ],
    function(Utils, TimeModel, SplunkDsBaseCollection) {
        var TimesCollection = SplunkDsBaseCollection.extend({
            url: 'data/ui/times',
            model: TimeModel,
            initialize: function() {
                SplunkDsBaseCollection.prototype.initialize.apply(this, arguments);
            },
            filterToRealTime: function(type) {
                return this.filter(function(model) {
                    return model.isRealTime();
                });
            },
            filterToPeriod: function(type) {
                return this.filter(function(model) {
                    return model.isPeriod();
                });
            },
            filterToLast: function(type) {
                return this.filter(function(model) {
                    return model.isLast();
                });
            },
            filterToOther: function(type) {
                return this.filter(function(model) {
                    return model.isOther();
                });
            },
            comparator: function(model) {
                // return the numeric value of the order field or MAXINT if not a valid number
                return parseInt(model.entry.content.get('order'), 10) || Number.MAX_VALUE;
            },
            // Return a settings model to enable/disable time-picker panels
            getSettings: function () {
                return this.filter(function (model) {
                    return model.isSettings();
                }).map(function (model) {
                    return {
                        showAdvanced: Utils.normalizeBoolean(model.entry.content.get('show_advanced')),
                        showDate: Utils.normalizeBoolean(model.entry.content.get('show_date_range')),
                        showDateTime: Utils.normalizeBoolean(model.entry.content.get('show_datetime_range')),
                        showPresets: Utils.normalizeBoolean(model.entry.content.get('show_presets')),
                        showRealtime: Utils.normalizeBoolean(model.entry.content.get('show_realtime')),
                        showRelative: Utils.normalizeBoolean(model.entry.content.get('show_relative'))
                    };
                })[0];
            }
        });

        return TimesCollection;
    }
);
