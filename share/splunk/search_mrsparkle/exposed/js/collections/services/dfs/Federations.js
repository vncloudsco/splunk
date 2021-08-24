define(['models/services/dfs/Federation', 'collections/SplunkDsBase'], function(
    FederationModel,
    SplunkDsBaseCollection
) {
    return SplunkDsBaseCollection.extend({
        url: 'dfs/federated',
        model: FederationModel,
    });
});
