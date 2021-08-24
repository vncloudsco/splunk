import React, { Component } from 'react';
import PropTypes from 'prop-types';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Select from '@splunk/react-ui/Select';
import Number from '@splunk/react-ui/Number';
import { createTestHook } from 'util/test_support';
import { _ } from '@splunk/ui-utils/i18n';

class ArchiveRetention extends Component {
    constructor(props, ...rest) {
        super(props, ...rest);
        const numValue = parseInt(this.props.defaultRetentionValue, 10);
        this.state = {
            value: numValue > 0 ? numValue : null,
        };
    }
    handleChange = (e, { value }) => {
        this.setState({ value });
        this.props.handlePeriodChange(value);
    }
    handleUnitChange = (e, { value }) => {
        this.props.handleUnitChange(value);
    }
    render() {
        return (
            <ControlGroup
                help={_(`Maximum archive retention: ${this.props.maxRetention.days} days`)}
                label={_('Archive Retention Period')}
                controlsLayout="fillJoin"
                {...createTestHook(null, 'ArchiveRetentionControl')}
            >
                <Number
                    value={this.state.value}
                    roundTo={0}
                    min={0}
                    onChange={this.handleChange}
                    {...createTestHook(null, 'ArchiveRetentionNumber')}
                />
                <Select
                    value={this.props.retentionUnit}
                    style={{ minWidth: '80px' }}
                    onChange={this.handleUnitChange}
                    {...createTestHook(null, 'ArchiveRetentionUnitSelect')}
                >
                    <Select.Option
                        label={_('years')}
                        value="years"
                        {...createTestHook(null, 'ArchiveRetentionUnitOption')}
                    />
                    <Select.Option
                        label={_('months')}
                        value="months"
                        {...createTestHook(null, 'ArchiveRetentionUnitOption')}
                    />
                    <Select.Option
                        label={_('days')}
                        value="days"
                        {...createTestHook(null, 'ArchiveRetentionUnitOption')}
                    />
                </Select>
            </ControlGroup>
        );
    }
}

ArchiveRetention.propTypes = {
    maxRetention: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    handleUnitChange: PropTypes.func.isRequired,
    handlePeriodChange: PropTypes.func.isRequired,
    retentionUnit: PropTypes.string.isRequired,
    defaultRetentionValue: PropTypes.number,
};

ArchiveRetention.defaultProps = {
    defaultRetentionValue: 0,
};

export default ArchiveRetention;