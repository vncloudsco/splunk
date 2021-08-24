define(
    [
        'underscore',
        'models/services/catalog/metricstore/Rollup',
        'collections/SplunkDsBase',
    ],
    function(
        _,
        RollupModel,
        SplunkDsBaseCollection
    ) {
        return SplunkDsBaseCollection.extend({
            model: RollupModel,
            url: 'catalog/metricstore/rollup'
        });
    }
);
