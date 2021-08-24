import {
    UPDATE_LINK_TO_SEARCH_SETTING,
    PARSE_EARLIEST_REQUEST,
    PARSE_EARLIEST_SUCCESS,
    PARSE_EARLIEST_FAILURE,
    PARSE_LATEST_REQUEST,
    PARSE_LATEST_SUCCESS,
    PARSE_LATEST_FAILURE,
} from 'dashboard/containers/editor/drilldown/actionTypes';
import {
    LINK_TO_SEARCH,
} from 'dashboard/containers/editor/drilldown/drilldownNames';
import { getISO } from '@splunk/time-range-utils/timeParser';

// eslint-disable-next-line import/prefer-default-export
export const updateLinkToSearchSetting = value =>
    ({ type: UPDATE_LINK_TO_SEARCH_SETTING, value });

const parseEarliestRequest = time => ({
    type: PARSE_EARLIEST_REQUEST,
    parseEarliest: {
        time,
    },
});

const parseEarliestSuccess = parseEarliest => ({
    type: PARSE_EARLIEST_SUCCESS,
    parseEarliest,
});

const parseEarliestFailure = parseEarliest => ({
    type: PARSE_EARLIEST_FAILURE,
    parseEarliest,
});

export const parseEarliest = time => (dispatch, getState) => {
    if (getState().forms[LINK_TO_SEARCH].isParsingEarliest) {
        return Promise.resolve();
    }

    dispatch(parseEarliestRequest(time));

    return getISO(time)
        .then(data => dispatch(parseEarliestSuccess(data)))
        .catch(data => dispatch(parseEarliestFailure(data)));
};

const parseLatestRequest = time => ({
    type: PARSE_LATEST_REQUEST,
    parseLatest: {
        time,
    },
});

const parseLatestSuccess = parseLatest => ({
    type: PARSE_LATEST_SUCCESS,
    parseLatest,
});

const parseLatestFailure = parseLatest => ({
    type: PARSE_LATEST_FAILURE,
    parseLatest,
});

export const parseLatest = time => (dispatch, getState) => {
    if (getState().forms[LINK_TO_SEARCH].isParsingLatest) {
        return Promise.resolve();
    }

    dispatch(parseLatestRequest(time));

    return getISO(time)
        .then(data => dispatch(parseLatestSuccess(data)))
        .catch(data => dispatch(parseLatestFailure(data)));
};
