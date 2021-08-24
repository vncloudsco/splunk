define([
    'collections/SplunkDsBase',
    'models/services/licenser/License'
], function(SplunkDsBaseCollection, LicenseModel) {
    return SplunkDsBaseCollection.extend({
        url: 'licenser/licenses',
        model: LicenseModel
    });
});
