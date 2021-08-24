define(
    [
        "jquery",
        'underscore',
        "util/splunkd_utils",
        "models/services/data/inputs/Oneshot",
        "models/indexes/shared/IndexesDistributedFetchData",
        "collections/SplunkDsBase"
    ],
    function(
        $,
        _,
        splunkdUtil,
        OneshotModel,
        IndexesDistributedFetchData,
        SplunkDsBaseCollection
    ) {
        return SplunkDsBaseCollection.extend({
            model: OneshotModel,
            url: 'search/jobs/oneshot',
            initialize: function(models, options) {
                options = options || {};
                options.fetchData = options.fetchData || new IndexesDistributedFetchData();
                SplunkDsBaseCollection.prototype.initialize.call(this, models, options);
            },

            parse: function(response) {
                if (response && response.results) {
                    var newResponse = {};
                    newResponse.entry = [];
                    newResponse.paging = {};

                    _.each(response.results, function(value) {
                        var bundleJson = {
                            name: value.name,
                            content: value
                        };
                        newResponse.entry.push(bundleJson);
                    }.bind(this));

                    newResponse.paging.total = newResponse.entry.length;
                    response = newResponse;
                }
                return SplunkDsBaseCollection.prototype.parse.call(this, response);
            },

            searchByValues: function(values) {
                var $deferred = $.Deferred();
                if (values === void 0) {
                    $deferred.reject();
                    return $deferred;
                }
                var searchFilterString = _.map(values, function(value) {
                    return 'index=' + splunkdUtil.quoteSearchFilterValue(value);
                }).join(' ');
                this.fetchData.set('searchFilterString', searchFilterString, {silent: true});
                $.when(this.fetch())
                    .then(function () {
                        $deferred.resolve(this.models);
                        this.reset(void 0, {silent:true});
                    }.bind(this))
                    .fail(function () {
                        $deferred.reject();
                    });
                return $deferred;
            },

            search: function(rawSearch) {
                var searchFilterString = "index=" + splunkdUtil.quoteSearchFilterValue("*" + rawSearch + "*");
                this.fetchData.set({searchFilterString: searchFilterString});
            }
        });
    }
);

