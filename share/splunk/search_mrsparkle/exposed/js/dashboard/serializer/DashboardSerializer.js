define([
    'underscore',
    'jquery',
    'util/general_utils',
    'util/console',
    'util/xml',
    'controllers/dashboard/helpers/ReportModelHelper',
    './RowColumnSerializer',
    './ElementSerializer',
    './SearchSerializer',
    './EventManagerSerializer'
], function(_,
            $,
            GeneralUtils,
            console,
            XML,
            ReportModelHelper,
            RowColumnSerializer,
            ElementSerializer,
            SearchSerializer,
            EventManagerSerializer) {

    /**
     * Add a new report to the current dashboard xml
     * @param reportProperties
     * @param $xml existing dashboard xml
     * @param options
     */
    function addReportToDashboard(reportProperties, $xml, options) {
        options || (options = {});
        _.defaults(options, {tokens: true});

        var $panel = RowColumnSerializer.appendPanelNode($xml, options);

        var extendedReportProps = _.extend(
            {},
            reportProperties,
            ReportModelHelper.getDisabledDrilldownAttribute(reportProperties)
        );
        var $element = ElementSerializer.createElementNodeFromReport(null, extendedReportProps, options);

        var searchSettings = options.searchType === 'saved' ?
            createSavedSearchSettings(options) : createInlineSearchSettings(reportProperties);
        var $search = SearchSerializer.createSearchNodeFromSetting(null, searchSettings, options);

        // put search on top
        $search.prependTo($element);
        $element.appendTo($panel);
        return $xml;
    }

    function createInlineSearchSettings(reportProperties) {
        return {
            searchType: 'inline',
            earliest_time: reportProperties['dispatch.earliest_time'] || undefined,
            latest_time: reportProperties['dispatch.latest_time'] || undefined,
            search: formatSearch(reportProperties['search']),
            sampleRatio: reportProperties['dispatch.sample_ratio']
        };
    }

    function createSavedSearchSettings(options) {
        var settings = {
            searchType: 'saved',
            name: options.searchName
        };

        if (options.overrideTimeRange) {
            _.extend(settings, {
                earliest_time: options.overrideTimeRange.earliest_time,
                latest_time: options.overrideTimeRange.latest_time
            });
        }

        return settings;
    }

    function applyDashboardState(state, xml, options) {
        options = _.extend({
            tokens: true,
            forceDirty: false,
            addGlobalSearches: false
        }, options);

        var $xml = XML.parse(xml);

        $xml = migrateViewType($xml, state.inputs.empty() ? 'dashboard' : 'form');

        if (state.dashboard.isDirty() || options.forceDirty) {
            applyDashboardGlobalState($xml, state.dashboard.getState(), options);
        }

        RowColumnSerializer.applyRowColumnLayout(XML.root($xml), state, _.extend({flagUsedSearchStates: options.addGlobalSearches}, options));
        // handle global search
        if (options.addGlobalSearches) {
            var globalSearches = _(state.searches.getStates()).filter(function(searchState) {
                return !searchState.usedFlag;
            });

            _(globalSearches).each(function(globalSearch) {
                insertGlobalSearchNode($xml, SearchSerializer.createSearchNode(globalSearch, state, options));
            });
        } else {
            moveGlobalSearches($xml);
        }
        // handle init event handler
        var evtManagerId = state.dashboard.getState()['evtmanagerid'];
        if (evtManagerId) {
            EventManagerSerializer.updateEventNodes($xml, state.events.get(evtManagerId), state, options);
        }

        return XML.serializeDashboardXML($xml, true);
    }

    function applyDashboardGlobalState($xml, dashboardState, options) {
        var root = XML.root($xml);
        var newLabel = dashboardState.label;
        var newDescription = dashboardState.description;
        var theme = dashboardState.theme;
        var rootNodeName = root[0].nodeName;
        var labelNode = root.find(rootNodeName + ">label");
        if (!labelNode.length) {
            labelNode = XML.$node("<label/>");
            labelNode.prependTo(root);
        }
        labelNode.text(newLabel);
        var descriptionNode = root.find(rootNodeName + ">description");
        if (!descriptionNode.length) {
            descriptionNode = XML.$node("<description/>");
            descriptionNode.insertAfter(labelNode);
        }
        if (newDescription) {
            descriptionNode.text(newDescription);
        } else {
            descriptionNode.remove();
        }
        var currentTheme = root.attr('theme');
        if (currentTheme == null && theme === 'light') {
            root.removeAttr('theme');
        } else {
            root.attr('theme', theme);
        }
    }

    function moveGlobalSearches($xml) {
        var root = XML.root($xml);
        var searches = root.find('row>panel>search');
        if (searches.length) {
            insertGlobalSearchNode($xml, searches);
        }
    }

    function insertGlobalSearchNode($xml, $globalSearch) {
        XML.inject({
            node: $globalSearch,
            container: XML.root($xml),
            where: 'after',
            selectors: ['description', 'label'],
            fallback: 'prepend'
        });
    }

    /*
     Global dashboard structure
     */

    /**
     * Migrates the root node tag name of the given dashboard XML document.
     *
     * @param $xml the dashboard XML document
     * @param tagName the new root tag name
     * @returns {*} undefined if the document already has the given root node name, otherwise the new XML document
     */
    function migrateViewType($xml, tagName) {
        if (!isViewOfType($xml, tagName)) {
            var curRoot = XML.root($xml);
            var newXML = XML.parse('<' + tagName + '/>');
            var newRoot = XML.root(newXML);
            var cur = curRoot[0];
            _(cur.attributes).each(function(attr) {
                newRoot.attr(attr.nodeName, attr.nodeValue);
            });
            XML.moveChildren(curRoot, newRoot);
            return newXML;
        } else {
            return $xml;
        }
    }

    function isViewOfType($xml, tagName) {
        var curRoot = XML.root($xml);
        return curRoot.prop('tagName') === tagName;
    }

    /**
     * format the query string
     * @param {*} query
     */
    function formatSearch(query) {
        // replace $ with $$
        return (query || '').replace(/\$/gi,"$$$$");
    }

    return {
        addReportToDashboard: addReportToDashboard,
        applyDashboardState: applyDashboardState,
        _createInlineSearchSettings: createInlineSearchSettings,
        _createSavedSearchSettings: createSavedSearchSettings
    };

});
