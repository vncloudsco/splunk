define(
    [
        'jquery',
        'underscore',
        'backbone',
        'models/SplunkDBase',
        'splunk.util',
        'util/splunkd_utils',
        'util/console'
    ],
    function($, _, Backbone, SplunkDBaseModel, splunkUtils, splunkdUtils, console) {
        var extractAppOwner = function(options) {
            var appOwner = {};
            if (options && options.data){
                appOwner = $.extend(appOwner, {
                    app: options.data.app || undefined,
                    owner: options.data.owner || undefined,
                    sharing: options.data.sharing || undefined
                });

                delete options.data.app;
                delete options.data.owner;
                delete options.data.sharing;
            }
            return appOwner;
        };

        var syncCreate = function(model, options) {
            var url = {}, attrs,
                bbXHR, deferredResponse = $.Deferred(),
                defaults = {
                    data: {
                        output_mode: 'json',
                        name: model.entry.get('name')   // required for POST create
                    }
                },
                appOwner = extractAppOwner(options);

            url = _.isFunction(model.url) ? model.url() : model.url;

            defaults.url = splunkdUtils.fullpath(url, appOwner);
            defaults.processData = true;

            attrs = _.reduce(model.toJSON(), function(memo, value, key) {
                if (! _.isUndefined(value)) { memo[key] = value; }
                return memo;
            }, {});
            $.extend(true, defaults.data, attrs);
            $.extend(true, defaults, options);

            bbXHR = Backbone.sync.call(this, "create", model, defaults);
            bbXHR.done(function() {
                deferredResponse.resolve.apply(deferredResponse, arguments);
            });
            bbXHR.fail(function() {
                deferredResponse.reject.apply(deferredResponse, arguments);
            });
            return deferredResponse.promise();
        },
        syncUpdate = function(model, options) {
            var url = {}, attrs,
                bbXHR, deferredResponse = $.Deferred(),
                defaults = {
                    data: {
                        output_mode: 'json'
                    }
                },
                appOwner = extractAppOwner(options);

            defaults.url = splunkdUtils.fullpath(model.id, appOwner);
            model.unset('id');
            model.unset('name');
            defaults.processData = true;
            defaults.type = 'POST';
            attrs = _.reduce(model.toJSON(), function(memo, value, key) {
                if (! _.isUndefined(value)) { memo[key] = value; }
                return memo;
            }, {});
            $.extend(true, defaults.data, attrs);
            $.extend(true, defaults, options);

            // turn off client-side normalization since backend has no consistent
            // boolean normalization (e.g. default/props.conf uses a mix of true/True/1)
            //defaults.data = splunkdUtils.normalizeValuesForPOST(defaults.data);

            bbXHR = Backbone.sync.call(this, "update", model, defaults);
            bbXHR.done(function() {
                deferredResponse.resolve.apply(deferredResponse, arguments);
            });
            bbXHR.fail(function() {
                deferredResponse.reject.apply(deferredResponse, arguments);
            });
            return deferredResponse.promise();
        };

        return SplunkDBaseModel.extend({
            initialize: function(options) {
                SplunkDBaseModel.prototype.initialize.apply(this, arguments);
                this.isCloud = options.isCloud;
                var onPremEndpoint = 'data/transforms/metric-schema';
                var cloudEndpoint = 'cluster_blaster_transforms/sh_metric_transforms_manager';
                this.url = this.isCloud ? cloudEndpoint : onPremEndpoint;
            },
            defaults: {
                'blacklist_dimensions': undefined,
                'field_names': undefined,
                'name': undefined,
                'sourcetype_name': ''
            },
            validation: {
                'sourcetype_name': [
                    {
                        required: true,
                        msg: _('Source type name is required').t()
                    },
                    {
                        required: function (val, attr, computed) {
                            return computed[attr] === '';
                        },
                        pattern: /^[^#?&]*$/,
                        msg: _('Source type name does not allow ? or # or &.').t()
                    }
                ],
                'field_names': [
                    {
                        required: function (val, attr, computed) {
                            return computed[attr] === '';
                        },
                        msg: _('Measures field in \'Metrics\' tab must include at least one word').t()
                    },
                    {
                        required: function (val, attr, computed) {
                            return computed[attr] === '';
                        },
                        pattern: /^(\s*[\w. *-]+\s*)(,\s*[\w. *-]+\s*)*$/,
                        msg: _('Measures field in \'Metrics\' tab must be non-empty, comma separated, alphanumeric words').t()
                    }
                ],
                'blacklist_dimensions': [
                    {
                        required: function (val, attr, computed) {
                            return computed[attr] && computed[attr].length;
                        },
                        pattern: /^(\s*[\w. *-]+\s*)(,\s*[\w. *-]+\s*)*$/,
                        msg: _('Blacklist field in \'Metrics\' tab must be non-empty, comma separated, alphanumeric words').t()
                    }
                ]
            },
            isParsing: function() {
                return this._parsing;
            },
            getExplicitProps: function() {
                return this.entry.content.attributes;
            },
            changedAttributesUI: function() {
                if (!this.changedAttributes()) { return false; }
                var uiRegex = this.uiAttrsRegex,
                    uiAttrs = _.chain(this.changedAttributes())
                        .reduce(function(memo, value, key) {
                            if (uiRegex.test(key)) { memo[key] = value; }
                            return memo;
                        }, {})
                        .value();

                return uiAttrs;
            },
            parse: function() {
                this._parsing = true;
                var response = SplunkDBaseModel.prototype.parse.apply(this, arguments);
                this._parsing = false;
                return response;
            },
            deleteMetricTranform: function(schemaName, sourcetypeModel) {
                this.set({'id': '/services/' + this.url + '/' + encodeURIComponent(schemaName)});
                this.destroy().done(function() {
                    this.unset('id');
                    if (sourcetypeModel) {
                        sourcetypeModel.unset('ui.metric_transforms.schema_name');
                    }
                }.bind(this));
            },
            sanitizeAttributes: function() {
                var validAttributes = [
                    'blacklist_dimensions',
                    'field_names',
                    'name',
                    'sourcetype_name',
                    'id'
                ];
                _.each(this.attributes, function(value, key) {
                    if (_.indexOf(validAttributes, key) < 0) {
                        this.unset(key);
                    } else if (key === 'blacklist_dimensions' || key === 'field_names') {
                        this.set(key, value.replace(/[^\S ]+/g, ' '));
                    }
                }.bind(this));
            },
            // override save to abstract away logic from model consumer in case
            save: function(key, val, options) {
                // Handle both `"key", value` and `{key: value}` -style arguments.
                if (key == null || typeof key === 'object') {
                    options = val;
                }

                var sourcetypeModel = options.sourcetypeModel;
                var sourcetypeName = sourcetypeModel.entry.get('name');
                this.set('sourcetype_name', sourcetypeName);

                if (_.isUndefined(this.get('field_names'))) {
                    this.set({'field_names':''});
                }
                if (_.isUndefined(this.get('blacklist_dimensions'))) {
                    this.set({'blacklist_dimensions':''});
                }
                var savedSchemaName = sourcetypeModel.get('ui.metric_transforms.schema_name');
                if (_.isEmpty(savedSchemaName)) {
                    var schemaName = sourcetypeName + '_' + Date.now();
                    this.set({'name':schemaName});
                } else {
                    var parsedSchemaName = savedSchemaName.split('metric-schema:')[1];
                    var newId = this.url + '/' + encodeURIComponent(parsedSchemaName);
                    this.set({'id': newId});
                }

                this.sanitizeAttributes();

                // call backbone model save with same arguments
                return SplunkDBaseModel.prototype.save.apply(this, arguments);
            },
            sync: function(method, model, options) {
                // override only create/update sync methods of SplunkDBaseModel
                // in order to circumvent whitelisting which is unnecessary for Sourcetype
                model.unset('sourcetype_name');
                switch (method) {
                    case 'create':
                        return syncCreate.call(this, model, options);
                    case 'update':
                        return syncUpdate.call(this, model, options);
                    default:
                        return SplunkDBaseModel.prototype.sync.apply(this, arguments);
                }
            },
            _onerror: function(collection, response, options) {
                // Remove 'In handler' prefix from server messages
                var messages = splunkdUtils.xhrErrorResponseParser(response, this.id);
                _.each(messages, function(msgObj) {
                    var msg = msgObj.message;
                    if (msg) {
                        var res = msg.match(/with name=(.+)\salready exists/);
                        if (res) {
                            msgObj.message = splunkUtils.sprintf(_('Schema name "%s" already exists. Please provide a unique name.').t(), res[1], res[1]);
                        }
                    }
                });
                this.trigger('serverValidated', false, this, messages);
            }
        });
    }
);
