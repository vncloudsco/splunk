import $ from 'jquery';
import { fullpath } from 'util/splunkd_utils';

let appName = null;
export const getDashboardV2AppName = () => appName;
export const setDashboardV2AppName = (name) => { appName = name; };

export const DASHBOARD_V2_DASHBOARD_ENDPOINT = '/services/dashboardframework/dashboard';

export const isV2Supported = appsCollection =>
    !!appsCollection.find(appModel => appModel.entry.get('name') === appName);

// this REST endpoint is implemented in a separate app as of Pinkie Pie release,
// so make sure you check the app is installed before sending request to this endpoint.
export const convertV1ToV2 = ({ layoutType, simplexml }) =>
    $.post(`${fullpath(DASHBOARD_V2_DASHBOARD_ENDPOINT)}`, { layoutType, simplexml });