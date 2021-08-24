/**
 * @author jszeto
 * @date 2/20/15
 * 
 * Represents a specific Index
 * 
 * Cloud-specific endpoint that is only available if the Cloud Administration app has been installed
 * (https://github.com/SplunkStorm/cloud_apps)
 *
 * The response format should be a subset of the response from the services/data/indexes/INDEX_NAME endpoint
 *
 */
define(
    [
        'jquery',
        'underscore',
        'models/Base',
        'models/services/data/Indexes',
        'models/indexes/cloud/CloudIndexValidation',
        'util/splunkd_utils'
    ],
    function(
        $,
        _,
        BaseModel,
        BaseIndexesModel,
        CloudIndexValidation,
        splunkdutils
    ) {
        var Index = BaseIndexesModel.extend({
            url: 'cluster_blaster_indexes/sh_indexes_manager',
            validation: CloudIndexValidation.validationObj,
            initialize: function() {
                BaseIndexesModel.prototype.initialize.apply(this, arguments);
            },

            _onerror: function(model, response, options) {
                var status, text, message;

                if (response && response.hasOwnProperty('fetchXhr')
                    && response.fetchXhr && response.fetchXhr.hasOwnProperty('status')
                    && response.fetchXhr.status == 404
                    && response.fetchXhr.hasOwnProperty('responseJSON')
                    && typeof response.fetchXhr.responseJSON == 'object'
                    && response.fetchXhr.responseJSON.messages.length
                    && response.fetchXhr.responseJSON.messages[0].hasOwnProperty('text')
                ){
                    text = response.fetchXhr.responseJSON.messages[0].text;
                    message = splunkdutils.createMessageObject('error', text);
                }

                if (message) {
                    this.trigger('serverValidated', false, this, [message]);
                    model.error.set('message', message);
                } else {
                    BaseModel.prototype._onerror.call(this, model, response, options);
                }
            }
        });

        return Index;
    }
);
