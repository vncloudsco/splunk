define(['models/services/admin/FshPassword', 'collections/SplunkDsBase'], function(
    FshPasswordModel,
    SplunkDsBaseCollection
) {
    return SplunkDsBaseCollection.extend({
        url: 'storage/fshpasswords',
        model: FshPasswordModel,
    });
});
