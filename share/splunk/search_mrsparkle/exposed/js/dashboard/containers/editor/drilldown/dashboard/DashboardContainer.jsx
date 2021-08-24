import { connect } from 'react-redux';
import DashboardEditor from 'dashboard/components/editor/drilldown/dashboard/DashboardActionEditor';
import { generateLinkToDashboard } from 'controllers/dashboard/helpers/DrilldownStateConverter';
import { LINK_TO_DASHBOARD } from 'dashboard/containers/editor/drilldown/drilldownNames';
import route from 'uri/route';
import { updateLinkToDashboardSetting } from './dashboardActions';
import { fetchDashboards } from '../drilldownActions';

const mapStateToProps = state => Object.assign({},
    {
        apps: state.apps.items,
        isFetchingApps: state.apps.isFetching,
        dashboards: state.dashboards.items,
        isFetchingDashboards: state.dashboards.isFetching,
        activeApp: state.forms[LINK_TO_DASHBOARD].activeApp,
        activeAppError: state.forms[LINK_TO_DASHBOARD].activeAppError,
        activeDashboard: state.forms[LINK_TO_DASHBOARD].activeDashboard,
        activeDashboardError: state.forms[LINK_TO_DASHBOARD].activeDashboardError,
        target: state.forms[LINK_TO_DASHBOARD].target,
        params: state.forms[LINK_TO_DASHBOARD].params,
        previewLink: {
            label: generateLinkToDashboard(state),
            // needs to be absolute path because current location is <dashboard_name>/edit
            value: generateLinkToDashboard(state),
        },
        learnMoreLinkForTokens: route.docHelp(
            state.splunkEnv.application.root,
            state.splunkEnv.application.locale,
            'learnmore.dashboard.drilldown.tokens',
        ),
        candidateTokens: state.elementEnv.drilldownTokens,
    },
);

const mapDispatchToProps = dispatch => ({
    onAppChange(e, { value }) {
        dispatch(updateLinkToDashboardSetting({
            activeApp: value,
            // reset activeDashboard to make sure it is in sync with UI. If activeDashboard is not
            // reset, it will not match any dashboards in the newly rendered dashboard dropdown,
            // which gives user a wrong perception that no dashboard is selected.
            activeDashboard: '',
        }));
        dispatch(fetchDashboards({ app: value }));
    },
    onDashboardChange(e, { value }) {
        dispatch(updateLinkToDashboardSetting({ activeDashboard: value }));
    },
    onTargetChange(e, { value }) {
        dispatch(updateLinkToDashboardSetting({ target: value }));
    },
    onParamsChange(params) {
        dispatch(updateLinkToDashboardSetting({ params }));
    },
});

export default connect(
    mapStateToProps,
    mapDispatchToProps,
)(DashboardEditor);
