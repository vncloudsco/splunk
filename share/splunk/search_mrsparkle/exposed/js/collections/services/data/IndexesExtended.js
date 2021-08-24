define([
    'jquery',
    'underscore',
    "models/services/data/IndexesExtended",
    "collections/SplunkDsBase"
],
function(
    $,
    _,
    IndexExtendedModel,
    SplunkDsBaseCollection
) {
    return SplunkDsBaseCollection.extend({
        model: IndexExtendedModel,
        url: 'data/indexes-extended',
        parse: function(response) {
            if (response && response.results && !response.entries) {
                // convert splunk query response to entries
                var entries = {
                    entry: [],
                    paging: { offset: 0, total: response.results.length}
                };
                _.each(response.results, function(value) {
                    entries.entry.push({
                        name: value.title,
                        content: value
                    });
                }.bind(this));
                response = entries;
            }
            return SplunkDsBaseCollection.prototype.parse.call(this, response);
        },
        getIndexTotalRawSize: function(indexName) {
            var index = this.findByEntryName(indexName);
            if (index) {
                return index.getTotalRawSize();
            }
            return 0;
        }
    });
});
