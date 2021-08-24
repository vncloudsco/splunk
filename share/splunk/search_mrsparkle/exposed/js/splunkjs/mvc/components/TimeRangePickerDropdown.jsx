import React, { Component } from 'react';
import PropTypes from 'prop-types';
import Dropdown from '@splunk/react-time-range/Dropdown';
import { createTestHook } from 'util/test_support';
import moment from '@splunk/moment';
import SplunkwebConnector from '@splunk/react-time-range/SplunkwebConnector';

export const convertISOtoEpoch = (time) => {
    const momentTime = moment.newSplunkTime({ time, format: moment.ISO_8601 });
    if (momentTime.isValid()) {
        // the valueOf() method is used here to keep the millisecond values, and we divide by 1000.
        // This way of keeping ms is not preferrable but is okay since the only place being used is
        // down in the _convertEpochToISO() method
        return (momentTime.valueOf() / 1000).toString();
    }
    return time;
};

export const convertEpochToISO = (time) => {
    if (!time || time === '0') {
        // deal with empty string and special case '0'
        return time;
    }
    const momentTime = moment.unix(time);
    if (momentTime.isValid()) {
        return moment.newSplunkTime({ time: momentTime }).format('YYYY-MM-DDTHH:mm:ss.SSS');
    }
    return time;
};

class TimeRangePickerDropdown extends Component {
    constructor(props) {
        super(props);

        const {
            earliest,
            latest,
        } = this.props;

        this.state = {
            earliest,
            latest,
            parseEarliest: null,
            parseLatest: null,
        };
    }

    componentWillReceiveProps({ earliest, latest }) {
        if (earliest !== this.state.earliest) {
            this.setState({
                earliest,
            });
        }

        if (latest !== this.state.latest) {
            this.setState({
                latest,
            });
        }
    }

    render() {
        const {
            presets,
            onChange,
            documentationURL,
            menuSettings,
            labelMaxChars,
        } = this.props;

        const {
            earliest,
            latest,
        } = this.state;

        const formInputTypes = [];
        let advancedInputTypes = [];

        if (menuSettings.showRelative) {
            formInputTypes.push('relative');
            advancedInputTypes.push('relative');
        }
        if (menuSettings.showRealtime) {
            formInputTypes.push('realTime');
            advancedInputTypes.push('realTime');
        }
        if (menuSettings.showDate) {
            formInputTypes.push('date');
            advancedInputTypes.push('allTime');
        }
        if (menuSettings.showDateTime) {
            formInputTypes.push('dateTime');
            advancedInputTypes.push('dateTime');
        }
        if (!menuSettings.showAdvanced) {
            advancedInputTypes = [];
        }

        return (
            <SplunkwebConnector
            // keeping the presets from Splunkjs implementation because it allows
            // users to provide customized presets
                presetsTransform={menuSettings.showPresets ? () => presets : () => []}
            >
                <Dropdown
                    advancedInputTypes={advancedInputTypes}
                    formInputTypes={formInputTypes}
                    onChange={(e, timeRange) => {
                        const epochTimeRange = {
                            earliest: convertISOtoEpoch(timeRange.earliest),
                            latest: convertISOtoEpoch(timeRange.latest),
                        };
                        this.setState(epochTimeRange);
                        onChange(e, epochTimeRange);
                    }}
                    inline={false}
                    earliest={convertEpochToISO(earliest)}
                    latest={convertEpochToISO(latest)}
                    documentationURL={documentationURL}
                    labelMaxChars={labelMaxChars}
                    {...createTestHook(module.id)}
                />
            </SplunkwebConnector>
        );
    }
}

TimeRangePickerDropdown.propTypes = {
    presets: PropTypes.arrayOf(PropTypes.shape({
        label: PropTypes.string,
        earliest: PropTypes.string,
        latest: PropTypes.string,
    })).isRequired,
    onChange: PropTypes.func.isRequired,
    earliest: PropTypes.string,
    latest: PropTypes.string,
    documentationURL: PropTypes.string,
    menuSettings: PropTypes.objectOf(PropTypes.bool),
    labelMaxChars: PropTypes.number,
};

TimeRangePickerDropdown.defaultProps = {
    earliest: '',
    latest: '',
    documentationURL: null,
    menuSettings: {
        showPresets: true,
        showAdvanced: true,
        showDate: true,
        showRealtime: true,
        showDateTime: true,
        showRelative: true,
    },
    labelMaxChars: 40,
};

export default TimeRangePickerDropdown;
