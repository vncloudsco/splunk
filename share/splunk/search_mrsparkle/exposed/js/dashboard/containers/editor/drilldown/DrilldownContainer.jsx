import { connect } from 'react-redux';
import DrilldownEditor from 'dashboard/components/editor/drilldown/DrilldownEditor';
import { updateActiveAction } from './drilldownActions';

const mapStateToProps = state => ({
    isSupported: state.isSupported,
    isCustomViz: state.isCustomViz,
    activeAction: state.activeAction,
});

const mapDispatchToProps = dispatch => ({
    onActionChange: (e, { value }) => {
        dispatch(updateActiveAction(value));
    },
});

export default connect(
    mapStateToProps,
    mapDispatchToProps,
)(DrilldownEditor);