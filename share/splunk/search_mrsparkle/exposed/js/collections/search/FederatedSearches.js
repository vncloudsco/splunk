define(
    [
        'models/search/FederatedSearch',
        'collections/services/saved/Searches'
    ],
    function(
        FederatedSearchModel,
        SavedSearchCollection
    ) {
        return SavedSearchCollection.extend({
            model: FederatedSearchModel,
            initialize: function() {
                SavedSearchCollection.prototype.initialize.apply(this, arguments);
            },
            sync: function(method, model, options) {
                options.includeFederated = true;
                return SavedSearchCollection.prototype.sync.apply(this, arguments);
            }
        });
    }
);
