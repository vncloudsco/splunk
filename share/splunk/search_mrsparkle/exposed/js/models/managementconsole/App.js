define([
        'jquery',
        'underscore',
        'models/managementconsole/DmcBase',
        'models/managementconsole/Configuration',
        'helpers/managementconsole/url',
        'views/managementconsole/utils/string_utils',
        'util/splunkd_utils',
        'util/time'
    ],
    function(
        $,
        _,
        DmcBaseModel,
        ConfigurationModel,
        urlHelper,
        stringUtils,
        splunkdUtils,
        timeUtil
    ) {
        var STRINGS = {
                NO_VERSION: _('None').t(),
                APP_NULL_LABEL: _('N/A').t()
            },

            INTERNAL_GROUP_NAMES = {
                forwarders: '_forwarders',
                search_heads: '_search_heads',
                indexers: '_indexers'
            };

        var appModel = ConfigurationModel.extend(
            {
                urlRoot: "/services/dmc/apps",
                exportUrlRoot: "/services/dmc/apps-download",
                configureUrlKey: 'app',

                isApp: function() {
                    return true;
                },

                isExternal: function() {
                    return this.entry.content.get('external');
                },

                isPrivate: function() {
                    return this.entry.content.get('private');
                },

                isIndexerOnly: function() {
                    var groups = this.getGroups();
                    return groups.length === 1 && groups[0] === INTERNAL_GROUP_NAMES.indexers;
                },

                isDisabled: function() {
                    return this.entry.content.get('@disabled');
                },

                getPrefix: function() {
                    return _('App').t();
                },

                getBundleName: function() {
                    return this.entry.get('name');
                },

                getType: function() {
                    return 'app';
                },

                getBundleType: function() {
                    return 'app';
                },

                getAppLabel: function() {
                    return this.entry.content.get('@label');
                },

                getVersion: function() {
                    return this.entry.content.get('@version') || STRINGS.NO_VERSION;
                },

                hasUpdate: function() {
                    return !_.isNull(this.entry.content.get('@updateAvailable'));
                },

                canUpdate: function() {
                    return this.getUpdateLink();
                },

                getRemotePath: function() {
                    return this.hasUpdate() ? this.entry.content.get('@updateAvailable').path : null;
                },

                getLicenseName: function() {
                    return this.hasUpdate() ? this.entry.content.get('@updateAvailable').license_name : null;
                },

                getLicenseUrl: function() {
                    return this.hasUpdate() ? this.entry.content.get('@updateAvailable').license_url : null;
                },

                getReleaseNotesURI: function() {
                    return this.entry.get('manifest') ? this.entry.get('manifest').info.releaseNotes.uri : null;
                },

                getPrettyPackageDependenciesString: function() {
                    var dependencies = this.entry.get('manifest') ? this.entry.get('manifest').dependencies : {},
                        dependenciesArr = [];

                    _.each(dependencies, function(val, key) {
                        dependenciesArr.push(val.label + ' (' + val.version + ')');
                    });
                    return _.isEmpty(dependenciesArr) ? '' : dependenciesArr.join(', ');
                },

                getDescription: function() {
                    if (this.entry.get('manifest') && this.entry.get('manifest').info.description) {
                        return this.entry.get('manifest').info.description;
                    } else {
                        return _('No description').t();
                    }
                },

                getTemplate: function() {
                    return this.entry.content.get('template');
                },

                getViewObjectsUrl: function() {
                    return urlHelper.viewObjectsUrl(this.getBundleName());
                },

                getGroups: function() {
                    var groups = this.entry.content.get('groups');
                    return _.filter(groups, function(group) {
                        return group !== INTERNAL_GROUP_NAMES.forwarders;
                    }) || [];
                },

                getInstallLocationLabel: function() {
                    var groupLabels = _.map(this.getGroups(), function(group) {
                        return DmcBaseModel.getInternalGroupDisplayName(group);
                    });

                    return groupLabels.length > 0 ? stringUtils.formatList(groupLabels) : _('N/A').t();
                },

                enable: function() {
                    return this.save({}, {
                        url: splunkdUtils.fullpath(this.getEnableLink()),
                        contentType: 'application/json',
                        data: JSON.stringify({}),
                        parse: false
                    });
                },

                disable: function() {
                    return this.save({}, {
                        url: splunkdUtils.fullpath(this.getDisableLink()),
                        contentType: 'application/json',
                        data: JSON.stringify({}),
                        parse: false
                    });
                },

                install: function() {
                    return this.save({}, {
                        url: splunkdUtils.fullpath("/services/dmc/apps-install"),
                        data: JSON.stringify({
                            // will need to change this later to accept null instead
                            appId: this.entry.content.get('appId'),
                            auth: this.entry.content.get('auth'),
                            installDependencies: this.entry.content.get('installDependencies')
                        }),
                        contentType: 'application/json'
                    });
                },

                uninstall: function() {
                    return ConfigurationModel.prototype.destroy.call(this, {
                        url: splunkdUtils.fullpath("/services/dmc/apps-install/" + this.getId())
                    });
                },

                update: function() {
                    return this.save({}, {
                        url: splunkdUtils.fullpath(this.getUpdateLink()),
                        contentType: 'application/json',
                        data: JSON.stringify({
                            auth: this.entry.content.get('auth')
                        })
                    });
                },

                /**
                 * Need to override because base manager delete confirmation dialog simply calls destroy on model
                 * @returns {*}
                 */
                destroy: function() {
                    return this.uninstall();
                },

                getExportUrl: function() {
                    return [this.getFullUrlRoot(this.exportUrlRoot), encodeURIComponent(this.entry.get('name')) + '.tar.gz'].join('/');
                },

                getDetailFields: function() {
                    return [
                        'version',
                        'afterInstallation'
                    ];
                },

                getEnableLink: function() {
                    return this.getLink('enable');
                },

                getDisableLink: function() {
                    return this.getLink('disable');
                },

                getUpdateLink: function() {
                    return this.getLink('update');
                },

                getLink: function(link) {
                    return this.entry.links.get(link);
                },

                getDeployedBy: function() {
                    return this.entry.content.get('@deployedBy');
                },

                getDeployedOn: function() {
                    return timeUtil.convertToLocalTime(this.entry.content.get('@deployedOn'));
                },

                getLaunchUrl: function() {
                    return urlHelper.appUrl(this.entry.get('name'));
                },

                getSetupUrl: function() {
                    return urlHelper.setupUrl(this.entry.get('name'));
                }
            },
            {
                getLicenseMap: function(dependencies) {
                    var licenseMap = {};
                    _.each(dependencies, function(app) {
                        licenseMap[app.license] = licenseMap[app.license] || { apps: [], license_url: app.license_url };
                        licenseMap[app.license].apps.push(app);
                    });
                    return licenseMap;
                }
            }
        );

        return appModel;
    }
);
