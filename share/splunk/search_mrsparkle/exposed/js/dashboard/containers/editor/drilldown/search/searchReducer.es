import _ from 'underscore';
import {
    UPDATE_LINK_TO_SEARCH_SETTING,
    PARSE_EARLIEST_REQUEST,
    PARSE_EARLIEST_SUCCESS,
    PARSE_EARLIEST_FAILURE,
    PARSE_LATEST_REQUEST,
    PARSE_LATEST_SUCCESS,
    PARSE_LATEST_FAILURE,
} from 'dashboard/containers/editor/drilldown/actionTypes';
import { EXPLICIT_OPTION } from 'dashboard/containers/editor/drilldown/search/timeRangeOptionNames';

const INITIAL_SEARCH_SETTING = {
    options: [
        {
            label: _('Auto').t(),
            value: 'default',
        },
        {
            label: _('Custom').t(),
            value: 'custom',
        },
    ],
    activeOption: 'default',
    search: '',
    searchError: '',
    target: '',
    isParsingEarliest: false,
    parseEarliest: {},
    isParsingLatest: false,
    parseLatest: {},
    extraTimeRangeOptions: [],
    activeTimeRangeOption: EXPLICIT_OPTION,
    activeTimeRange: {
        earliest: 0,
        latest: '',
    },
    activeTimeRangeToken: {
        earliest: '',
        latest: '',
    },
    earliestTokenError: '',
    latestTokenError: '',
};

const search = (state = INITIAL_SEARCH_SETTING, action) => {
    switch (action.type) {
        case UPDATE_LINK_TO_SEARCH_SETTING:
            return Object.assign({}, state, action.value);
        case PARSE_EARLIEST_REQUEST:
            return Object.assign({}, state, { isParsingEarliest: true, parseEarliest: action.parseEarliest });
        case PARSE_EARLIEST_SUCCESS:
            return Object.assign({}, state, { isParsingEarliest: false, parseEarliest: action.parseEarliest });
        case PARSE_EARLIEST_FAILURE:
            return Object.assign({}, state, { isParsingEarliest: false, parseEarliest: action.parseEarliest });
        case PARSE_LATEST_REQUEST:
            return Object.assign({}, state, { isParsingLatest: true, parseLatest: action.parseLatest });
        case PARSE_LATEST_SUCCESS:
            return Object.assign({}, state, { isParsingLatest: false, parseLatest: action.parseLatest });
        case PARSE_LATEST_FAILURE:
            return Object.assign({}, state, { isParsingLatest: false, parseLatest: action.parseLatest });
        default:
            return state;
    }
};

export default search;
