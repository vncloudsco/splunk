define(
    [
        'jquery',
        'underscore',
        'backbone',
        'models/SplunkDBase',
        'util/splunkd_utils'
    ],
    function(
        $,
        _,
        Backbone,
        SplunkDBase,
        splunkd_utils
    ) {
        /**
         * @constructor
         * @memberOf models
         * @name InstallApp
         * @extends models.SplunkDBase
         * @description Model that will install an app given a splunkbase URL. It performs a POST to the apps/local endpoint.
         * This model requires the "auth" attribute to be set with the authorization token retrieved from
         * logging into splunkbase. Use models/apps_remote/ProxyLogin to obtain the authorization token.
         * Pass the following data:
         *
         */
        return SplunkDBase.extend(/** @lends models.apps_remote.InstallApp.prototype */{
            url: 'apps/local',
            sync: function(method, model, options) {
                if ( method!=='create' ) {
                    throw new Error('invalid method: ' + method);
                }
                options = options || {};
                var defaults = {
                    data: {
                        filename: true,
                        output_mode: 'json'
                    },
                    processData: true,
                    type: 'POST',
                    url: splunkd_utils.fullpath(_.isFunction(model.url) ? model.url() : model.url || model.id)
                };
                $.extend(true, defaults, options);
                return Backbone.sync.call(this, method, model, defaults);
            },

            parseSplunkDMessages: function(response) {
                // If the message has been created by admin.py, then it has a different format than an EAI response.
                // Normalize the message into the EAI response format.
                if (_(response).has("status") && _(response).has("msg")) {
                    response = {messages: [{type: response.status.toLowerCase(), text: response.msg}]};
                }

                return SplunkDBase.prototype.parseSplunkDMessages.call(this, response);
            }

        });
    }
);
