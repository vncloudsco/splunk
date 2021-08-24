import _ from 'underscore';
import ModelHelper from 'controllers/dashboard/helpers/ModelHelper';
import AppLocalsCollection from 'collections/services/AppLocals';
import $ from 'jquery';
import {
    LINK_TO_DASHBOARD,
    LINK_TO_CUSTOM_URL,
} from 'dashboard/containers/editor/drilldown/drilldownNames';
import {
    UPDATE_ACTIVE_ACTION,
    FETCH_TIME_RANGE_PRESETS_REQUEST,
    FETCH_TIME_RANGE_PRESETS_SUCCESS,
    FETCH_TIME_RANGE_PRESETS_FAILURE,
    FETCH_APPS_REQUEST,
    FETCH_APPS_SUCCESS,
    FETCH_APPS_FAILURE,
    FETCH_DASHBOARDS_REQUEST,
    FETCH_DASHBOARDS_SUCCESS,
    FETCH_DASHBOARDS_FAILURE,
    FETCH_REPORTS_REQUEST,
    FETCH_REPORTS_SUCCESS,
    FETCH_REPORTS_FAILURE,
} from 'dashboard/containers/editor/drilldown/actionTypes';
import {
    updateLinkToDashboardSetting,
} from 'dashboard/containers/editor/drilldown/dashboard/dashboardActions';

export const updateActiveAction = value =>
    ({ type: UPDATE_ACTIVE_ACTION, value });

const fetchTimeRangePresetsRequest = fetchOptions => ({
    type: FETCH_TIME_RANGE_PRESETS_REQUEST,
    fetchOptions,
});

const fetchTimeRangePresetsSuccess = (timeRangePresets, fetchOptions) => ({
    type: FETCH_TIME_RANGE_PRESETS_SUCCESS,
    timeRangePresets,
    fetchOptions,
});

const fetchTimeRangePresetsFailure = (error, fetchOptions) => ({
    type: FETCH_TIME_RANGE_PRESETS_FAILURE,
    error,
    fetchOptions,
});

export const fetchTimeRangePresets = (options = {}) => (dispatch, getState) => {
    const fetchOptions = _.defaults({}, options, { count: -1 });

    if (getState().timeRangePresets.isFetching) {
        // return $.Deferred to be consistent with what Backbone.Model.fetch() returns
        return (new $.Deferred()).resolve();
    }

    dispatch(fetchTimeRangePresetsRequest(fetchOptions));

    // ideally we should use @splunk/time-range-utils/presets instead of using ModelHelper, because
    // @splunk/time-range-utils is designed for @splunk/react-time-range. But, we have been using
    // ModelHelper in other places in dashboard codebase, it is memoized so we can reduce number of
    // network request (in some cases).
    const timeRangePresetsCollection = ModelHelper.getCachedModel('times', fetchOptions);

    return timeRangePresetsCollection.dfd
        .done(() => {
            const presets = timeRangePresetsCollection
                .filter(model => model.entry.content.get('earliest_time') || model.entry.content.get('latest_time'))
                .map((model) => {
                    const { label, earliest_time, latest_time } = model.entry.content.toJSON();
                    return {
                        label,
                        earliest: earliest_time || '',  // eslint-disable-line camelcase
                        latest: latest_time || '',      // eslint-disable-line camelcase
                    };
                });

            return dispatch(fetchTimeRangePresetsSuccess(
                presets,
                fetchOptions));
        })
        .fail(() => dispatch(fetchTimeRangePresetsFailure('fetch time range presets failed!', fetchOptions)));
};

const fetchAppsRequest = fetchOptions => ({
    type: FETCH_APPS_REQUEST,
    fetchOptions,
});

const fetchAppsSuccess = (collection, fetchOptions) => ({
    type: FETCH_APPS_SUCCESS,
    value: collection,
    fetchOptions,
});

const fetchAppsFailure = (error, fetchOptions) => ({
    type: FETCH_APPS_FAILURE,
    value: error,
    fetchOptions,
});

