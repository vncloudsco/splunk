define(
    [
        'jquery',
        'underscore',
        'module',
        'models/services/configs/Visualization',
        'collections/SplunkDsBase',
        'helpers/VisualizationRegistry',
        'util/console'
    ],
    function(
        $,
        _,
        module,
        VisualizationModel,
        SplunkDsBaseCollection,
        VisualizationRegistry,
        console
    ) {

        return SplunkDsBaseCollection.extend({
            moduleId: module.id,
            url: 'data/ui/visualizations',
            model: VisualizationModel,
            fetch: function(options) {
                options = options || {};
                var appLocals = options.appLocalsCollection;
                var allDfd = $.Deferred();
                var baseOptions = _.extend({}, options, {
                    data: _.extend({
                        includeFormatter: options.includeFormatter !== false
                    }, options.data),
                    success: function(collection, response, opts) {
                        if (options.success) {
                            allDfd.then(function() {
                                options.success(collection, response, opts);
                            });
                        }
                    }
                });
                var fetchDfd = SplunkDsBaseCollection.prototype.fetch.call(this, baseOptions);
                fetchDfd.done(function(response, status, options){
                    VisualizationRegistry.registerVisualizationsCollection({
                        collection: {
                            visualizations: this,
                            appLocals: appLocals
                        }
                    }).then(function() {
                        allDfd.resolve(response, status, options);
                    });
                }.bind(this));
                fetchDfd.fail(function(e){
                    allDfd.reject(e);
                });
                return allDfd;
            }
        });
    }
);
