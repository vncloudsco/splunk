/* eslint no-underscore-dangle: ["warn", { "allow": ["_splunk_metrics_events"] }] */
/* eslint no-use-before-define: ["error", { "functions": false }] */

/** @module DashboardMetrics */

import _ from 'underscore';
import Backbone from 'backbone';

/**
 *
 * Send UI metrics data from a dashboard page for instrumentation purposes.
 * This data transmission will only happen on page load, or upon dashboard
 * XML changes.
 *
 * No user data will be sent if 'window._splunk_metrics_events' is not loaded on the page.
 *
 * @param {Object} options - wrapper for model, state, deferreds, and managers objects
 * @property {Object} model
 * @property {Backbone.Model} model.page - autoRun, hideChrome, submitButton, etc.
 * @property {Backbone.Model} model.scheduledView
 * @property {Backbone.Model} model.scheduledView.entry.content - isScheduled, etc.
 * @property {SplunkDBase} model.reportDefaults - default report attributes
 * @property {Backbone.Model} model.committedState
 * @property {Object} model.committedState.structure.settings - isVisible, refresh, etc.
 * @property {Object} state
 * @property {LayoutState} state.layout
 * @property {FieldsetState} state.fieldset
 * @property {ItemStateCollection} state.elements
 * @property {Object.<ElementState>} state.elements._items
 * @property {ItemStateCollection} state.inputs
 * @property {Object.<InputState>} state.inputs._items
 * @property {ItemStateCollection} state.searches
 * @property {Object.<SearchState>} state.searches._items
 * @property {ItemStateCollection} state.panels
 * @property {Object.<PanelState>=} state.panels._items - only available in row column layouts
 * @property {LayoutState} state.layout
 * @property {FieldsetState} state.fieldset
 * @property {Object} deferreds
 * @property {Deferred} deferreds.managers
 * @property {Deferred} deferreds.reportDefaults
 * @property {Deferred} deferreds.scheduledView
 * @property {Deferred} deferreds.componentReady
 * @property {Array.<BaseManager>} managers
 */
export function sendDashboardMetrics({ model, state, deferreds, managers,
  VisualizationRegistry, SearchManager, isValidPivotSearch }) {
    if (_.isUndefined(window._splunk_metrics_events)) {
        return;
    }
    Promise.all(_.values(deferreds)).then(() => {
        const dataPromise = captureDashboardMetrics(model, state, managers,
          VisualizationRegistry, SearchManager, isValidPivotSearch);
        dataPromise.then(data => (
            window._splunk_metrics_events.push({ type: 'dashboard.load', data })
        ));
    });
}

/**
 *
 * Collect UI metrics data from all dashboard pages for instrumentation
 * purposes.
 *
 * @param {Object} model
 * @param {Backbone.Model} model.page - autoRun, hideChrome, submitButton, etc.
 * @param {Backbone.Model} model.scheduledView
 * @property {Backbone.Model} model.scheduledView.entry.content - isScheduled, etc.
 * @param {SplunkDBase} model.reportDefaults - default report attributes
 * @param {Backbone.Model} model.committedState
 * @param {Object} model.committedState.structure.settings - isVisible, refresh, etc.
 * @param {Object} state
 * @param {LayoutState} state.layout
 * @param {FieldsetState} state.fieldset
 * @param {ItemStateCollection} state.elements
 * @param {Object.<ElementState>} state.elements._items
 * @param {ItemStateCollection} state.inputs
 * @param {Object.<InputState>} state.inputs._items
 * @param {ItemStateCollection} state.searches
 * @param {Object.<SearchState>} state.searches._items
 * @param {ItemStateCollection} state.panels
 * @param {Object.<PanelState>=} state.panels._items - only available in row column layouts
 * @param {LayoutState} state.layout
 * @param {FieldsetState} state.fieldset
 * @param {Array.<BaseManager>} managers
 * @return {Promise.<Object>} promise that resolves with the entire metrics data object
 */
