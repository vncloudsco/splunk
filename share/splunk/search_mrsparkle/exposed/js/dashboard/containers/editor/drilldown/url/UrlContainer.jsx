import { connect } from 'react-redux';
import UrlEditor from 'dashboard/components/editor/drilldown/UrlActionEditor';
import { LINK_TO_CUSTOM_URL } from 'dashboard/containers/editor/drilldown/drilldownNames';
import { updateLinkToURLSetting } from './urlActions';

const mapStateToProps = state => ({
    url: state.forms[LINK_TO_CUSTOM_URL].url,
    urlError: state.forms[LINK_TO_CUSTOM_URL].urlError,
    target: state.forms[LINK_TO_CUSTOM_URL].target,
});

const mapDispatchToProps = dispatch => ({
    onUrlChange: (e, { value }) => {
        dispatch(updateLinkToURLSetting({ url: value }));
    },
    onTargetChange(e, { value }) {
        dispatch(updateLinkToURLSetting({ target: value }));
    },
});

export default connect(
    mapStateToProps,
    mapDispatchToProps,
)(UrlEditor);

