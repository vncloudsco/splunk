import {
  UPDATE_TOKENS_SETTING,
} from 'dashboard/containers/editor/drilldown/actionTypes';

const tokens = (state = {
    items: [],
}, action) => {
    switch (action.type) {
        case UPDATE_TOKENS_SETTING:
            return Object.assign({}, state, action.value);
        default:
            return state;
    }
};

export default tokens;
