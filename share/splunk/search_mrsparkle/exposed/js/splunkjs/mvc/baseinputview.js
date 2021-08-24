define(function(require, exports, module) {
    var _ = require('underscore');
    var $ = require('jquery');
    var SimpleSplunkView = require("./simplesplunkview");
    var BackboneMessages = require('./messages');
    var Message = require('./components/Message');
    var ReactDOM = require('react-dom');
    var React = require('react');
    var getReactUITheme = require('util/theme_utils').getReactUITheme;
    var ThemeProvider = require('util/theme_utils').ThemeProvider;

    /**
     * @constructor
     * @memberOf splunkjs.mvc
     * @name BaseInputView
     * @description The **BaseInputView** base input class is used for Splunk
     * form inputs. This class is not designed to be instantiated directly.
     * @extends splunkjs.mvc.SimpleSplunkView
    */
    var BaseInputView = SimpleSplunkView.extend(/** @lends splunkjs.mvc.BaseInputView.prototype */{

        output_mode: 'json',

        options: {
            disabled: false,
            managerid: null,
            data: "preview"
        },

        initialize: function(options) {
            SimpleSplunkView.prototype.initialize.apply(this, arguments);

            // The 'value' setting is always pushed
            this.settings.enablePush("value");

            // Handle the 'default' and 'initialValue' settings
            this._onDefaultChange();

            this.createSearchReadyDfd();

            this.listenTo(this.settings, 'change', this.render);
            this.listenTo(this.settings, 'change:value', this._onValueChange);
            this.listenTo(this.settings, 'change:default', this._onDefaultChange);

            // Trigger a ready event when the input finished loading.
            // NOTE: do not delete, splunk dashboard engine relies on this event.
            this._onReady(_.bind(this.trigger, this, 'ready'));
        },

        createSearchReadyDfd: function() {
            this._readyDfd = $.Deferred();

            // this._readyDfd is to indicate whether the input view is ready when dashboard is initially
            // loaded. If the input view doesn't have search manager, it is immediately ready; otherwise,
            // it will be ready when the search is done/failed/cancelled etc.
            // NOTE: it doesn't matter if user adds a search manager later, the input view will always be
            // ready.
            if (!this.settings.get('managerid')) {
                this._readyDfd.resolve();
            }
        },

        _onReady: function(cb) {
            // Returns a promise which is fulfilled as soon as the input is ready
            // This is typically the case when search-based choices are loaded
            // For inputs that do not need to load data, the promise is resolved immediately
            if (cb) {
                this._readyDfd.always(cb);
            }
            return this._readyDfd.promise();
        },

        onDataChanged: function() {
            var ret = SimpleSplunkView.prototype.onDataChanged.apply(this, arguments);
            // Once we get data from the search manager we signal readiness of the input
            if (this._readyDfd) {
                this._readyDfd.resolve();
            }
            return ret;
        },

        _onDataChanged: function() {
            var r = SimpleSplunkView.prototype._onDataChanged.apply(this, arguments);
            // TODO: this is probably unnecessary.
            this.trigger('datachange');
            return r;
        },

        // do not delete, splunk dashboard engine relies on this method
        _getSelectedData: function() {
            return {
                value: this._getSelectedValue(),
                label: this._getSelectedLabel()
            };
        },

        // do not delete, splunk dashboard engine relies on this method
        _getSelectedValue: function() {
            return this.val();
        },

        // do not delete, splunk dashboard engine relies on this method
        _getSelectedLabel: function(){
            return this.settings.get('selectedLabel');
        },

        _onSearchProgress: function(properties) {
            SimpleSplunkView.prototype._onSearchProgress.apply(this, arguments);
            if (this._readyDfd) {
                var content = properties.content || {};
                var previewCount = content.resultPreviewCount || 0;
                // Signal readiness of the input in case the populating search does not return any results
                if (content.isDone && previewCount === 0) {
                    this._readyDfd.resolve();
                }
            }
        },

        _onSearchError: function() {
            if (this._readyDfd) {
                this._readyDfd.reject();
            }
            SimpleSplunkView.prototype._onSearchError.apply(this, arguments);
        },

        _onSearchFailed: function() {
            if (this._readyDfd) {
                this._readyDfd.reject();
            }
            SimpleSplunkView.prototype._onSearchFailed.apply(this, arguments);
        },

        normalizeValue: function(value) {
            // sub-view can override this method to mathc its value format.
            // for example, basemultichoiceview requires value to be array.
            return value;
        },

        _onDefaultChange: function(model, value, options) {
            var oldDefaultValue = this.settings.previous("default");

            // Initialize value with default, if provided.
            var defaultValue = this.settings.get("default");
            var calledFromConstructor = !model;
            if (defaultValue === undefined && calledFromConstructor) {
                // this is not the best place to handle 'initialValue', but it works, so be it.
                defaultValue = this.settings.get("initialValue") == null ? this.settings.get("seed") : this.settings.get("initialValue");
            }

            var currentValue = this.settings.get('value');
            if (defaultValue !== undefined &&
                (_.isEqual(currentValue, oldDefaultValue) || currentValue === undefined))
            {
                this.settings.set('value', this.normalizeValue(defaultValue));
            }
        },

        _onValueChange: function(model, value, options) {
            this.trigger("change", value, this);
        },

        // this function is to generate a full state object for the rendering logic
        getState: function() {
            return {
                value: this.settings.get('value'),
                disabled: this.settings.get('disabled'),
                onChange: function(value) {
                    this.val(value);
                }.bind(this)
            };
        },

        getReactRoot: function() {
            return this.el;
        },

        // individual views should implement this method
        getReactComponent: function() {
            return null;
        },

        renderReactComponent: function() {
            var component = this.getReactComponent();

            if (!component) {
                return;
            }

            ReactDOM.render(
                React.createElement(ThemeProvider, { theme: getReactUITheme() },
                    React.createElement(component, this.getState())
                ),
                this.getReactRoot()
            );
        },

        remove: function() {
            ReactDOM.unmountComponentAtNode(this.getReactRoot());
            SimpleSplunkView.prototype.remove.apply(this, arguments);
        },

        createView: function() {
            this.renderReactComponent();
            return this.$el;
        },

        updateView: function() {
            // have to manually re-render
            this.renderReactComponent();
        },

        render: function() {
            this._updateView(this._viz, this._data || []);
            return this;
        },

        // Skip the empty data check.  Empty data is acceptable for
        // form objects.
        _updateView: function() {
            var data = this._data || [];

            if (!this._viz) {
                this._createView(data);
            }

            if (!this._viz) {
                return; // Couldn't create the visualization
            }

            this.updateView(this._viz, data);
        },

        /**
         * Override the method in simplesplunkview.js, so that it renders React-based Message,
         * otherwise the Backbone-based message view clashes with the React-based form inputs after
         * upgrading to React v16.
         *
         * However, we still need to keep the old messages.js {Backbone.View} for non-input views.
         *
         * We should consolidate messages.js and Message.jsx eventually.
         */
        displayMessage: function(info) {
            this._viz = null;

            var i = _.isString(info) ? BackboneMessages.messages[info] : info;

            if (!i) {
                return;
            }

            ReactDOM.render(
                React.createElement(ThemeProvider, { theme: getReactUITheme() }, React.createElement(Message, i)),
                this.getReactRoot()
            );
            return this;
        },

        /**
         * Gets the view's value if passed no parameters.
         * Sets the view's value if passed a single parameter.
         * @param {String} value - The value to set.
         * @returns {String}
         */
        val: function(newValue) {
            if (arguments.length === 0) {
                return this.settings.get("value");
            }

            if (newValue !== this.settings.get("value")) {
                this.settings.set('value', newValue);
            }

            return this.settings.get('value');
        },

        // This logic applies what Dashboards expects in order for an input to have a "value" - it is not a generally
        // applicable construct, and should only be used by the Dashboard helpers
        _hasValueForDashboards: function() {
            var value = this.settings.get("value");
            var defaultValue = this.settings.get("default");
            var valueIsDefined = value !== undefined && value !== null;
            return valueIsDefined || defaultValue === undefined || value === defaultValue;
        }
    });

    return BaseInputView;
});
/**
 * Change event.
 *
 * @name splunkjs.mvc.BaseSplunkView#change
 * @event
 * @property {Boolean} change - Fired when the value of the view changes.
 */
