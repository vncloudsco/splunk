import React, { Component } from 'react';
import PropTypes from 'prop-types';
import _ from 'underscore';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import RadioList from '@splunk/react-ui/RadioList';
import Tooltip from '@splunk/react-ui/Tooltip';
import { createTestHook } from 'util/test_support';
import ArchiveRetention from './ArchiveRetention';

class DynamicDataStorage extends Component {
    constructor(props, ...rest) {
        super(props, ...rest);
        this.state = {
            value: props.selectedOption,
        };
    }

    handleChange = (e, params) => {
        if (e.target.type === 'button') {
            this.setState({ value: params.value });
            this.props.onAttributeChange(params.value);
        }
    }

    renderRadioListOption = item =>
        (
            <RadioList.Option
                key={item.type}
                value={item.type}
                disabled={item.disabled}
                {...createTestHook(null, 'DynamicDataListOption')}
            >
                {item.name}
                {
                    (item.tooltip || item.disabledTooltip) ?
                        <Tooltip
                            style={{ marginLeft: '5px', pointerEvents: 'all' }}
                            content={item.disabled ? item.disabledTooltip : item.tooltip}
                            {...createTestHook(null, 'DynamicDataOptionTooltip')}
                        /> : null
                }
                <div className={item.type}>
                    {
                        (this.state.value === this.props.archiveConst && item.type === this.props.archiveConst) ?
                            <ArchiveRetention
                                maxRetention={this.props.maxArchiveRetention}
                                handleUnitChange={this.props.handleRetentionUnitChange}
                                handlePeriodChange={this.props.handleRetentionPeriodChange}
                                retentionUnit={this.props.retentionUnit}
                                defaultRetentionValue={this.props.defaultRetentionValue}
                            /> : null
                    }
                </div>
            </RadioList.Option>
        );

    render() {
        return (
            <ControlGroup
                label={_('Dynamic Data Storage').t()}
                help={this.props.help}
                {...createTestHook(null, 'DynamicDataListControl')}
            >
                <RadioList
                    value={this.state.value}
                    onChange={this.handleChange}
                    {...createTestHook(null, 'DynamicDataList')}
                >
                    {this.props.options.map(option => this.renderRadioListOption(option))}
                </RadioList>
            </ControlGroup>
        );
    }
}

DynamicDataStorage.propTypes = {
    options: PropTypes.array.isRequired,  // eslint-disable-line react/forbid-prop-types
    selectedOption: PropTypes.string.isRequired,
    help: PropTypes.string.isRequired,
    onAttributeChange: PropTypes.func.isRequired,
    archiveConst: PropTypes.string.isRequired,
    retentionUnit: PropTypes.string.isRequired,
    defaultRetentionValue: PropTypes.number,
    handleRetentionUnitChange: PropTypes.func.isRequired,
    handleRetentionPeriodChange: PropTypes.func.isRequired,
    maxArchiveRetention: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
};

DynamicDataStorage.defaultProps = {
    defaultRetentionValue: 0,
};

export default DynamicDataStorage;