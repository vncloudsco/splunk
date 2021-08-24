define([
        "collections/managementconsole/DmcsBase",
        "models/managementconsole/Package"
    ],
    function(
        DmcsBaseCollection,
        Package
    ) {
        return DmcsBaseCollection.extend({
            url: 'dmc/packages',
            model: Package
        });
    }
);
