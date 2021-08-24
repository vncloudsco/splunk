import {
    UPDATE_LINK_TO_DASHBOARD_SETTING,
} from 'dashboard/containers/editor/drilldown/actionTypes';

// eslint-disable-next-line import/prefer-default-export
export const updateLinkToDashboardSetting = value =>
    ({ type: UPDATE_LINK_TO_DASHBOARD_SETTING, value });
