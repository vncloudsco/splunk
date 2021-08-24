/*
 * This file represents the central manifest for the "internal modular visualization framework".  It defines
 * a list of built-in visualizations as well as an API for additional visualizations to be registered at runtime.
 *
 * For more details on this project, see: https://confluence.splunk.com/display/PROD/Internal+Mod+Viz+ERD
 *
 * The structure for each entry in the registry should have the following structure:
 *
 * {
 *     id: <String> a unique id for the viz
 *     label: <String> a user-visible label for the viz
 *     icon: <String> the suffix to use for the CSS class of the icon
 *     recommendFor: <Array <String> > a list of search commands that the viz should be recommended for
 *     factory: <View> the view to instantiate when rendering the viz
 *     editorSchema: the schema for the editor controls associated with the viz, a full description
 *         of this schema can be found here:  https://confluence.splunk.com/display/PROD/Internal+Mod+Viz+ERD#InternalModVizERD-VisualizationEditorSchema
 *     pivotSchema: the schema for integrating the viz with the pivot page, a full description of this
 *         schema can be found here:  https://confluence.splunk.com/display/PROD/Internal+Mod+Viz+ERD#InternalModVizERD-PivotEditorSchema
 *     matchConfig: <Object> a dictionary of report attribute key-value pairs, these are used to decide which viz to
 *         use for a given report, as well as what to set on the report when the viz is selected
 *     size: <Object> {
 *         resizable: <Boolean> whether the viz should allow the user to resize it via the UI
 *         minHeight: <Integer> minimum height for the viz
 *         maxHeight: <Integer> maximum height for the viz
 *         heightAttribute: <String> the report attribute name that control's the viz height, this attribute
 *             will be used to calculate the initial height, and will be updated if the viz is resized
 *     }
 * }
 */

define([
    'jquery',
    'underscore',
    'helpers/viz/VisualizationMetadata',
    'helpers/viz/CoreVisualizations',
    'helpers/viz/ExternalVisualizations'
], function($, _, VizMetadata, CoreVisualizations, ExternalVisualizations) {

    var registered = [];
    var overrides = {};

    var VisualizationRegistry = {

        /**
         * Register all visualizations from the given visualizations collection
         *
         * @param options.collection.visualizations {Backbone.Collection}
         * @param options.collection.appLocals {Backbone.Collection}
         *
         * @returns {jQuery.Deferred}
         */
        registerVisualizationsCollection: function(options) {
            return VisualizationRegistry.prepareVizRegistration(options).done(function(regData) {
                regData.forEach(function(viz) {
                    VisualizationRegistry.register(viz);
                });
                VisualizationRegistry.applyAllOverrides();
            });
        },

        registerVisualization: function(vizModel, options) {
            var viz = VizMetadata.getVisualizationMetadata(vizModel);
            viz = VisualizationRegistry.applyTypeSpecificVizConfig(viz, options);
            this.register(viz);
        },

        applyTypeSpecificVizConfig: function(viz, options) {
            var appLocals = options && options.collection && options.collection.appLocals;
            if (viz.isExternal) {
                if (appLocals) {
                    viz.appBuildNumber = ExternalVisualizations.getAppBuildNumber(viz.vizName, viz.appName, appLocals);
                }
                viz.factory = ExternalVisualizations.getFactory(viz);
            } else {
                // Apply preconfigured factory, editorSchema and pivotSchema for core visualizations
                _.extend(viz, CoreVisualizations.getCoreVizConfig(viz.id));
            }
            return viz;
        },

        prepareVizRegistration: function(options) {
            var visualizations = options.collection.visualizations;

            var regData = visualizations
                .map(VizMetadata.getVisualizationMetadata)
                .map(function(viz) {
                    return VisualizationRegistry.applyTypeSpecificVizConfig(viz, options);
                });

            return $.Deferred().resolve(regData).promise();
        },

        // Hook for tests
        reset: function() {
            registered = [];
            overrides = {};
        },

        register: function(vizConfig) {
            if (!vizConfig.id) {
                vizConfig = _.extend({ id: _.uniqueId('registered_viz_') }, vizConfig);
            }
            var duplicateConfig = _(registered).find(function(existingConfig) {
                return _.isEqual(existingConfig.matchConfig, vizConfig.matchConfig);
            });
            if (duplicateConfig) {
                registered = _(registered).without(duplicateConfig);
            }
            registered.unshift(vizConfig);
            return vizConfig;
        },

        isLoaded: function() {
            return registered.length > 0;
        },

        checkLoaded: function() {
            if (!VisualizationRegistry.isLoaded()) {
                throw new Error('VisualizationRegistry has not been populated yet. ' +
                    'Make sure that the visualizations collection is loaded before attempting to use it.');
            }
        },

        applyAllOverrides: function() {
            Object.keys(overrides).forEach(VisualizationRegistry.applyOverride);
        },

        applyOverride: function(id) {
            var overrideContent = overrides[id];
            if (overrideContent) {
                var registeredViz = VisualizationRegistry.getVisualizationById(id);
                if (registeredViz) {
                    _.extend(registeredViz, overrideContent);
                    delete overrides[id];
                    VisualizationRegistry.register(registeredViz);
                }
            }
        },

        registerOverride: function(id, overrideConfig) {
            overrides[id] = overrideConfig;
            if (VisualizationRegistry.isLoaded()) {
                this.applyOverride(id);
            }
        },

        findVisualizationForConfig: function(configJson, generalTypeOverride, customOverride) {
            VisualizationRegistry.checkLoaded();
            configJson = _.extend(
                {},
                configJson,
                generalTypeOverride ? { 'display.general.type': generalTypeOverride } : {},
                customOverride
            );
            return _(registered).find(function(vizConfig) {
                return _.matches(vizConfig.matchConfig)(configJson);
            });
        },

        getAllVisualizations: function(generalTypeWhitelist) {
            VisualizationRegistry.checkLoaded();
            var matches = registered;
            if (generalTypeWhitelist) {
                matches = _(matches).filter(function(vizConfig) {
                    return _(generalTypeWhitelist).contains(vizConfig.matchConfig['display.general.type']);
                });
            }

            // Sort the visualizations such that all built-in ones come first and retain the order they were
            // registered in, and the external ones come after sorted by their label.
            return matches.sort(function(a, b) {
                if (a.order === b.order) {
                    if (a.label === b.label) {
                        return 0;
                    } else {
                        return a.label > b.label ? 1 : -1;
                    }
                } else {
                    return a.order - b.order;
                }
            });
        },

        getVisualizationById: function(id) {
            VisualizationRegistry.checkLoaded();
            return _(registered).findWhere({ id: id });
        },

        getReportSettingsForId: function(id) {
            VisualizationRegistry.checkLoaded();
            var config = this.getVisualizationById(id);
            return config ? config.matchConfig : null;
        },

        getExternalVizBasePath: function(appBuildNumber, appName, vizName){
            return ExternalVisualizations.getBasePath(appBuildNumber, appName, vizName);
        }
    };

    return VisualizationRegistry;

});
