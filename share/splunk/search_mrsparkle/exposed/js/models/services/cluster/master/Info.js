define(
    [
        'underscore',
        'models/StaticIdSplunkDBase',
        'splunk.util'
    ],
    function(_, BaseModel, splunkUtil){
        return BaseModel.extend({
            initialize: function() {
                BaseModel.prototype.initialize.apply(this, arguments);
            },
            getAvailableSites: function() {
                var sites = [];
                if (_.has(this.entry.content.attributes, 'available_sites')) {
                    sites = this.entry.content.get('available_sites')
                        .replace('[', '').replace(']', '').split(',');
                }
                return sites;
            },
            isMultiSite: function() {
                return splunkUtil.normalizeBoolean(this.entry.content.get("multisite")); 
            } 
        },
        {
            id: 'cluster/master/info/master'
        });
    }
);
