import PropTypes from 'prop-types';
import React from 'react';
import { createTestHook } from 'util/test_support';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import TimeRangeDropdown from '@splunk/react-time-range/Dropdown';

const propTypes = {
    label: PropTypes.string,
    activeTimeRange: PropTypes.shape({
        earliest: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        latest: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    }).isRequired,
    onTimeRangeChange: PropTypes.func.isRequired,
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
    documentationURL: PropTypes.string,
};

const defaultProps = {
    label: '',
    parseEarliest: null,
    parseLatest: null,
    documentationURL: null,
};

const TimeRangeSelector = ({
    label,
    activeTimeRange,
    onTimeRangeChange,
    isFetchingPresets,
    presets,
    locale,
    parseEarliest,
    parseLatest,
    onRequestParseEarliest,
    onRequestParseLatest,
    documentationURL,
}) => (
    <ControlGroup label={label} {...createTestHook(module.id)} controlsLayout="none">
        {isFetchingPresets ? (<WaitSpinner size="medium" />) : (<TimeRangeDropdown
            onChange={onTimeRangeChange}
            earliest={activeTimeRange.earliest || ''}
            latest={activeTimeRange.latest || ''}
            inline={false}
            presets={presets}
            locale={locale}
            parseEarliest={parseEarliest}
            parseLatest={parseLatest}
            onRequestParseEarliest={onRequestParseEarliest}
            onRequestParseLatest={onRequestParseLatest}
            documentationURL={documentationURL}
        />)}
    </ControlGroup>
);

TimeRangeSelector.propTypes = propTypes;
TimeRangeSelector.defaultProps = defaultProps;

export default TimeRangeSelector;
