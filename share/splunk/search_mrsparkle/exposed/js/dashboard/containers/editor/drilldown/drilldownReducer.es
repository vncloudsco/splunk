import { combineReducers } from 'redux';

import {
    NO_DRILLDOWN,
    LINK_TO_SEARCH,
    LINK_TO_DASHBOARD,
    LINK_TO_REPORT,
    LINK_TO_CUSTOM_URL,
    EDIT_TOKENS,
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

import linkToDashboard from './dashboard/dashboardReducer';
import linkToSearch from './search/searchReducer';
import linkToReport from './report/reportReducer';
import linkToURL from './url/urlReducer';
import tokens from './tokens/tokensReducer';

const isSupported = (state = true) => state;
const isCustomViz = (state = false) => state;

const activeAction = (state = NO_DRILLDOWN, action) => {
    switch (action.type) {
        case UPDATE_ACTIVE_ACTION:
            return action.value;
        default:
            return state;
    }
};

const apps = (state = {
    isFetching: false,
    fetchOptions: {},
    items: [],
    error: '',
}, action) => {
    switch (action.type) {
        case FETCH_APPS_REQUEST:
            return {
                isFetching: true,
                fetchOptions: action.fetchOptions,
                items: [],
                error: '',
            };
        case FETCH_APPS_SUCCESS:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: action.value,
                error: '',
            };
        case FETCH_APPS_FAILURE:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: [],
                error: action.value,
            };
        default:
            return state;
    }
};

const dashboards = (state = {
    isFetching: false,
    fetchOptions: {},
    items: [],
    error: '',
}, action) => {
    switch (action.type) {
        case FETCH_DASHBOARDS_REQUEST:
            return {
                isFetching: true,
                fetchOptions: action.fetchOptions,
                items: [],
                error: '',
            };
        case FETCH_DASHBOARDS_SUCCESS:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: action.value,
                error: '',
            };
        case FETCH_DASHBOARDS_FAILURE:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: [],
                error: action.value,
            };
        default:
            return state;
    }
};

const reports = (state = {
    isFetching: false,
    fetchOptions: {},
    items: [],
    error: '',
}, action) => {
    switch (action.type) {
        case FETCH_REPORTS_REQUEST:
            return {
                isFetching: true,
                fetchOptions: action.fetchOptions,
                items: [],
                error: '',
            };
        case FETCH_REPORTS_SUCCESS:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: action.value,
                error: '',
            };
        case FETCH_REPORTS_FAILURE:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: [],
                error: action.value,
            };
        default:
            return state;
    }
};

const timeRangePresets = (state = {
    isFetching: false,
    fetchOptions: {},
    items: [],
    error: '',
}, action) => {
    switch (action.type) {
        case FETCH_TIME_RANGE_PRESETS_REQUEST:
            return {
                isFetching: true,
                fetchOptions: action.fetchOptions,
                items: [],
                error: '',
            };
        case FETCH_TIME_RANGE_PRESETS_SUCCESS:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: action.timeRangePresets,
                error: '',
            };
        case FETCH_TIME_RANGE_PRESETS_FAILURE:
            return {
                isFetching: false,
                fetchOptions: action.fetchOptions,
                items: [],
                error: action.error,
            };
        default:
            return state;
    }
};

const splunkEnv = (state = {}) => state;
const elementEnv = (state = {}) => state;

const reducers = combineReducers({
    isSupported,
    isCustomViz,
    activeAction,
    apps,
    dashboards,
    reports,
    forms: combineReducers({
        [LINK_TO_SEARCH]: linkToSearch,
        [LINK_TO_DASHBOARD]: linkToDashboard,
        [LINK_TO_REPORT]: linkToReport,
        [LINK_TO_CUSTOM_URL]: linkToURL,
        [EDIT_TOKENS]: tokens,
    }),
    timeRangePresets,
    elementEnv,
    splunkEnv,
});

export default reducers;