export function captureDashboardMetrics(model, state, managers,
    VisualizationRegistry, SearchManager, isValidPivotSearch) {
    const summary = getSummaryAttrs(state);
    const dashboard = getDashboardAttrs(model.committedState, model.page, model.scheduledView, state.fieldset);
    const elementTypeCounts = getElementTypeCounts(state.elements, model.reportDefaults, VisualizationRegistry);
    const formInputTypeCounts = getFormInputTypeCounts(state.inputs);
    const searchManagers = managers.filter(mgr => mgr instanceof SearchManager);
    const searchCountsPromise = getSearchTypeCounts(state.searches, searchManagers, isValidPivotSearch);
    return searchCountsPromise.then(searchTypeCounts => (
        Object.assign({
            searchTypeCounts,
            dashboard,
            elementTypeCounts,
            formInputTypeCounts,
        }, summary)
    ));
}

/**
 * Gather metrics data that resides in a dashboard's XML
 *
 * @param {Backbone.Model} committedState
 * @param {Object} committedState.structure.settings - isVisible, refresh, etc.
 * @param {Backbone.Model} page - autoRun, hideChrome, submitButton, etc.
 * @param {Backbone.Model} scheduledView
 * @property {Backbone.Model} scheduledView.entry.content - isScheduled, etc.
 * @param {FieldsetState} state.fieldset
 * @returns {Object} dashboard attributes (autoRun, submitButton, numCustomJs, etc.)
 */
export function getDashboardAttrs(committedState, page, scheduledView, fieldsetState) {
    const settings = committedState.get('structure').settings || {};
    const isVisible = settings.isVisible || false;
    const refresh = settings.refresh || 0;
    const script = settings.script || [];
    const stylesheet = settings.stylesheet || [];
    const numCustomCss = stylesheet.length;
    const numCustomJs = script.length;
    const theme = settings.theme || 'light';

    const hideAppBar = !!page.get('hideAppBar');
    const hideChrome = !!page.get('hideChrome');
    const hideEdit = !!page.get('hideEdit');
    const hideFilters = !!page.get('hideFilters');
    const hideSplunkBar = !!page.get('hideSplunkBar');
    const hideTitle = !!page.get('hideTitle');
    const hideExport = !!page.get('hideExport');

    const isScheduled = !!scheduledView.entry.content.get('is_scheduled');

    const globalFieldsetState = fieldsetState.getState ? fieldsetState.getState() : {};
    const submitButton = !!globalFieldsetState.submitButton;
    const autoRun = !!globalFieldsetState.autoRun;

    return {
        autoRun,
        hideAppBar,
        hideChrome,
        hideEdit,
        hideFilters,
        hideSplunkBar,
        hideTitle,
        isScheduled,
        isVisible,
        numCustomCss,
        numCustomJs,
        refresh,
        submitButton,
        theme,
        hideExport,
    };
}

/**
 * Get a count of each element type
 *
 * @param {ItemStateCollection} elements
 * @param {Object.<ElementState>} elements._items
 * @param {SplunkDBase} reportDefaults - default report attributes
 * @returns {Object}              key value pairs of element type and count
 */
export function getElementTypeCounts(elements, reportDefaults, VisualizationRegistry) {
    const entry = reportDefaults.entry ? reportDefaults.entry : {};
    const content = entry.content ? entry.content : new Backbone.Model();
    const elementStates = elements.getStates ? elements.getStates() : [];
    const elementTypeIds = elementStates.map((element) => {
        const elementState = element.getState();
        if (elementState.type === 'html') {
            // Since HTML visualizations aren't available in the VisualizationRegistry,
            // we need to handle this case explicitly.
            return 'html';
        }
        const elementReport = Object.assign({}, content.toJSON(), elementState);
        const viz = VisualizationRegistry.findVisualizationForConfig(elementReport);
        return viz ? viz.id : 'unknown';
    });
    return _.countBy(elementTypeIds, id => id);
}

 /**
  * Get a count of each form input type
  *
  * @param {ItemStateCollection} formInputs
  * @param {Object.<InputState>} formInputs._items
  * @returns {Object}               key value pairs of form input type and count
  */
export function getFormInputTypeCounts(formInputs) {
    const formInputStates = formInputs.getStates ? formInputs.getStates() : [];
    return _.countBy(formInputStates, input => input.getState().type);
}

/**
 * Get an overview of a dashboard page's attributes
 *
 * @param {Object} state
 * @param {LayoutState} state.layout
 * @param {ItemStateCollection} state.elements
 * @param {Object.<ElementState>} state.elements._items
 * @param {ItemStateCollection} state.inputs
 * @param {Object.<InputState>} state.inputs._items
 * @param {ItemStateCollection} state.searches
 * @param {Object.<SearchState>} state.searches._items
 * @param {ItemStateCollection} state.panels
 * @param {Object.<PanelState>=} state.panels._items - only available in row column layouts
 * @returns {Object}                top level meta info for a dashboard
 */
