import { connect } from 'react-redux';
import SearchEditor from 'dashboard/components/editor/drilldown/search/SearchActionEditor';
import { LINK_TO_SEARCH } from 'dashboard/containers/editor/drilldown/drilldownNames';
import route from 'uri/route';
import {
    updateLinkToSearchSetting,
    parseEarliest,
    parseLatest,
} from './searchActions';

const mapStateToProps = state => ({
    options: state.forms[LINK_TO_SEARCH].options,
    activeOption: state.forms[LINK_TO_SEARCH].activeOption,
    search: state.forms[LINK_TO_SEARCH].search,
    searchError: state.forms[LINK_TO_SEARCH].searchError,
    isFetchingPresets: state.timeRangePresets.isFetching,
    presets: state.timeRangePresets.items,
    locale: state.splunkEnv.application.locale,
    parseEarliest: state.forms[LINK_TO_SEARCH].parseEarliest,
    parseLatest: state.forms[LINK_TO_SEARCH].parseLatest,
    extraTimeRangeOptions: state.forms[LINK_TO_SEARCH].extraTimeRangeOptions,
    activeTimeRangeOption: state.forms[LINK_TO_SEARCH].activeTimeRangeOption,
    activeTimeRange: state.forms[LINK_TO_SEARCH].activeTimeRange,
    activeTimeRangeToken: state.forms[LINK_TO_SEARCH].activeTimeRangeToken,
    earliestTokenError: state.forms[LINK_TO_SEARCH].earliestTokenError,
    latestTokenError: state.forms[LINK_TO_SEARCH].latestTokenError,
    target: state.forms[LINK_TO_SEARCH].target,
    learnMoreLinkForTokens: route.docHelp(
        state.splunkEnv.application.root,
        state.splunkEnv.application.locale,
        'learnmore.dashboard.drilldown.tokens',
    ),
    timeRangePickerDocsURL: route.docHelp(
        state.splunkEnv.application.root,
        state.splunkEnv.application.locale,
        'learnmore.timerange.picker',
    ),
});

const mapDispatchToProps = dispatch => ({
    onOptionChange: (e, { value }) => {
        dispatch(updateLinkToSearchSetting({ activeOption: value }));
    },
    onSearchChange: (e, { value } = {}) => {
        dispatch(updateLinkToSearchSetting({
            search: value,
        }));
    },
    onTargetChange(e, { value }) {
        dispatch(updateLinkToSearchSetting({ target: value }));
    },
    onTimeRangeOptionChange: (e, { value }) => {
        dispatch(updateLinkToSearchSetting({ activeTimeRangeOption: value }));
    },
    onTimeRangeChange: (e, { earliest, latest }) => {
        dispatch(updateLinkToSearchSetting({ activeTimeRange: { earliest, latest } }));
    },
    onTimeRangeTokenChange: (e, { value }) => {
        dispatch(updateLinkToSearchSetting({ activeTimeRangeToken: value }));
    },
    onRequestParseEarliest: (time) => {
        dispatch(parseEarliest(time));
    },
    onRequestParseLatest: (time) => {
        dispatch(parseLatest(time));
    },
});

export default connect(
    mapStateToProps,
    mapDispatchToProps,
)(SearchEditor);

