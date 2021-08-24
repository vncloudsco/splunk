define(
    [
        'models/services/saved/Search',
        'collections/SplunkDsBase'
    ],
    function(Model, Collection) {
        return Collection.extend({
            initialize: function() {
                Collection.prototype.initialize.apply(this, arguments);
            },
            url: 'saved/searches',
            model: Model,

            /*
             ******** HACK *******
             * As of the merge of DFS SPL-161961 savedsearches.conf now contains the concept of remote datasets.
             * It's unclear how to surface these datasets in the UI/UX right now, so the sync code below will
             * always filter them out. We should determine how to surface them and remove this filter and properly
             * filter datsets vs reports vs alerts.
             */
            sync: function(method, model, options) {
                switch (method) {
                    case 'read' :
                        options = options || {};
                        options.data = options.data || {};
                        var search = options.includeFederated
                            ? ''
                            : 'NOT (' + this.constructor.REMOTE_DATASET_SEARCH_STRING + ')';
                        if (options.data.search) {
                            search = search
                                ? search + ' AND ' + options.data.search
                                : options.data.search;
                        }
                        options.data.search = search;
                        break;
                }
                return Collection.prototype.sync.apply(this, arguments);
            }
        },
        {
            ALERT_SEARCH_STRING: '(is_scheduled=1 AND (alert_type!=always OR alert.track=1 OR (dispatch.earliest_time="rt*" AND dispatch.latest_time="rt*" AND actions="*" AND actions!="")))',
            REMOTE_DATASET_SEARCH_STRING: '(federated.provider!="")',
        });
    }
);
