/**
 * @author lbudchenko
 * @date 10/25/15
 *
 * Grid component of listing page
 */
define([
        'jquery',
        'underscore',
        'module',
        'views/shared/basemanager/Grid'
    ],
    function(
        $,
        _,
        module,
        BaseView
    ){
        return BaseView.extend({
            moduleId: module.id,
            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);

                this.columns = [
                    {
                        id: 'name',
                        title: _('Name').t()
                    }, {
                        id: 'eai:acl.app',
                        title: _('App').t(),
                        visible: function() {
                            return this.model.user.canUseApps();
                        }.bind(this)
                    }, {
                        id: 'currentDBSizeMB',
                        title: _('Current Size').t(),
                         visible: function() {
                            return this.model.controller.get('mode') === 'local';
                        }.bind(this)
                    }, {
                        id: 'totalRawSizeMB',
                        title: _('Current Size').t(),
                        tooltip: _('This column shows the current amount of raw data (uncompressed) that is stored in the index. Information may be delayed as it is only updated on an hourly basis, by default.').t(),
                        visible: function() {
                            return this.model.controller.get('mode') === 'cloud';
                        }.bind(this)
                    }, {
                        id: 'maxGlobalRawDataSizeMB',
                        title: _('Max Size').t(),
                        tooltip: _('This column shows the maximum amount of raw data (uncompressed) that can be stored in the index.').t(),
                        visible: function() {
                            return this.model.controller.get('mode') === 'local' || this.collection.appLocals.isArchiverAppInstalled();
                        }.bind(this)
                    }, {
                        id: 'maxTotalDataSizeMB',
                        title: _('Max Size').t(),
                        tooltip: _('This column shows the maximum amount of data that can be stored in the index.').t(),
                        visible: function() {
                            return this.model.controller.get('singleInstance') && !this.collection.appLocals.isArchiverAppInstalled();
                        }.bind(this)
                    }, {
                        id: 'totalEventCount',
                        title: _('Event Count').t()
                    }, {
                        id: 'minTime',
                        title: _('Earliest Event').t()
                    }, {
                        id: 'maxTime',
                        title: _('Latest Event').t()
                    }, {
                        id: 'homePath',
                        title: _('Home Path').t(),
                        visible: function() {
                            return this.model.controller.get('mode') === 'local';
                        }.bind(this)
                    }, {
                        id: 'coldToFrozenDir',
                        title: _('Frozen Path').t(),
                        visible: function() {
                            return this.model.controller.get('mode') === 'local';
                        }.bind(this)
                    }, {
                        id: 'frozenTimePeriodInSecs',
                        title: _('Searchable Retention').t(),
                        visible: function() {
                            return (this.model.controller.get('mode') === 'cloud');
                        }.bind(this)
                    }, {
                        id: 'archiver.selfStorageBucket',
                        title: _('Self Storage Location').t(),
                        visible: function() {
                            return ((this.model.controller.get('mode') === 'cloud') && this.collection.appLocalsUnfilteredAll.findByEntryName('dynamic-data-self-storage-app'));
                        }.bind(this)
                    }, {
                        id: 'archive.provider',
                        title: _('Archive Destination').t(),
                        visible: function() {
                            return ((this.model.controller.get('mode') === 'cloud') && this.model.user.canViewArchives());
                        }.bind(this)
                    }, {
                        id: 'disabled',
                        title: _('Status').t()
                    }
                ];
            }

        });
    });
