import React, { Component } from 'react';
import PropTypes from 'prop-types';
import moment from '@splunk/moment';
import { _ } from '@splunk/ui-utils/i18n';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Text from '@splunk/react-ui/Text';
import Date from '@splunk/react-ui/Date';
import Select from '@splunk/react-ui/Select';

const timeRegex = /^\d\d:\d\d$/;

class DateTimePicker extends Component {

    static propTypes = {
        /** String containing label to be passed to Control Group */
        label: PropTypes.string.isRequired,
        /** Method to pass new value back to container when fields are modified. */
        onChange: PropTypes.func.isRequired,
        /** Boolen indicating whether fields should be highlighted as an error  */
        error: PropTypes.bool,
        /** Boolen indicating whether fields should be disabled  */
        disabled: PropTypes.bool,
        /** String conataining tooltip to be passed to Control Group */
        tooltip: PropTypes.string,
    }

    static defaultProps = {
        error: false,
        disabled: false,
        tooltip: '',
    }

    constructor(props, context) {
        super(props, context);
        this.state = {
            selectType: 'relative',
            relTimeStr: '',
            date: moment().format(Date.momentFormat),
            time: '23:59',
        };
    }

    /**
     * Returns help text based on the current selection type
     */
    getHelpText = () => {
        if (this.state.selectType === 'absolute') {
            return _('Time is in format HH:MM. Example: 15:45');
        } else if (this.state.selectType === 'relative') {
            return _('Examples: +10m,+20h,+30d');
        }
        return '';
    }

    formatDateTime = (date, time) => {
        if (!time) {
            return moment(`${date}T00:00`).format();
        }
        if (!timeRegex.test(time)) {
            return 'bad time';
        }
        return moment(`${date}T${time}`).format();
    }

    /**
     * Sets state of  selection type to relative or absolute and calls back with new value
     */
    handleSelectTypeChange = (e, { value }) => {
        this.setState({ selectType: value });
        if (value === 'absolute') {
            this.props.onChange(this.formatDateTime(this.state.date, this.state.time));
        } else if (value === 'relative') {
            this.props.onChange(this.state.relTimeStr);
        }
    };

    /**
     * Sets time state for absolute time and calls back with the new full date time value
     */
    handleTimeTextChange = (e, { value }) => {
        this.setState({
            time: value,
        });
        this.props.onChange(this.formatDateTime(this.state.date, value));
    };

    /**
     * Sets date state for absolute time and calls back with the new full date time value
     */
    handleDateChange = (e, { value }) => {
        this.setState({
            date: value,
        });
        this.props.onChange(this.formatDateTime(value, this.state.time));
    };

    /**
     * Sets state of the relative time value and calls back with new value
     */
    handleRelTimeTextChange = (e, { value }) => {
        this.setState({
            relTimeStr: value,
        });
        this.props.onChange(value);
    };

    render() {
        return (
            <div>
                <ControlGroup
                    label={this.props.label}
                    controlsLayout="none"
                    help={this.getHelpText()}
                    tooltip={this.props.tooltip}
                    error={this.props.error}
                    data-test-name={'date-time-group'}
                >
                    <Select
                        value={this.state.selectType}
                        onChange={this.handleSelectTypeChange}
                        disabled={this.props.disabled}
                        error={this.props.error}
                        style={{ paddingBottom: '5px' }}
                    >
                        <Select.Option label={_('Relative Time')} value="relative" />
                        <Select.Option label={_('Absolute Time')} value="absolute" />
                    </Select>
                    {this.state.selectType === 'absolute' && (
                    <div style={{ minWidth: '205px' }}>
                        <Date
                            value={this.state.date}
                            onChange={this.handleDateChange}
                            inline
                            error={this.props.error}
                            disabled={this.props.disabled}
                        />
                        <Text
                            value={this.state.time}
                            onChange={this.handleTimeTextChange}
                            canClear
                            inline
                            style={{ width: '90px' }}
                            error={this.props.error}
                            disabled={this.props.disabled}
                            data-test-name={'abs-time-text'}
                        />
                    </div>
                    )}
                    {this.state.selectType === 'relative' && (
                    <Text
                        value={this.state.relTimeStr}
                        onChange={this.handleRelTimeTextChange}
                        error={this.props.error}
                        disabled={this.props.disabled}
                        data-test-name={'rel-time-text'}
                    />
                    )}
                </ControlGroup>
            </div>
        );
    }
}

export default DateTimePicker;
