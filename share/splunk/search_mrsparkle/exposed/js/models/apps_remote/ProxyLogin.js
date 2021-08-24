define(
    [
        'jquery',
        'underscore',
        'backbone',
        'util/splunkd_utils'
    ],
    function(
        $,
        _,
        Backbone,
        splunkDUtils
    ) {
        /**
         * @constructor
         * @memberOf models
         * @name ProxyLogin
         * @extends Backbone.Model
         *
         * Model to pass in the username / password to splunkbase and get back an authentication token. Functionally, this
         * serves the same purpose as models/apps_remote/Login. However, whereas the Login model is hitting a Python endpoint
         * (which we want to deprecate), this model is hitting the splunkbase proxy endpoint which proxies the request
         * to splunkbase.
         *
         * Usage:
         *      set the following attributes:
         *      username {String} - SplunkBase username
         *      password {String} - SplunkBase password
         *
         *      returns the following structure:
         *      { sbsessionid: "aunqppb9dnlnp2q0ierq9dxptszi5s57"}
         */

        return Backbone.Model.extend(/** @lends models.ProxyLogin.prototype */ {
            url: 'appsbrowser/account:login',

            initialize: function(attributes, options) {
                Backbone.Model.prototype.initialize.apply(this, arguments);
                this.on('error', this._onerror, this);
            },

            _onerror: function(model, response, options) {
                var messages = [];

                if (response.hasOwnProperty('status')) {
                    if (response.status == 403) {
                        messages.push(splunkDUtils.createMessageObject(splunkDUtils.ERROR, _('Incorrect username or password').t()));
                    } else if (response.status == 502) {
                        messages.push(splunkDUtils.createMessageObject(splunkDUtils.ERROR, _('Error connecting to server').t()));

                    }
                }
                this.trigger('serverValidated', false, this, messages);
            },

            sync: function(method, model, options) {
                if ( method!=='create' ) {
                    throw new Error('invalid method: ' + method);
                }
                options = options || {};
                var url = splunkDUtils.fullpath(this.url, {});

                var defaults = {
                    data: {
                        password: model.get('password'),
                        username: model.get('username')
                    },
                    processData: true,
                    type: 'POST',
                    dataType: 'xml',
                    url: url
                };
                $.extend(true, defaults, options);
                return Backbone.sync.call(this, method, model, defaults);
            },

            parse: function(response, options) {
                var responseJSON = {};
                // The response is coming in as XML instead of JSON, so we need to parse the xml
                // Probably overkill to use an xmlToJSON parser. For now, just hardcode the mapping, especially
                // since we only really care about the id attribute.
                // We map the id attribute to sbsessionid because setting it to id makes backbone think the model is
                // an existing model. It then attempts to call sync w/ "update" instead of "create".
                responseJSON.sbsessionid = $(response).find('id').text();

                return responseJSON;
            }

        });
    }
);
