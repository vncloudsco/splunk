import {
    UPDATE_LINK_TO_REPORT_SETTING,
} from 'dashboard/containers/editor/drilldown/actionTypes';

const INITIAL_REPORT_SETTING = {
    activeApp: '',
    activeAppError: '',
    activeReport: '',
    activeReportError: '',
};

const toReport = (state = INITIAL_REPORT_SETTING, action) => {
    switch (action.type) {
        case UPDATE_LINK_TO_REPORT_SETTING:
            return Object.assign({}, state, action.value);
        default:
            return state;
    }
};

export default toReport;
