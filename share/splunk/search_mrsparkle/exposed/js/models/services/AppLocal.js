define(
    [
        'jquery',
        'underscore',
        'backbone',
        'models/SplunkDBase',
        'util/general_utils',
        'util/splunkd_utils',
        'splunk.util'
    ],
    function($, _, Backbone, SplunkDBaseModel, general_utils, splunkd_utils, splunkUtil) {
        var sharingNames = {
            user: _('Private').t(),
            app: _('App').t(),
            global: _('Global').t(),
            system: _('Global').t()
        };

        // private sync method for links
        var syncLink = function(link, model, options) {
            if (!model.entry.links.get(link) && !options.url) {
                throw new Error('URL not provided or ' + link + 'does not exist.');
            }
            var bbXHR,
                deferredResponse = $.Deferred(),
                defaults = {
                    processData: true,
                    type: 'POST',
                    url: splunkd_utils.fullpath(model.entry.links.get(link)),
                    data: {
                        output_mode: 'json'
                    }
                };

            options = options || {};

            $.extend(true, defaults, options);
            defaults.data = splunkd_utils.normalizeValuesForPOST(defaults.data);
            bbXHR = Backbone.sync.call(null, "update", model, defaults);

            bbXHR.done(function() {
                deferredResponse.resolve.apply(deferredResponse, arguments);
            });
            bbXHR.fail(function(response, err, errMsg) {
                model.trigger('error', model, response);
                deferredResponse.reject.apply(deferredResponse, arguments);
            });
            return deferredResponse.promise();
        };

        return SplunkDBaseModel.extend({
            url: "apps/local",
            initialize: function() {
                SplunkDBaseModel.prototype.initialize.apply(this, arguments);
            },
            appAllowsDisable: function() {
                return this.entry.links.get("disable") ? true : false;
            },
            appAllowsEnable: function() {
                return this.entry.links.get('enable') ? true : false;
            },
            isCoreApp: function() {
                return general_utils.normalizeBoolean(this.entry.content.get('core'));
            },
            getSplunkAppsId: function() {
                var details = this.entry.content.get('details');
                if (details) {
                    var idRe = /\/apps\/id\/(.*)/g;
                    var res = idRe.exec(details);
                    if (res.length === 2) {
                        return res[1];
                    }
                }
            },
            isDisabled: function() {
                return this.entry.content.get('disabled');
            },
            getLink: function(name) {
                return this.entry.links.get(name);
            },
            // Using getAppId to match apps remote similar method name
            getAppId: function() {
                return this.entry.get('name');
            },
            // Using getTitle to match apps remote similar method name
            getTitle: function() {
                return this.entry.content.get('label');
            },
            getVersion: function() {
                return this.entry.content.get('version');
            },
            getDetails: function() {
                return this.entry.content.get('details');
            },
            getBuild: function() {
                return this.entry.content.get('build');
            },
            getCheckForUpdates: function() {
                return this.entry.content.get('check_for_updates');
            },
            getVisibility: function() {
                return this.entry.content.get('visible');
            },
            getLabel: function() {
                var id = this.getAppId();
                var name = this.getTitle() || '';
                if (_.isUndefined(id)) {
                    return '';
                } else {
                    return splunkUtil.sprintf('%s (%s)', name, id);
                }
            },
            getValue: function() {
                return this.getAppId();
            },
            getSharingName: function() {
                return sharingNames[this.entry.acl.get('sharing')];
            },
            // Toggles the 'check_for_updates' flag
            toggleUpdateChecking: function() {
                this.entry.content.set('check_for_updates', !this.getCheckForUpdates());
            },
            // Toggles the 'visible' flag
            toggleVisibility: function() {
                this.entry.content.set('visible', !this.getVisibility());
            },
            // returns a promise to disable the app
            disable: function() {
                return syncLink.call(this, 'disable', this, {});
            },
            // returns a promise to enable the app
            enable: function() {
                return syncLink.call(this, 'enable', this, {});
            },
            // returns a boolean that tells if the app can be launched
            canLaunch: function() {
                return !!(!this.isDisabled() && this.getVisibility());
            },
            // returns a boolean that tells if the app can be setup
            canSetup: function() {
                return this.entry.links.get("setup") ? true : false;
            }
        });
    }
);