export const fetchApps = options => (dispatch, getState) => {
    const fetchOptions = _.defaults({}, options);

    fetchOptions.data = _.defaults({}, fetchOptions.data, {
        count: -1,
        sort_key: 'label',
    });

    if (getState().apps.isFetching) {
        return (new $.Deferred()).resolve();
    }

    dispatch(fetchAppsRequest(fetchOptions));

    const appLocalsCollection = new AppLocalsCollection();
    return appLocalsCollection.fetch(fetchOptions).then(
        () => dispatch(fetchAppsSuccess(appLocalsCollection.listWithoutInternals().filter(app => (
            app.entry.content.get('visible')
            && app.entry.content.get('show_in_nav')
            && !app.entry.content.get('disabled')
            && app.entry.get('name') !== 'launcher' // launcher is the Home app
        )).map(app => ({
            label: app.entry.content.get('label'),
            value: app.entry.get('name'),
        })), fetchOptions)),
        () => dispatch(fetchAppsFailure('fetch apps failed', fetchOptions)),
    );
};

const fetchDashboardsRequest = fetchOptions => ({
    type: FETCH_DASHBOARDS_REQUEST,
    fetchOptions,
});

const fetchDashboardsSuccess = (collection, fetchOptions) => ({
    type: FETCH_DASHBOARDS_SUCCESS,
    value: collection,
    fetchOptions,
});

const fetchDashboardsFailure = (error, fetchOptions) => ({
    type: FETCH_DASHBOARDS_FAILURE,
    value: error,
    fetchOptions,
});

export const fetchDashboards = options => (dispatch, getState) => {
    const fetchOptions = _.defaults({}, options, {
        count: -1,
        sort_key: 'label',
        digest: '1',
        // cannot use (eai:data="*<dashboard*" OR eai:data="*<form*") here, because eai:data is not available
        // in digest mode.
        search: '(eai:type="views" OR eai:type="html")',
    });

    if (getState().dashboards.isFetching) {
        return (new $.Deferred().resolve());
    }

    dispatch(fetchDashboardsRequest(fetchOptions));

    const dashboards = ModelHelper.getCachedModel('dashboards', fetchOptions);

    return dashboards.dfd.then(
        () => dispatch(fetchDashboardsSuccess(dashboards.map(app => ({
            label: app.entry.content.get('label'),
            value: app.entry.get('name'),
        })), fetchOptions)),
        () => dispatch(fetchDashboardsFailure('fetch dashboards failed', fetchOptions)),
    );
};

const fetchReportsRequest = fetchOptions => ({
    type: FETCH_REPORTS_REQUEST,
    fetchOptions,
});

const fetchReportsSuccess = (collection, fetchOptions) => ({
    type: FETCH_REPORTS_SUCCESS,
    value: collection,
    fetchOptions,
});

const fetchReportsFailure = (error, fetchOptions) => ({
    type: FETCH_REPORTS_FAILURE,
    value: error,
    fetchOptions,
});

export const fetchReports = options => (dispatch, getState) => {
    const fetchOptions = _.defaults({}, options, {
        count: -1,
        sort_key: 'name',
        search: 'is_visible=1',
    });

    if (getState().reports.isFetching) {
        return (new $.Deferred().resolve());
    }

    dispatch(fetchReportsRequest(fetchOptions));

    const reports = ModelHelper.getCachedModel('reports', Object.assign({}, fetchOptions));

    // NOTE: duck typing, it shouldn't be a problem once jQuery is upgraded to 3.0 because it will
    // be compatible with native Promise.
    return reports.dfd.then(
        () => dispatch(fetchReportsSuccess(reports.map(app => ({
            label: app.entry.get('name'),
            value: app.entry.get('name'),
        })), fetchOptions)),
        () => dispatch(fetchReportsFailure('fetch reports failed', fetchOptions)),
    );
};

export const validateLinkToDashboard = () => (dispatch, getState) => {
    const state = getState();

    if (state.activeAction !== LINK_TO_DASHBOARD) {
        return;
    }

    const activeDashboard = state.forms[LINK_TO_DASHBOARD].activeDashboard;

    // SPL-143638: if activeDashboard is empty string, that means user hasn't selected a dashboard,
    // this is a valid state.
    if (!activeDashboard) {
        return;
    }

    const isDashboardMatched = state.dashboards.items.find(
        dashboard => dashboard.value === activeDashboard);

    if (isDashboardMatched) {
        return;
    }

    // if the activeDashboard does not match any dashboard in the dashboards list, will consider it
    // as a custom url. This happens when an app contains some custom js page, for example, the
    // `datasets` page, or any manager pages.
    dispatch(updateActiveAction(LINK_TO_CUSTOM_URL));
    // reset activeDashboard because it is not a valid dashboard.
    dispatch(updateLinkToDashboardSetting({ activeDashboard: '' }));
};
