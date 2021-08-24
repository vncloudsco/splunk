import _ from 'underscore';
import Backbone from 'backbone';
import IntentionsParser from 'models/services/search/IntentionsParser';
import VisualizationRegistry from 'helpers/VisualizationRegistry';
import route from 'uri/route';

/**
 * VizNormalizer generates the visualization attributes required by viz picker includes
 * the recommended flag for a given IntentionsParser
 */
class VizNormalizer {
    /**
     * @constructor
     * @param options {
     *     model: {
     *         application: <models.shared.Application>
     *         intentionsParser: <models.services.search.IntentionsParser>
     *     }
     *     vizTypes (required): [events &| statistics &| visualizations]
     * }
     */
    constructor({ model, vizTypes = [] }) {
        _.extend(this, Backbone.Events);
        this.intentionsParser = model.intentionsParser || new IntentionsParser();
        this.applicationModel = model.application;
        this.vizTypes = vizTypes;
        if (this.vizTypes.length === 0) {
            throw new Error('VizLoader must be instantiated with at least one viz type');
        }
        this.items = [];
        this.listenTo(this.intentionsParser, 'change', this.load);
        this.load();
    }

    load() {
        let reportingCommand = null;
        const reportsSearch = this.intentionsParser.get('reportsSearch');

        if (reportsSearch) {
            reportingCommand = reportsSearch.split(/\s{2,}/g)[0];
            if (this.intentionsParser.has('commands')) {
                const commands = _(this.intentionsParser.get('commands')).pluck('command');
                if (_(commands).contains('predict')) {
                    reportingCommand = 'predict';
                } else if (_(commands).contains('geostats')) {
                    reportingCommand = 'geostats';
                } else if (_(commands).contains('geom')) {
                    reportingCommand = 'geom';
                }
            }
        }
        this.items = _(this.vizTypes).map(vizType => (
            _(VisualizationRegistry.getAllVisualizations([vizType])).chain()
                .where({ isSelectable: true })
                .map((vizConfig) => {
                    let isRecommended;
                    if (vizConfig.id === 'events') {
                        isRecommended = !reportingCommand && (reportsSearch != null);
                    } else {
                        isRecommended = _(vizConfig.recommendFor || []).contains(reportingCommand);
                    }
                    const categories = vizConfig.categories || [];
                    if (isRecommended) {
                        categories.push('recommended');
                    }
                    return ({
                        id: vizConfig.id,
                        label: vizConfig.label,
                        icon: vizConfig.icon,
                        categories,
                        description: vizConfig.description,
                        searchHint: vizConfig.searchHint,
                        thumbnailPath: this.getThumbnailPath(vizConfig),
                    });
                }

                , this)
                .value()), this);
        this.trigger('itemsChange');
    }

    getThumbnailPath(vizConfig) {
        const appBuildNumber = vizConfig.appBuildNumber || null;
        const appName = vizConfig.appName || 'system';
        const directory = vizConfig.vizName;
        const thumbnailName = vizConfig.preview;

        return route.vizIconFile(
            this.applicationModel.get('root'),
            this.applicationModel.get('locale'),
            appBuildNumber,
            appName,
            thumbnailName,
            directory,
        );
    }

    findById(vizId) {
        const vizItem = _.filter(this.listAll(), viz => (
            viz.id === vizId
        ));
        return vizItem[0];
    }

    listAll(options = {
        flatten: true,
    }) {
        let ret = this.items;
        if (options.flatten) {
            ret = _(ret).flatten();
        }
        return ret;
    }
}


export default VizNormalizer;
