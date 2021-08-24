define([
    'underscore',
    'jquery',
    'backbone',
    'models/StaticIdBase',
    'util/splunkd_utils',
    'splunk.util'
],
function (
    _,
    $,
    Backbone,
    BaseModel,
    splunkDUtils,
    splunkUtils
) {
    return BaseModel.extend({
        sync: function(method, model, options) {
            var defaults = {
                data: {
                    output_mode: 'json'
                }
            };
            switch (method) {
                case 'read':
                    defaults.processData = true;
                    defaults.type = 'GET';
                    defaults.url = splunkDUtils.fullpath(model.id);
                    $.extend(true, defaults, options);
                    break;
                default:
                    throw new Error(splunkUtils.sprintf('invalid method: %s', method));
            }
            return Backbone.sync.call(this, method, model, defaults);
        },

        getHealth: function() {
            try {
                return this.attributes.entry[0].content.health;
            } catch(err) {
                return "";
            }
        },

        isDisabled: function() {
            try {
                return this.attributes.entry[0].content.disabled;
            }
            catch(err) {
                return false;
            }
        }
    },
    {
        id: 'server/health/splunkd'
    });
});