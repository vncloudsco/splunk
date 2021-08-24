import {
    UPDATE_LINK_TO_DASHBOARD_SETTING,
} from 'dashboard/containers/editor/drilldown/actionTypes';

const INITIAL_DASHBOARD_SETTING = {
    activeApp: '',
    activeAppError: '',
    activeDashboard: '',
    activeDashboardError: '',
    params: [],
};

const dashboard = (state = INITIAL_DASHBOARD_SETTING, action) => {
    switch (action.type) {
        case UPDATE_LINK_TO_DASHBOARD_SETTING:
            return Object.assign({}, state, action.value);
        default:
            return state;
    }
};

export default dashboard;
