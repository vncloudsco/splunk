define(
    [
        'jquery',
        'underscore',
        'models/EAIBase'
    ],
    function(
        $,
        _,
        EAIBaseModel
    ) {
        return EAIBaseModel.extend({
            url: 'catalog/metricstore/metrics',
            urlRoot: 'catalog/metricstore/metrics',
            getContent: function() {
                return this.entry.content;
            }
        });
    }
);
