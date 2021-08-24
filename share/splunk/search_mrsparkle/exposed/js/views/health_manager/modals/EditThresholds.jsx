import React, { Component } from 'react';
import PropTypes from 'prop-types';
import merge from 'lodash/merge';
import { defaultFetchInit, handleResponse } from '@splunk/splunk-utils/fetch';
import { sprintf } from '@splunk/ui-utils/format';
import { _ } from '@splunk/ui-utils/i18n';
import { createTestHook } from '@splunk/base-lister/utils/TestSupport';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import EditIndicator from 'views/health_manager/modals/EditIndicator';

class EditThresholdsModal extends Component {
    static propTypes = {
        /**
         * Indicates whether the Modal is open.
         */
        open: PropTypes.bool.isRequired,
        /**
         * Object that is currently being created/edited/cloned.
         */
        object: PropTypes.shape({
            content: PropTypes.shape({
                display_name: PropTypes.string.isRequired,
            }),
        }).isRequired,
        /**
         * String that represents the path for the object collection.
         */
        objectsCollectionPath: PropTypes.string.isRequired,
        /**
         * ID attribute of the object. Default is 'id'.
         * Other example: _key
         */
        idAttribute: PropTypes.string.isRequired,
        /**
         * Function that allows for customization or formatting of error messages.
         */
        errorFormatter: PropTypes.func.isRequired,
        /**
         * Handler function that is triggered when the Modal closes.
         */
        handleRequestClose: PropTypes.func.isRequired,
        /**
         * Setter method that can be used when any action of a Modal should trigger a refresh of the objects list
         * when the Modal closes.
         */
        setShouldRefreshOnClose: PropTypes.func.isRequired,
        /**
         * Warning message displayed at the top of the modal, if any.
         */
        warningMessage: PropTypes.string,
    };

    static defaultProps = {
        warningMessage: '',
        objectsCollectionPath: '',
    };

    /**
     * Given the full indicator name, return the id and color.
     * @returns {String, String} id and color from indicator
     */
    static getIdAndColor(fullIndicator) {
        const firstColon = fullIndicator.indexOf(':');
        const secondColon = fullIndicator.indexOf(':', firstColon + 1);
        const id = fullIndicator.slice(firstColon + 1, secondColon);
        const color = fullIndicator.slice(secondColon + 1);
        return { id, color };
    }

    constructor(props, context) {
        super(props, context);
        this.state = {
            /** Indicates whether the page is saving. Used to disable button. */
            isWorking: false,
            /** Error message, if any */
            errorMessage: '',
            /** Indicators in a format for rendering.  */
            indicators: this.getIndicators(),
        };
    }

    /**
     * Get display title of the modal.
     * @returns {String}
     */
    getModalTitle() {
        return sprintf(_('Edit Thresholds for %s'),
            this.props.object.content.display_name);
    }

    /**
     * Get label for the save button.
     * @returns {String}
     */
    getButtonLabel() {
        if (this.state.isWorking) {
            return _('Saving...');
        }
        return _('Save');
    }

    /**
     * Processes the object's indicators so they can be rendered.
     * @returns {Object}
     */
    getIndicators() {
        const indicators = {};
        Object.keys(this.props.object.content).forEach((indicator) => {
            if (indicator.startsWith('indicator:')) {
                const { id, color } = EditThresholdsModal.getIdAndColor(indicator);
                if (!indicators[id]) {
                    indicators[id] = {};
                    indicators[id].name = id;
                }
                if (color === 'description') {
                    // This value is a description instead of color.
                    indicators[id].description = this.props.object.content[indicator];
                } else {
                    // Actually a threshold value for red or yellow
                    indicators[id][color] = parseInt(this.props.object.content[indicator], 10);
                }
            }
        });
        return indicators;
    }

    /**
     * Handles the successful save of the data.
     */
    handleSuccess = () => {
        this.props.setShouldRefreshOnClose();
        this.handleCloseModal();
    };


