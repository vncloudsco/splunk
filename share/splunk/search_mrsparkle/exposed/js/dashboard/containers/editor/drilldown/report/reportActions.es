import {
    UPDATE_LINK_TO_REPORT_SETTING,
} from 'dashboard/containers/editor/drilldown/actionTypes';

// eslint-disable-next-line import/prefer-default-export
export const updateLinkToReportSetting = value =>
    ({ type: UPDATE_LINK_TO_REPORT_SETTING, value });
