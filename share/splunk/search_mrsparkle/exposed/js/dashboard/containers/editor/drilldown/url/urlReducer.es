import {
    UPDATE_LINK_TO_URL_SETTING,
} from 'dashboard/containers/editor/drilldown/actionTypes';

const INITIAL_SEARCH_SETTING = {
    url: 'http://',
    target: '',
};
const linkToURL = (state = INITIAL_SEARCH_SETTING, action) => {
    switch (action.type) {
        case UPDATE_LINK_TO_URL_SETTING:
            return Object.assign({}, state, action.value);
        default:
            return state;
    }
};

export default linkToURL;