    /**
     * Handles the save action.
     */
    handleSaveActionDispatcher = () => {
        this.setState({
            isWorking: true,
        });
        const editObjectURL = `${this.props.objectsCollectionPath}/${this.props.object[
            this.props.idAttribute
        ]
            .split('/')
            .pop()}?output_mode=json`;

        let changeIndicators = '';
        Object.keys(this.state).forEach((indicator) => {
            if (indicator.startsWith('indicator:')) {
                if (changeIndicators.length) {
                    changeIndicators = sprintf('%s&%s=%s', changeIndicators, indicator, this.state[indicator]);
                } else {
                    changeIndicators = sprintf('%s=%s', indicator, this.state[indicator]);
                }
            }
        });

        const fetchOverrides = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: changeIndicators,
        };
        const editFetchInit = merge({}, defaultFetchInit, fetchOverrides);

        fetch(editObjectURL, editFetchInit)
            .then(handleResponse(200))
            .then(() => {
                this.handleSuccess();
            })
            .catch((response) => {
                this.handleError(
                    sprintf(
                        _('Could not edit thresholds of %s.'),
                        this.props.object.content.display_name),
                    response,
                );
            });
    };

    /**
     * Error handler
     * @param {String} message error message.
     * @param {String} response request response containing some more useful information.
     */
    handleError = (message, response) => {
        if (response && response.text && typeof response.text === 'function') {
            response.text().then((body) => {
                const enrichedError = response;
                enrichedError.responseText = body;
                this.setState({
                    isWorking: false,
                    errorMessage: this.props.errorFormatter(message, enrichedError),
                });
            });
        } else {
            this.setState({
                isWorking: false,
                errorMessage: message,
            });
        }
    };

    /**
     * Handles closing the edit threshold modal.
     */
    handleCloseModal = () => {
        this.setState({
            isWorking: false,
            errorMessage: '',
        });
        this.props.handleRequestClose();
    };

    /**
     * Threshold change handler
     * @param {String} indicatorName name of indicator.
     * @param {Number} value indicator value
     */
    handleThresholdChange = (indicatorName, value) => {
        const { id, color } = EditThresholdsModal.getIdAndColor(indicatorName);
        const newIndicators = { ...this.state.indicators };
        newIndicators[id][color] = value;
        this.setState({
            [indicatorName]: value,
            indicators: newIndicators,
        });
    };

    /**
     * Renders the element.
     * @returns {XML}
     */
    render() {
        return (
            <Modal
                onRequestClose={this.handleCloseModal}
                open={this.props.open}
                style={{ width: '500px' }}
                {...createTestHook(__filename)}
            >
                <Modal.Header
                    title={this.getModalTitle()}
                    onRequestClose={this.handleCloseModal}
                />
                <Modal.Body>
                    {this.state.errorMessage && (
                        <Message type="error">{this.state.errorMessage}</Message>
                    )}
                    {this.props.warningMessage && (
                        <Message type={'warning'}>{this.props.warningMessage}</Message>
                    )}
                    {Object.keys(this.state.indicators).map((indicator, i) =>
                        <EditIndicator
                            key={this.state.indicators[indicator].name}
                            indicatorName={this.state.indicators[indicator].name}
                            indicatorDescription={this.state.indicators[indicator].description || null}
                            indicatorRed={this.state.indicators[indicator].red || null}
                            indicatorYellow={this.state.indicators[indicator].yellow || null}
                            handleThresholdChange={this.handleThresholdChange}
                            hideSeparator={i === Object.keys(this.state.indicators).length - 1}
                        />,
                    )}
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        data-test-name={'cancel-btn'}
                        onClick={this.handleCloseModal}
                        label={_('Cancel')}
                    />
                    <Button
                        appearance="primary"
                        data-test-name={'save-btn'}
                        disabled={this.state.isWorking}
                        onClick={this.handleSaveActionDispatcher}
                        label={this.getButtonLabel()}
                    />
                </Modal.Footer>
            </Modal>
        );
    }
}

export default EditThresholdsModal;
