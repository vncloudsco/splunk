define(
    [
        'jquery',
        'underscore',
        'collections/SplunkDsBase',
        'collections/services/data/Indexes',
        'util/indexes/RollupUtils'
    ],
    function(
        $,
        _,
        SplunkDsBaseCollection,
        IndexesBaseCollection,
        RollupUtils
    ) {
        return IndexesBaseCollection.extend({
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
                if (response && response.entry) {
                    response.entry = response.entry.map(function(entry) {
                        if (entry.content.datatype === 'metric' && entry.content.rollupPolicy) {
                            if (entry.content.rollupPolicy.summaries) {
                                entry.content.datatype = 'rollup';
                            }
                            entry.content.rollupUIProps = RollupUtils.getUIPropsFromRollupPolicy(entry.content.rollupPolicy);
                        }
                        return entry;
                    }.bind(this));
                }
                return SplunkDsBaseCollection.prototype.parse.call(this, response);
            },
            _fetchShIndexes: function(options) {
                return SplunkDsBaseCollection.prototype.fetch.call(
                    this, $.extend(true, {}, {
                        data: {
                            datatype: 'all',
                            list_rollup: 1
                        }
                    }, options)
                );
            }
        });
    }
);
