define([
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
        url: 'data/indexes-extended',
        urlRoot: 'data/indexes-extended',

        getTotalRawSize: function() {
            return this.entry.content.get('total_raw_size') || 0;
        }
    });
});
