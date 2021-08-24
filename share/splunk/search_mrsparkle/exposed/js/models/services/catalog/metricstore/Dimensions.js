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
            url: 'catalog/metricstore/dimensions',
            urlRoot: 'catalog/metricstore/dimensions',
            getContent: function() {
                return this.entry.content;
            }
        });
    }
);
