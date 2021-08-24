define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/shared/apps_remote/ResultsPane',
    'views/managementconsole/apps/install_app/overrides/shared/apps_remote/apps/Master',
    'views/managementconsole/apps/install_app/overrides/shared/apps_remote/SortFilter'
], function(
    $,
    _,
    Backbone,
    module,
    ResultsPane,
    AppsBoxView,
    SortFilterView
){
    return ResultsPane.extend({
        moduleId: module.id,

        initialize: function(options) {
            options = $.extend(true, options, {
              appsBoxViewClass: AppsBoxView,
              sortFilterClass: SortFilterView
            });
            ResultsPane.prototype.initialize.call(this, options);
        },

        onAppsRemoteSync: function() {
            this.syncDmcAppsCollection().always(function() {
                ResultsPane.prototype.onAppsRemoteSync.apply(this, arguments);
            }.bind(this));
        },

        syncDmcAppsCollection: function() {
            var query = {
                    $or: []
                },
                apps = _.map(this.collection.appsRemote.models, function(app) {
                    return app.attributes.appid;
                });

            _.each(apps, function(appid) {
                query.$or.push({name: appid});
            });

            this.collection.dmcApps.fetchData.set({
                query: JSON.stringify(query)
            }, {
                silent: true
            });

            return this.collection.dmcApps.fetch();
        }
    });
});