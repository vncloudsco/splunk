define(
    [
        'jquery',
        'underscore',
        "models/services/data/Indexes",
        "collections/SplunkDsBase",
        'models/services/server/ServerInfo'
    ],
    function(
        $,
        _,
        IndexModel,
        SplunkDsBaseCollection,
        ServerInfoModel
    ) {
        var ShApiUrl = 'data/indexes';
        var CloudApiUrl = 'search/jobs/oneshot';

        return SplunkDsBaseCollection.extend({
            model: IndexModel,
            url: null,
            initialize: function(models, options) {
                SplunkDsBaseCollection.prototype.initialize.call(this, models, options);
            },
            fetch: function(options) {
                if (this.url) {
                    // fast path - api url has been already "resolved"
                    return this._fetchIndexes(options);
                }
                // Slow path - find API according to the system configuration.
                // We use an additional promise to sync the caller.
                var dfd = $.Deferred();
                var serverInfo = new ServerInfoModel();
                serverInfo.fetch().done(function() {
                    this.url = serverInfo.isCloud() && serverInfo.isClusterSearchHead() ? CloudApiUrl : ShApiUrl;
                    this._fetchIndexes(options).done(function(result) {
                        dfd.resolve(result);
                    });
                }.bind(this));
                return dfd.promise();
            },
            getIndexDataType: function(indexName) {
                var index = this.findByEntryName(indexName);
                if (index) {
                    return index.getDataType();
                }
            },
            getItems: function() {
                return _(this.models).map(function(lookup) {
                    var name = lookup.entry.get("name");
                    return {
                        value: name,
                        label: _(name).t()
                    };
                });
            },
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
            _fetchIndexes: function(options) {
                return this.url === CloudApiUrl ?
                    this._fetchCloudIndexes(options) :
                    this._fetchShIndexes(options);
            },
            _fetchShIndexes: function(options) {
                return SplunkDsBaseCollection.prototype.fetch.call(
                    this, $.extend(true, {}, {data: {datatype: 'all'}}, options));
            },
            _fetchCloudIndexes: function(options) {
                // Indexes are defined on the indexers and could be absent on the
                // search head itself (actually that is mostly the case). A
                // "savedsearch" is used to collect information about indexes.
                // Saved search query is invoked with admin rights (see default.meta
                // for details) and therefore could be accessed even by a
                // user that doesn't have rest to indexers capability.
                var query;
                if (options && options.isCloudAdmin) {
                    query = '| eventcount summarize=false index=* | dedup index | rename index As title | fields title';

                }
                else {
                    query = '| savedsearch _private_splunk_getCloudIndexesInfo';
                }
				var data = {};
				// Add filtering and sorting to the query.
                if (options && options.data) {
                    if (options.data.search && !options.isCloudAdmin)
                        query += ' | search ' + options.data.search;
                    if (options.data.sort_key)
                        query += ' | sort ' + options.data.sort_key;
					if (options.data.hasOwnProperty("count")) {
					    // Some apps still pass count as -1, which will result in invalid count for oneshot search.
						if (options.data.count === -1) {
							data.count = 0;
						}
						else {
							data.count = options.data.count;
						}
					}
                }
				data.search = query;
                return SplunkDsBaseCollection.prototype.fetch.call(
                   this, {data: data, success: options && options.success, error: options && options.error});
            }
        });
    }
);
