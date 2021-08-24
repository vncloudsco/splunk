import { connect } from 'react-redux';
import ReportActionEditor from 'dashboard/components/editor/drilldown/ReportActionEditor';
import { LINK_TO_REPORT } from 'dashboard/containers/editor/drilldown/drilldownNames';
import { updateLinkToReportSetting } from './reportActions';
import { fetchReports } from '../drilldownActions';

const mapStateToProps = state => ({
    activeApp: state.forms[LINK_TO_REPORT].activeApp,
    activeAppError: state.forms[LINK_TO_REPORT].activeAppError,
    apps: state.apps.items,
    isFetchingApps: state.apps.isFetching,
    activeReport: state.forms[LINK_TO_REPORT].activeReport,
    activeReportError: state.forms[LINK_TO_REPORT].activeReportError,
    target: state.forms[LINK_TO_REPORT].target,
    reports: state.reports.items,
    isFetchingReports: state.reports.isFetching,
});

const mapDispatchToProps = dispatch => ({
    onAppChange(e, { value }) {
        dispatch(updateLinkToReportSetting({
            activeApp: value,
            // reset activeReport to make sure it is in sync with UI. If activeReport is not reset,
            // it will not match any reports in the newly rendered report dropdown, which gives user
            // a wrong perception that no report is selected.
            activeReport: '',
        }));
        dispatch(fetchReports({ app: value }));
    },
    onReportChange(e, { value }) {
        dispatch(updateLinkToReportSetting({ activeReport: value }));
    },
    onTargetChange(e, { value }) {
        dispatch(updateLinkToReportSetting({ target: value }));
    },
});

const ReportContainer = connect(
    mapStateToProps,
    mapDispatchToProps,
)(ReportActionEditor);

export default ReportContainer;
