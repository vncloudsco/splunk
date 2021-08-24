import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import TimeRangeTokenEditor from 'dashboard/components/shared/TimeRangeTokenEditor';
import TimeRangeSelector from 'dashboard/components/shared/TimeRangeSelector';
import ItemSelector from 'dashboard/components/shared/ItemSelector';
import {
    EXPLICIT_OPTION,
    TOKEN_OPTION,
    GLOBAL_OPTION,
} from 'dashboard/containers/editor/drilldown/search/timeRangeOptionNames';
import { createTestHook } from 'util/test_support';

const TimeRangeEditor = ({
    isFetchingPresets,
    presets,
    locale,
    parseEarliest,
    parseLatest,
    onRequestParseEarliest,
    onRequestParseLatest,
    extraOptions,
    activeOption,
    onOptionChange,
    activeTimeRange,
    onTimeRangeChange,
    activeTimeRangeToken,
    onTimeRangeTokenChange,
    earliestTokenError,
    latestTokenError,
    timeRangePickerDocsURL,
}) => {
    const options = (extraOptions || []).concat([
        {
            value: EXPLICIT_OPTION,
            label: _('Use time picker').t(),
        },
        {
            value: TOKEN_OPTION,
            label: _('Tokens').t(),
        },
        {
            value: GLOBAL_OPTION,
            label: _('Global').t(),
        },
    ]);

    const optionToView = {
        [GLOBAL_OPTION]: null,
        [TOKEN_OPTION]: <TimeRangeTokenEditor
            activeTimeRangeToken={activeTimeRangeToken}
            onTimeRangeTokenChange={onTimeRangeTokenChange}
            earliestTokenError={earliestTokenError}
            latestTokenError={latestTokenError}
        />,
        [EXPLICIT_OPTION]: <TimeRangeSelector
            isFetchingPresets={isFetchingPresets}
            presets={presets}
            locale={locale}
            parseEarliest={parseEarliest}
            parseLatest={parseLatest}
            onRequestParseEarliest={onRequestParseEarliest}
            onRequestParseLatest={onRequestParseLatest}
            activeTimeRange={activeTimeRange}
            onTimeRangeChange={onTimeRangeChange}
            documentationURL={timeRangePickerDocsURL}
        />,
    };

    return (
        <div {...createTestHook(module.id)}>
            <ItemSelector
                activeItem={activeOption}
                label={_('Time Range').t()}
                items={options}
                onChange={onOptionChange}
                {...createTestHook(null, 'timeRangeType')}
            />
            {optionToView[activeOption]}
        </div>
    );
};

TimeRangeEditor.propTypes = {
    isFetchingPresets: PropTypes.bool.isRequired,
    presets: PropTypes.arrayOf(PropTypes.object).isRequired,
    locale: PropTypes.string.isRequired,
    parseEarliest: PropTypes.shape({
        error: PropTypes.string,
        iso: PropTypes.string,
        time: PropTypes.string,
    }),
    parseLatest: PropTypes.shape({
        error: PropTypes.string,
        iso: PropTypes.string,
        time: PropTypes.string,
    }),
    onRequestParseEarliest: PropTypes.func.isRequired,
    onRequestParseLatest: PropTypes.func.isRequired,
    extraOptions: PropTypes.arrayOf(PropTypes.object),
    activeOption: PropTypes.string.isRequired,
    onOptionChange: PropTypes.func.isRequired,
    activeTimeRange: PropTypes.shape({
        earliest: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        latest: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    }).isRequired,
    onTimeRangeChange: PropTypes.func.isRequired,
    activeTimeRangeToken: PropTypes.shape({
        earliest: PropTypes.string,
        latest: PropTypes.string,
    }).isRequired,
    onTimeRangeTokenChange: PropTypes.func.isRequired,
    earliestTokenError: PropTypes.string,
    latestTokenError: PropTypes.string,
    timeRangePickerDocsURL: PropTypes.string,
};

TimeRangeEditor.defaultProps = {
    extraOptions: [],
    earliestTokenError: '',
    latestTokenError: '',
    parseEarliest: null,
    parseLatest: null,
    timeRangePickerDocsURL: null,
};

export default TimeRangeEditor;
