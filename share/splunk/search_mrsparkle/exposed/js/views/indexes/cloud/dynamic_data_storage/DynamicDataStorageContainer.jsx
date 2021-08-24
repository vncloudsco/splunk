import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import DynamicDataStorage from './DynamicDataStorage';

class DynamicDataStorageContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.storageOptions = [
            {
                name: _('Splunk Archive'),
                type: this.props.constants.ARCHIVE,
                disabled: !this.props.archiveLicense,
                tooltip: _('As data in this index expires, move it to the Splunk archive.'),
                disabledTooltip: (`To enable Splunk archiving, contact your Splunk representative 
                for details and pricing.`),
            },
            {
                name: _('Self Storage'),
                type: this.props.constants.SELF_STORAGE,
                disabled: false,
                tooltip: _('As data in this index expires, move it to your self storage location.'),
            },
            {
                name: _('No Additional Storage'),
                type: this.props.constants.NONE,
                disabled: false,
            },
        ];
        this.maxRet = {
            years: Math.floor(this.props.maxArchiveRetention / 365),
            months: Math.floor(this.props.maxArchiveRetention / 30),
            days: this.props.maxArchiveRetention,
        };

        this.model = this.context.model;
        this.state = {
            storageType: this.model.state.get('dynamicStorageOption'),
            storageOptions: this.storageOptions,
            storageUnit: this.model.state.get('archiveRetentionUnit'),
        };
    }

    handleAttributeChange = (value) => {
        this.setState({
            storageType: value,
            storageOptions: this.storageOptions,
        });
        this.model.state.set('dynamicStorageOption', value);
    }

    handleRetentionUnitChange = (value) => {
        this.setState({ storageUnit: value });
        this.model.state.set('archiveRetentionUnit', value);
    }

    handleRetentionPeriodChange = (value) => {
        this.model.addEditIndexModel.set('archiver.coldStorageRetentionPeriod', value);
    }

    render() {
        const retValue = this.model.addEditIndexModel.get('archiver.coldStorageRetentionPeriod');
        return (
            <DynamicDataStorage
                archiveConst={this.props.constants.ARCHIVE}
                options={this.state.storageOptions}
                selectedOption={this.state.storageType}
                help={_('Learn more about Dynamic Data Storage options.')}
                onAttributeChange={value => this.handleAttributeChange(value)}
                handleRetentionUnitChange={this.handleRetentionUnitChange}
                handleRetentionPeriodChange={this.handleRetentionPeriodChange}
                retentionUnit={this.state.storageUnit}
                defaultRetentionValue={retValue}
                maxArchiveRetention={this.maxRet}
            />
        );
    }
}

DynamicDataStorageContainer.contextTypes = {
    model: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

DynamicDataStorageContainer.propTypes = {
    constants: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    archiveLicense: PropTypes.bool.isRequired,
    maxArchiveRetention: PropTypes.number.isRequired,
};

export default DynamicDataStorageContainer;