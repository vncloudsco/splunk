define(
    [
        'underscore',
        'models/services/catalog/metricstore/Dimensions',
        'collections/SplunkDsBase'
    ],
    function(
        _,
        DimensionsModel,
        SplunkDsBaseCollection
    ) {
        return SplunkDsBaseCollection.extend({
            model: DimensionsModel,
            url: 'catalog/metricstore/dimensions',
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