export function getSummaryAttrs({ elements, inputs, searches, layout, panels }) {
    const numElements = elements.getStates().length || 0;
    const numFormInputs = inputs.getStates().length || 0;
    const numSearches = searches.getStates().length || 0;
    const layoutType = layout.getState().type || 'row-column-layout';
    const summary = {
        layoutType,
        numElements,
        numFormInputs,
        numSearches,
    };

    // layout dependent attrs
    if (layoutType === 'row-column-layout') {
        const panelStates = panels.getStates();
        const numPanels = panelStates.length;
        const numPrebuiltPanels = panelStates.reduce((acc, panel) => {
            const state = panel.getState();
            const isPrebuiltPanel = state.ref && (state.ref.length > 0);
            return acc + (isPrebuiltPanel ? 1 : 0);
        }, 0);
        summary.numPanels = numPanels;
        summary.numPrebuiltPanels = numPrebuiltPanels;
    }
    return summary;
}

/**
 * Get a count of the different search manager types. 'inline', 'saved',
 * 'postprocess', and 'pivot' search manager types are available in the search state.
 *
 * 'realtime' searches are known after valid search events have been triggered
 * on a search manager, and there is a job response. In the event that no valid
 * search event has been triggered, reject with a reason.
 *
 * A uniform manner to determine whether any search is 'realtime', is to check
 * the job response returned by the backend. While we technically only need to
 * wait for the server response when a search is both 'realtime' AND 'saved',
 * we handle all search managers the same for consistency/simplicity.
 *
 * @param {ItemStateCollection} searches
 * @param {Object.<SearchState>} searches._items
 * @param {Array.<SearchManager>} managers
 * @returns {Promise.<Object>} resolves with an object of search type counts
 *                             (i.e. {inline: 1, saved: 1, realtime: 1, ...})
 */
export function getSearchTypeCounts(searches, managers, isValidPivotSearch) {
    const searchesState = searches.getStates();
    if (_.isEmpty(searchesState) || _.isEmpty(managers)) {
        return Promise.resolve({});
    }
    const typesArray = [];
    searchesState.forEach((item) => {
        const { searchType, search, refresh } = item.getState();
        typesArray.push(searchType);
        if (isValidPivotSearch(search)) {
            typesArray.push('pivot');
        }
        if (refresh) {
            typesArray.push('refresh');
        }
    });
    const searchTypeCounts = _.countBy(typesArray, type => type);
    const rtSearchPromises = managers.map(mgr => makeRTSearchPromise(mgr));
    return Promise.all(rtSearchPromises).then((rtSearchList) => {
        const realtimeCount = rtSearchList.reduce((acc, val) => acc + val, 0);
        if (realtimeCount > 0) {
            searchTypeCounts.realtime = realtimeCount;
        }
        return searchTypeCounts;
    });
}

/**
 *
 * Determine whether a search manager is a realtime search.
 *
 * 'realtime' searches are known after valid search events have been triggered
 * on a search manager, and there is a job response. In the event that no valid
 * search event has been triggered, reject the promise after 10 seconds.
 *
 * @param {Array.<SearchManager>} managers
 * @return {Promise.<Integer>} resolves with a 1 if a realtime search was found,
 *                             otherwise returns 0. The promise will reject upon timeout.
 */
export function makeRTSearchPromise(mgr) {
    const listenerContext = {};
    let timer;
    const promise = new Promise((resolve) => {
        const successCallback = response => (
            resolve(response.content.isRealTimeSearch ? 1 : 0)
        );
        const errorCallback = () => resolve(0);
        mgr.on('search:start search:progress search:done', successCallback, listenerContext);
        mgr.on('search:fail search:error', errorCallback, listenerContext);
        mgr.replayLastSearchEvent(listenerContext);
        timer = setTimeout(() => (
            resolve(0)
        ), 10000);
    });
    const clearListeners = () => {
        mgr.off(null, null, listenerContext);
        clearTimeout(timer);
    };

    promise.then(clearListeners, clearListeners);
    return promise;
}
