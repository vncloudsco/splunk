define(
    [
    	"jquery",
    	"underscore",
        "models/knowledgeobjects/Sourcetype",
        "collections/SplunkDsBase"
    ],
    /**
     * @param {Object} options
     * @param {Object} options.schemaName The name of the metric-transform to retrieve
     */
    function($, _, Model, SplunkDsBaseCollection) {
        return SplunkDsBaseCollection.extend({
            model: Model,
            initialize: function(options) {
                if (options === undefined) {
                    throw new Error('MetricSchema collection is missing required options parameter');
                }
                if (options.isCloud === undefined) {
                    throw new Error('MetricSchema collection is missing required isCloud parameter');
                }
                if (options.schemaName === undefined) {
                    throw new Error('MetricSchema collection is missing required schemaName parameter');
                }
                var onPremEndpoint = 'data/transforms/metric-schema';
                var cloudEndpoint = 'cluster_blaster_transforms/sh_metric_transforms_manager';
                var endpoint = options.isCloud ? cloudEndpoint : onPremEndpoint;
                this.url = endpoint + '/' + encodeURIComponent(options.schemaName);
                SplunkDsBaseCollection.prototype.initialize.apply(this, arguments);
            },
            getAttributes: function(){
                var model = this.models[0];
                return {
                    'field_names': model.entry.content.get('METRIC-SCHEMA-MEASURES'),
                    'blacklist_dimensions' : model.entry.content.get('METRIC-SCHEMA-BLACKLIST-DIMS')
                };
            }
        });
    }
);
