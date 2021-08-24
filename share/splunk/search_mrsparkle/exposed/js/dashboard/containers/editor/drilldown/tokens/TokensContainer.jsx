import { connect } from 'react-redux';
import _ from 'underscore';
import TokensActionEditor from 'dashboard/components/editor/drilldown/tokens/TokensActionEditor';
import { EDIT_TOKENS } from 'dashboard/containers/editor/drilldown/drilldownNames';
import route from 'uri/route';
import { updateTokensSetting } from './tokensActions';

const mapStateToProps = state => ({
    items: state.forms[EDIT_TOKENS].items,
    error: state.forms[EDIT_TOKENS].error,
    candidateTokens: state.elementEnv.drilldownTokens,
    learnMoreLinkForTokenUsage: route.docHelp(
        state.splunkEnv.application.root,
        state.splunkEnv.application.locale,
        'learnmore.dashboard.drilldown.example_token_usage',
    ),
});

const mapDispatchToProps = dispatch => ({
    onUpdateTokens(items) {
        dispatch(updateTokensSetting({ items: items.map((item) => {
            if (item.type === 'unset') {
                // 'unset' should not have value
                return _.omit(item, 'value');
            }

            // make sure value is not undefined for 'set' and 'eval'
            return _.defaults({}, item, { value: '' });
        }) }));
    },
});

export default connect(
    mapStateToProps,
    mapDispatchToProps,
)(TokensActionEditor);
