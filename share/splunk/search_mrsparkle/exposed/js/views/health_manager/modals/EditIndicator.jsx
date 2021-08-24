import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { sprintf } from '@splunk/ui-utils/format';
import { _ } from '@splunk/ui-utils/i18n';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Number from '@splunk/react-ui/Number';
import { createTestHook } from '@splunk/base-lister/utils/TestSupport';
import { indicatorSeparator } from 'views/health_manager/modals/EditIndicator.pcss';

class EditIndicator extends Component {
    static propTypes = {
        /**
         * Name of the indicator that is being edited.
         */
        indicatorName: PropTypes.string.isRequired,
        /**
         * Red value of the indicator that is being edited.
         */
        indicatorRed: PropTypes.number,
        /**
         * Yellow value of the indicator that is being edited.
         */
        indicatorYellow: PropTypes.number,
        /**
         * Description of the indicator that is being edited.
         */
        indicatorDescription: PropTypes.string,
        /**
         * If the separator under the Indicator should be hidden.
         * Defaults to false.
         */
        hideSeparator: PropTypes.boolean,
        /**
         * Function for updating the object's state.
         */
        handleThresholdChange: PropTypes.func.isRequired,
    };

    static defaultProps = {
        indicatorRed: null,
        indicatorYellow: null,
        indicatorDescription: null,
        hideSeparator: false,
    };

    /**
     * Handle when an indicator's red threshold is changed.
     */
    handleRedThresholdChange = (e, { value }) => {
        if (value) {
            // reassamble indicator name and update it
            const fullIndicatorName = sprintf('indicator:%s:red', this.props.indicatorName);
            this.props.handleThresholdChange(fullIndicatorName, value);
        }
    };

    /**
     * Handle when an indicator's yellow threshold is changed.
     */
    handleYellowThresholdChange = (e, { value }) => {
        if (value) {
            // reassamble indicator name and update it
            const fullIndicatorName = sprintf('indicator:%s:yellow', this.props.indicatorName);
            this.props.handleThresholdChange(fullIndicatorName, value);
        }
    };

    /**
     * Renders the element.
     * @returns {XML}
     */
    render() {
        return (
            <div
                data-test-name={this.props.indicatorName}
                data-role={'indicator'}
                style={
                    this.props.hideSeparator ? {} :
                    { borderBottomWidth: '1px',
                        borderBottomStyle: 'solid',
                        borderBottomColor: indicatorSeparator }}
                {...createTestHook(__filename)}
            >
                <ControlGroup
                    label={_('Indicator')}
                    controlsLayout="none"
                    data-test-name="indicator-title"
                >
                    <p
                        style={{ paddingTop: 6, marginBottom: 0 }}
                    >
                        {this.props.indicatorName}
                    </p>
                </ControlGroup>
                {this.props.indicatorDescription &&
                    <ControlGroup
                        label={_('Description')}
                        controlsLayout="none"
                        data-test-name="indicator-description"
                    >
                        <p>
                            {this.props.indicatorDescription}
                        </p>
                    </ControlGroup>
                }
                {this.props.indicatorRed &&
                    <ControlGroup
                        label={_('Red')}
                        controlsLayout="none"
                        data-test-name={'red_threshold'}
                    >
                        <Number
                            roundTo={0}
                            min={0}
                            value={this.props.indicatorRed}
                            onChange={this.handleRedThresholdChange}
                            inline
                            style={{ width: 90 }}
                        />
                    </ControlGroup>
                }
                {this.props.indicatorYellow &&
                    <ControlGroup
                        label={_('Yellow')}
                        controlsLayout="none"
                        data-test-name={'yellow_threshold'}
                    >
                        <Number
                            roundTo={0}
                            min={0}
                            value={this.props.indicatorYellow}
                            onChange={this.handleYellowThresholdChange}
                            inline
                            style={{ width: 90 }}
                        />
                    </ControlGroup>
                }
            </div>
        );
    }
}

export default EditIndicator;
