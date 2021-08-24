/*
 * This view is intended to be the only consumption point for rendering a visualization based on a report.
 *
 * The report visualizer is responsible for internally translating a report configuration to a particular
 * visualization, which involves the following things:
 *
 * 1. Preparing and rendering that visualization as a child view of the report visualizer.
 * 2. If enabled, setting the correct height for the visualization and providing height
 *    adjustment controls.
 * 3. Create data sources (helpers/search/DataSource) and make them available to comsumers.
 *
 * Data sources are created base on the definition from visualizations.conf.
 * It is the responsibility of the consumer to send latest results to corrsponding data sources by
 *
 * 1. Connecting data source with search job or search manager.
 * 2. Setting search result viz setSearchResults method.
 *
 * Additionally, the consumer is responsible for updating fetch params of each data source if it's changed externally.
 *
 * If a change in the report means that a new visualization should be displayed, the report visualizer will
 * internally destroy the previous visualization and replace it with the new one.  In this case, new instances
 * of the `DataSource` will be created, and a "dataSourcesChange" event will be fired.
 *
 * The consumer is expected to listen for this event and update any references it has for
 * the data sources
 *
 * Any events triggered by the visualization child view will be re-broadcasted unchanged
 * by the report visualizer.
 */

define([
            'debug',
            'jquery',
            'underscore',
            'module',
            'views/Base',
            'views/shared/LazyView',
            'views/shared/viz/Controller',
            'util/console',
            'util/env',
            'splunk.util',
            'helpers/VisualizationRegistry',
            'jquery.ui.resizable',
            'jquery.resize',
            'helpers/Printer',
            'helpers/VisualizationDataParams',
            'helpers/search/DataSource',
            'mixins/DataSourceMixin',
            'models/config'
        ],
        function(
            debugModule,
            $,
            _,
            module,
            BaseView,
            LazyView,
            VizControllerViewModule,
            console,
            env,
            splunkUtils,
            VisualizationRegistry,
            jqueryUIResizable,
            jqueryResize,
            Printer,
            VisualizationDataParams,
            DataSource,
            DataSourceMixin,
            ConfigModel
        ) {

    var debug = env.DEBUG ? debugModule('ReportVisualizer') : $.noop;
    var VizControllerView = VizControllerViewModule['default'];

    return BaseView.extend(_.extend({}, DataSourceMixin, {

        moduleId: module.id,

        omitFromChildOptions: ['el', 'allowResize', 'width', 'height'],

        /**
         *
         * @param options {
         *     model: {
         *         config: a model representing the content of the current report
         *         application: the application model
         *     }
         *     generalTypeOverride {String} a general type to use instead of whatever is
         *         in the config model's "display.general.type" when determining which
         *         visualization to use for the report
         *     customConfigOverride {Object} a dictionary of key-value pairs to override
         *         whatever is in the config model when determining which visualization to
         *         use for the report
         *     sizeConfigOverride {Object} a dictionary of key-value pairs to override
         *          the default size configuration of a visualization
         *     allowResize {Boolean} whether to render resize controls for the visualization,
         *         if the visualization also has resizing enabled, defaults to false
         *     saveOnResize {Boolean} if enabled, save() is called on the report model after the
         *         resized the visualization. This option is only used for the dashboard editor
         *         to communicate user-driven changes.
         *     ignoreConfigHeight {Boolean} whether to ignore the height value read from the config model,
         *         if true, the height passed to the constructor is used instead
         *     autoHideResizeBar {Boolean} whether the resize bar should automatically hide itself when
         *         the mouse is not over the visualization, defaults to true
         *     width {Number | String} a custom width for the visualization, can be any valid input
         *         to jQuery's width() method, default is 100%
         *     height {Number | String} a custom height for the visualization, can be any valid input
         *         to jQuery's height() method, default is to use the visualization's height attribute
         *         to determine the height from the config model, or 100% if that is not defined
         * }
         */

        initialize: function(options) {
            BaseView.prototype.initialize.apply(this, arguments);
            this.rendered = false;
            this.loaded = false;
            this.$el.width(this.options.width || '100%');
            this.$el.height(this.options.height || '100%');
            this.$resizeHandle = $('<div />').addClass('ui-resizable-handle ui-resizable-s');
            this.activate();
        },

        prepareForBrowserPrint: function() {
            this.listenToOnce(Printer, Printer.PRINT_END, this.restoreAfterBrowserPrint);
            if (this.children.viz && this.children.viz.isInFacetMode && this.children.viz.isInFacetMode()) {
                this.containerHeightBeforePrint = this.$el.height();
                this.children.viz.prepareForBrowserPrint();
                this.$el.height(this.children.viz.getPrintContainerHeight());
                this.invalidateReflow();
            }
        },

        restoreAfterBrowserPrint: function() {
            this.listenToOnce(Printer, Printer.PRINT_START, this.prepareForBrowserPrint);
            if (this.children.viz && this.children.viz.isInFacetMode && this.children.viz.isInFacetMode()) {
                this.children.viz.restoreAfterBrowserPrint();
                this.$el.height(this.containerHeightBeforePrint);
                this.invalidateReflow();
            }
        },

        setAllowResize: function(isAllowed) {
            this.options.allowResize = isAllowed;
            if (isAllowed && this.activeVizConfig) {
                this._setupResizing(this.activeVizConfig.size || {});
            } else {
                this._teardownResizing();
            }
        },

        render: function() {
            if (this.children.viz) {
                this.children.viz.render();
            }
            this.rendered = true;
            return this;
        },

        reflow: function() {
            if (this.children.viz) {
                this.children.viz.invalidateReflow();
            }
        },

        remove: function() {
            BaseView.prototype.remove.apply(this, arguments);
            this.rendered = false;
            this.$el.off('elementResize');
            this._removeDataSources();
            return this;
        },

        show: function() {
            // TODO: SPL-124312, we should remove the opacity setting here and find a better way to hide SVG.
            this.$el.css({ visibility: '', opacity: '' });
            if (this.options.allowResize && this.activeVizConfig) {
                this._setupResizing(this.activeVizConfig.size || {});
            }
        },

        hide: function() {
            // TODO: SPL-124312, we should remove the opacity setting here and find a better way to hide SVG.
            this.$el.css({ visibility: 'hidden', opacity: 0 });
            this._teardownResizing();
        },

        clear: function() {
            _(this.getAllDataSources()).invoke('clearSearchResults');
        },

        load: function() {
            this._load();
            this.loaded = true;
            return this;
        },

        activate: function() {
            if (this.active) {
                return BaseView.prototype.activate.apply(this, arguments);
            }
            BaseView.prototype.activate.apply(this, arguments);
            this._updateToMatchConfig();
            return this;
        },

        deactivate: function(options) {
            if (!this.active) {
                return BaseView.prototype.deactivate.apply(this, arguments);
            }
            BaseView.prototype.deactivate.apply(this, arguments);
            this.$el.off('elementResize');

            return this;
        },

        expandRow: function(rowIndex) {
            this.children.viz.callChildFunction('expandRow', rowIndex);
        },

        collapseRow: function() {
            this.children.viz.callChildFunction('collapseRow');
        },

        startListening: function() {
            this.listenTo(this.model.config, 'change', function() {
                this._updateToMatchConfig();
            });
            if (this.children.viz) {
                this.listenTo(this.children.viz, 'all', this.trigger);
                this.listenTo(this.children.viz, 'error', this._displayRenderErrorMessage);
                this.listenTo(this.children.viz, 'hideMessages', this._hideMessages);
            }
            this.$el.on('elementResize', _(this.invalidateReflow).bind(this));

            this.listenToOnce(Printer, Printer.PRINT_START, this.prepareForBrowserPrint);
        },

        suppressExternalMessage: function() {
            return this.$('.visualization-message').length > 0;
        },

        _load: function() {
            if (this.children.viz) {
                this.listenToOnce(this.children.viz, 'loadFailed', this._displayLoadErrorMessage);
                this.children.viz.load();
            }
        },

        _updateToMatchConfig: function() {
            if (!this.active) {
                return;
            }
            var oldVizConfig = this.activeVizConfig;
            this.activeVizConfig = VisualizationRegistry.findVisualizationForConfig(
                this.model.config.toJSON(),
                this.options.generalTypeOverride,
                this.options.customConfigOverride
            );
            if (this.options.sizeConfigOverride && this.activeVizConfig) {
                this.activeVizConfig.size = _.extend(this.activeVizConfig.size, this.options.sizeConfigOverride);
            }
            this._updateSizing(this.activeVizConfig, oldVizConfig);
            this._updateVizChild(this.activeVizConfig, oldVizConfig);
        },

        _updateVizChild: function(newVizConfig, oldVizConfig) {
            debug('_updateVizChild', 'newVizConfig', newVizConfig, 'oldVizConfig', oldVizConfig);

            if (!newVizConfig) {
                this._removeVizChild();
                this._removeDataSources();
                this.trigger('dataSourcesChange');
                this._displayNoMatchMessage();
                return;
            }

            if (oldVizConfig &&
                oldVizConfig.factory === newVizConfig.factory &&
                oldVizConfig.id === newVizConfig.id) {
                return;
            }

            this._createVizChild(newVizConfig);
        },

        _createVizChild: function (newVizConfig) {
            debug('_createVizChild', 'config', newVizConfig);
            var dataParamsGlobalConfig = _.pick(ConfigModel.toJSON(), 'JSCHART_RESULTS_LIMIT', 'CHOROPLETH_SHAPE_LIMIT');
            this._removeDataSources();
            this._createDataSources(newVizConfig, dataParamsGlobalConfig);
            this.trigger('dataSourcesChange');
            this._removeVizChild();

            this.children.viz = new VizControllerView(
                $.extend(
                    true,
                    {},
                    _(this.options).omit(this.omitFromChildOptions),
                    {
                        id: newVizConfig.id,
                        factory: newVizConfig.factory,
                        width: '100%',
                        height: '100%',
                        isSplittable: newVizConfig.isSplittable,
                        size: newVizConfig.size,
                        supports: newVizConfig.supports,
                        vizConfig: newVizConfig.config,
                        dataParamsGlobalConfig: dataParamsGlobalConfig,
                        dataSources: this.dataSources
                    }
                )
            );

            this.listenTo(this.children.viz, 'all', this.trigger);
            this.listenTo(this.children.viz, 'error', this._displayRenderErrorMessage);
            this.listenTo(this.children.viz, 'hideMessages', this._hideMessages);

            if (this.awake) {
                this.children.viz.wake();
            }
            else {
                this.children.viz.sleep();
            }
            if (this.active) {
                this.children.viz.activate();
            } else {
                this.children.viz.deactivate();
            }
            if (this.rendered) {
                this.children.viz.render();
            }

            this.$('.visualization-message').remove();
            this.children.viz.appendTo(this.el);

            if (this.loaded) {
                this._load();
            }
        },

        _removeVizChild: function() {
            if (this.children.viz) {
                this.stopListening(this.children.viz);
                this.children.viz.deactivate({ deep: true }).remove();
                delete this.children.viz;
            }
        },

        _createDataSources: function(newVizConfig, dataParamsGlobalConfig) {
            var sourceTypes = VisualizationDataParams.getDataSourceTypes(newVizConfig.config || {});
            this.dataSources = _(sourceTypes).map(function(type) {
                var fetchParams = {};
                if (!VisualizationDataParams.needsRuntimeConfig(newVizConfig.config)) {
                    // runtime config will be provided by views/shared/viz/Controller.es or concrete visualizations such as maps
                    fetchParams = VisualizationDataParams.generateDataSourceParams(type, newVizConfig.config, this.model.config.toJSON(), dataParamsGlobalConfig);
                }
                return new DataSource(type, fetchParams);
            }, this);
        },

        _removeDataSources: function() {
            _(this.getAllDataSources()).invoke('dispose');
            this.dataSources = null;
        },

        _updateSizing: function(newVizConfig, oldVizConfig) {
            var unbindHeightListener = _(function() {
                if(oldVizConfig && oldVizConfig.size && oldVizConfig.size.heightAttribute) {
                    this.stopListening(this.model.config, 'change:' + oldVizConfig.size.heightAttribute);
                }
            }).bind(this);

            // If the new viz config is empty, tear it all down and bail.
            if (!newVizConfig) {
                this._teardownResizing();
                unbindHeightListener();
                return;
            }

            // Make sure the current height matches the value of the height attribute in the config.
            // This should be done even if the viz config did not change, because the height attribute
            // could have changed in the config while the view was deactivated.
            var sizeConfig = newVizConfig.size || {};
            unbindHeightListener();
            if (sizeConfig.heightAttribute && !this.options.ignoreConfigHeight) {
                var height;
                var configHeight = parseInt(this.model.config.get(sizeConfig.heightAttribute), 10);
                if (this.children.viz && this.children.viz.isInFacetMode && this.children.viz.isInFacetMode()) {
                    // if the user changed height ( height != defaultHeight ), use that, otherwise use the defaultTrellisHeight
                    if ((configHeight !== sizeConfig.defaultHeight) && !isNaN(configHeight)){
                        height = configHeight;
                    } else {
                        height = sizeConfig.defaultTrellisHeight;
                    }
                } else {
                    height = configHeight || sizeConfig.defaultHeight || 0;
                }
                height = this._enforceMinMaxHeight(height, sizeConfig);
                this.$el.height(height);
                this.listenTo(this.model.config, 'change:' + sizeConfig.heightAttribute, function(model, value) {
                    this._resizeToNewHeight(this._enforceMinMaxHeight(value, sizeConfig));
                });
            } else {
                this.$el.height(this.options.height || '100%');
            }
            // Finally, make sure the state of the resizability matches what's in the viz config and the
            // constructor options.  This can safely be ignored if the viz config did not change.
            if (oldVizConfig && _.isEqual(oldVizConfig.size, newVizConfig.size)) {
                return;
            }
            if (sizeConfig.resizable && this.options.allowResize) {
                this._setupResizing(sizeConfig);
            } else {
                this._teardownResizing();
            }
        },

        _teardownResizing: function() {
            this.$el.css({ overflow: '' });
            this.$resizeHandle.detach();
            if (this.resizablePluginInitialized) {
                this.$el.resizable('destroy');
            }
            this.resizablePluginInitialized = false;
        },

        _setupResizing: function(sizeConfig) {
            this.$el.css({ overflow: 'hidden' });
            this.$resizeHandle.appendTo(this.$el);
            this.$el.resizable({
                autoHide: this.options.autoHideResizeBar !== false,
                handles: { s: this.$resizeHandle },
                maxHeight: sizeConfig.maxHeight || null,
                minHeight: sizeConfig.minHeight || 0,
                stop: _(function() {
                    var sizeConfig = this.activeVizConfig.size,
                        newHeight = this._enforceMinMaxHeight(this.$el.height(), sizeConfig);
                    this.model.config.set(sizeConfig.heightAttribute, String(newHeight));

                    this._resizeToNewHeight(newHeight);
                    if (this.options.saveOnResize) {
                        this.model.config.save();
                    }
                }).bind(this)
            });
            this.resizablePluginInitialized = true;
        },

        _resizeToNewHeight: function(height) {
            this.$el.height(height);
            if (this.children.viz) {
                this.children.viz.$el.height(height);
                this.children.viz.invalidateReflow();
            }
        },

        _enforceMinMaxHeight: function(height, sizeConfig) {
            if (_.isNaN(height)) {
                return sizeConfig.minHeight || 0;
            }
            height = Math.min(height, (sizeConfig.maxHeight || Infinity));
            height = Math.max(height, (sizeConfig.minHeight || 0));
            return height;
        },

        _displayNoMatchMessage: function() {
            if (this.model.config.get('display.visualizations.type') === 'custom') {
                if (this.model.config.get('display.visualizations.custom.type')) {
                    var customType = this.model.config.get('display.visualizations.custom.type');
                    var appAndViz = customType.split('.');
                    this._displayMessage(splunkUtils.sprintf(
                        _('No matching visualization found for type: %s, in app: %s').t(),
                        appAndViz[1], appAndViz[0]
                    ));
                }
                else {
                    this._displayMessage(_('Could not add a custom visualization as \"display.visualizations.custom.type\" is missing in ui-prefs.conf.').t());
                    console.warn('Could not add a custom visualization as \"display.visualizations.custom.type\" is missing in ui-prefs.conf.');
                }
            } else {
                console.error(
                    'ReportVisualizer failed to find a matching visualization for a built-in type, ' +
                    'this should not happen.'
                );
                this._displayMessage(_('No matching visualization found.').t());
            }
        },

        _displayLoadErrorMessage: function() {
            this._displayMessage(splunkUtils.sprintf(
                _('Failed to load source for %s visualization.').t(),
                this._getCurrentVizDisplayName()
            ));
        },

        _displayRenderErrorMessage: function(errorMessage) {
            var displayMessage;
            if (errorMessage ) {
                displayMessage = splunkUtils.sprintf(
                    _('Error rendering %s visualization: %s').t(),
                    this._getCurrentVizDisplayName(),
                    errorMessage
                );
            } else {
                displayMessage = splunkUtils.sprintf(
                    _('Error rendering %s visualization.').t(),
                    this._getCurrentVizDisplayName()
                );
            }
            this._displayMessage(displayMessage);
        },

        _displayMessage: function(message, type) {
            if (this.children.viz) {
                this.children.viz.$el.hide();
            }
            this.$('.visualization-message').remove();
            var $message = _(this._messageTemplate).template({
                message: message,
                type: type || 'error'
            });
            this.$el.append($message);
            this.trigger('message');
        },

        _hideMessages: function() {
            this.$('.visualization-message').remove();
            if (this.children.viz) {
                this.children.viz.$el.show();
            }
        },

        _getCurrentVizDisplayName: function() {
            if (!this.activeVizConfig) {
                return '';
            }
            return this.activeVizConfig.label || this._getCurrentVizIdString();
        },

        _getCurrentVizIdString: function() {
            if (!this.activeVizConfig) {
                return '';
            }
            if (this.activeVizConfig['display.visualizations.type'] === 'custom') {
                return this.activeVizConfig['display.visualizations.custom.type'];
            }
            return this.activeVizConfig.id || '';
        },

        _messageTemplate: '\
            <div class="visualization-message">\
                <div class="alert alert-<%- type %>">\
                    <i class="icon-alert"></i>\
                    <%- message %>\
                </div>\
            </div>\
        '

    }),
    {
        GENERAL_TYPES: {
            VISUALIZATIONS: 'visualizations',
            STATISTICS: 'statistics',
            EVENTS: 'events'
        }
    });

});
