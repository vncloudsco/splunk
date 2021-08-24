define(
    [
        'underscore',
        'models/SplunkDBase'
    ],
    function(
        _,
        SplunkDBaseModel
    ) {
        return SplunkDBaseModel.extend({
            url: 'saved/bookmarks/monitoring_console',
            urlRoot: 'saved/bookmarks/monitoring_console',
            id: 'monitoring_console',
            initialize: function() {
                SplunkDBaseModel.prototype.initialize.apply(this, arguments);
            },
            save: function(attributes, options) {
                if (this.isNew()) {
                    options = options || {};
                    options.data = _.defaults(options.data || {}, {
                        app: 'splunk_monitoring_console',
                        owner: 'nobody',
                        name: this.entry.get('name'),
                    });
                }
                return SplunkDBaseModel.prototype.save.call(this, attributes, options);
            }
        });
    }
);
