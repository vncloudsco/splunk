define([
    'jquery',
    'underscore',
    'splunkjs/mvc'
], function($,
            _,
            mvc) {

    var EventManagerMixin = {
        setupEventManager: function(options) {
            options || (options = {});
            this._eventManager = null;
            // wait until the eventmanager binds if there's evtmanagerid, otherwise resolve it right away.
            this._eventManagerDfd = this.settings.has('evtmanagerid') ? $.Deferred() : $.Deferred().resolve();
            this.bindToComponentSetting(options.key || 'evtmanagerid', this.onEventManagerChanged, this);
        },
        onEventManagerChanged: function(managers, eventManager) {
            this._eventManager && this._eventManager.unbindComponent();
            this._eventManager = eventManager;
            if (this._eventManager) {
                this._eventManager.bindComponent(this);
                this._eventManagerDfd.resolve();
            }
        },
        onEventManagerReady: function() {
            return this._eventManagerDfd;
        },
        getEventManager: function() {
            return this._eventManager;
        }
    };

    return EventManagerMixin;
});