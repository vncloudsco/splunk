define([
    'jquery',
    'underscore',
    'splunkjs/mvc',
    'splunkjs/mvc/basemanager',
    'splunkjs/mvc/settings',
    'dashboard/DashboardFactory',
    'splunk.util'
], function($,
            _,
            mvc,
            BaseManager,
            Settings,
            DashboardFactory,
            SplunkUtil) {

    var EventManager = BaseManager.extend({
        initialize: function(options) {
            BaseManager.prototype.initialize.apply(this, arguments);
            this.settings = new Settings(_.pick(options, 'events'));
            this.listenTo(this.settings, 'change:events', this.initEventHandlers);
            this.initEventHandlers();
        },
        applySetting: function(newSetting) {
            this.settings.set(newSetting);
        },
        initEventHandlers: function() {
            this.disposeEventHandlers();
            this._eventHandlers = _(this.settings.get('events') || []).map(function(eventDef) {
                return DashboardFactory.getDefault().instantiate(_.extend({
                    id: _.uniqueId(SplunkUtil.sprintf('%s-%s-', this.id, eventDef.type))
                }, eventDef), {});
            }, this);
            this._bindEventHandlers();
        },
        getEventHandlers: function() {
            return this._eventHandlers;
        },
        _bindEventHandlers: function() {
            if (this._component) {
                _(this._eventHandlers).each(function(eventHandler) {
                    eventHandler.settings.set(eventHandler.componentIdSetting, this._component.id);
                }, this);
            }
        },
        _unbindEventHandlers: function() {
            if (this._component) {
                _(this._eventHandlers).each(function(eventHandler) {
                    eventHandler.settings.unset(eventHandler.componentIdSetting);
                }, this);
            }
        },
        bindComponent: function(component) {
            if (component) {
                this._component = component;
                this._bindEventHandlers();
            }
        },
        unbindComponent: function() {
            if (this._component) {
                this._unbindEventHandlers();
                this._component = null;
            }
        },
        disposeEventHandlers: function() {
            this._unbindEventHandlers();
            _(this._eventHandlers).each(function(handler) {
                handler.dispose();
            }, this);
        },
        dispose: function() {
            this.disposeEventHandlers();
            BaseManager.prototype.dispose.apply(this, arguments);
        }
    });
    return EventManager;
});