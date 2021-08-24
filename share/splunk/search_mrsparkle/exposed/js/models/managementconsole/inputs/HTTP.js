// HTTP Inputs model
// @author: lbudchenko
define([
    'jquery',
    'underscore',
    'backbone',
    'models/managementconsole/inputs/Base',
    'mixins/input_models',
    'splunk.util'
], function (
    $,
    _,
    Backbone,
    BaseModel,
    inputMixin,
    splunkUtil
) {
    var currentStep = 0;
    var STANZA_NAME_PREFIX = 'http://';

    var InputModel = BaseModel.extend({
        url: '/http',

        parse: function(response, options) {
                // make a defensive copy of response since we are going to modify it
                response = $.extend(true, {}, response);

                if (!response || !response.entry || response.entry.length === 0) {
                    return;
                }
                var newAttrs = {};

                for (var attr in response.entry[0].content) {
                    var val = response.entry[0].content[attr];
                    if (attr === 'host' && val === '$decideOnStartup') {
                        delete response.entry[0].content[attr];
                    } else if (val === null || val === '') {
                        // filter out fields with empty values
                        delete response.entry[0].content[attr];
                    } else if (attr === 'indexes' && _.isString(val)) {
                        newAttrs[this.FIELD_PREFIX + attr] = val.split(',');
                    } else {
                        newAttrs[this.FIELD_PREFIX + attr] = val;
                    }
                }
                this.set(newAttrs, {silent: true});

                return BaseModel.prototype.parse.call(this, response, options);
            },

        initialize: function () {
            BaseModel.prototype.initialize.apply(this, arguments);

            this._documentationType = 'http';
        },

        validation: {
            'ui.name': [
                {
                    required: function() {
                        return this.isNew();
                    },
                    msg: _("Token name is required.").t()
                }
            ]
        },

        getStanzaName: function() {
            return STANZA_NAME_PREFIX + this.entry.get('name');
        },

        getReviewFields: function () {
            return [
                'name',
                'source',
                'description',
                'useACK',
                'index',
                'indexes',
                'sourcetype',
                'bundle'
            ];
        },

        // saves the step # in model's outer scope
        setStep: function(step) {
            currentStep = step;
        },

        formatDataToPOST: function (postData) {
            if (_.has(postData, 'useACK')) {
                postData.useACK = "" + splunkUtil.normalizeBoolean(postData.useACK);
            }
            if (_.has(postData, 'indexes') && _.isArray(postData.indexes)) {
                postData.indexes = postData.indexes.join(',');
            }
        }
    });

    _.extend(InputModel.prototype, inputMixin);
    return InputModel;


});
