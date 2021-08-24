import _ from 'underscore';
import $ from 'jquery';
import VisualizationRegistry from 'helpers/VisualizationRegistry';
import SharedModels from 'splunkjs/mvc/sharedmodels';
import VisualizationsCollection from 'collections/services/configs/Visualizations';
import Visualization from 'models/services/configs/Visualization';
import SplunkDsBaseCollection from 'collections/SplunkDsBase';
import VisualizationView from './visualizationview';
// Use this static JSON payload if we can't load the core visualizations from splunkd (Splunk < 7.0)
import legacyCoreVisualizations from './legacy/corevisualizations.json';


export const getVisualizer = (appName, vizName) => {
    if (!appName || !vizName) {
        throw new Error('app name and viz name required for getVisualizer');
    }
    if (!VisualizationRegistry.isLoaded()) {
        throw new Error(
            'The VisualizationRegistry has not been loaded. ' +
            'Make sure the "visualizations" collection in sharedmodels is loaded ' +
            'before retrieving a visualizer.',
        );
    }
    const vizId = `${appName}.${vizName}`;
    const vizConfig = VisualizationRegistry.getVisualizationById(vizId);
    if (!vizConfig) {
        throw new Error(
            `Visualization ${JSON.stringify(vizId)} has not been registered with the system. ` +
            'It may not exist or might not be visible for the current user or app.',
        );
    }
    return VisualizationView.extend({
        initialize(...args) {
            this.options.type = vizId;
            VisualizationView.prototype.initialize.apply(this, args);
        },
    });
};

/**
 * default visualization.conf
 */
const defaultVizConfig = {
    default_height: 250,
    default_width: 250,
    trellis_default_height: 400,
    allow_user_selection: true,
    supports_trellis: false,
    supports_drilldown: false,
    supports_export: false,
    data_sources: 'primary',
    'data_sources.primary.params.show_metadata': true,
};

/**
 * collection that loads custom viz in splunk <= 6.6
 */
const LegacyVisualizations = SplunkDsBaseCollection.extend({
    url: 'configs/conf-visualizations',
    model: Visualization,
});

const legacyLoadCustomViz = () =>
    new Promise((resolve, reject) => {
        SharedModels.load('app').then(() => {
            const visualizations = new LegacyVisualizations();
            visualizations
                .fetch({
                    includeFormatter: false,
                    data: _.extend(
                        {
                            search: Visualization.ENABLED_FILTER,
                            count: 0,
                        },
                        SharedModels.get('app').pick('app', 'owner'),
                    ),
                })
                .then(() => {
                    resolve(visualizations);
                }, reject);
        });
    });

export const loadVisualizations = () => new Promise((resolve, reject) => {
    SharedModels.load('visualizations').then(resolve, () => {
            // failed to load visualizations from visualizations endpoint
            // switch to load custom vizes from conf endpoint
        legacyLoadCustomViz().then((modVizsCollection) => {
            const visualizations = new VisualizationsCollection();
                // set core visualizations
            visualizations.setFromSplunkD(legacyCoreVisualizations);
                // add modvizs
            const modVizs = modVizsCollection.map((modViz) => {
                    // mixin default content
                modViz.entry.content.set(_.defaults(modViz.entry.content.toJSON(), defaultVizConfig));
                return modViz;
            });
            visualizations.add(modVizs);
            SharedModels._prepopulate({ // eslint-disable-line
                visualizations: {
                    model: visualizations,
                    dfd: $.Deferred().resolve(),
                },
            });
            VisualizationRegistry.registerVisualizationsCollection({
                collection: {
                    visualizations,
                    appLocals: SharedModels.get('appLocals'),
                },
            }).then(resolve, reject);
        }, reject);
    });
});
