define(
    [
        'underscore',
        'models/services/catalog/metricstore/Metrics',
        'collections/SplunkDsBase'
    ],
    function(
        _,
        MetricsModel,
        SplunkDsBaseCollection
    ) {
        return SplunkDsBaseCollection.extend({
            model: MetricsModel,
            url: 'catalog/metricstore/metrics',
            getItems: function() {
                return _(this.models).map(function(lookup) {
                    var name = lookup.entry.get("name");
                    return {
                        value: name,
                        label: _(name).t()
                    };
                });
            }
        });
    }
);
