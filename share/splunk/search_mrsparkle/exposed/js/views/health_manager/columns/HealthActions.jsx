import React, { Component } from 'react';
import PropTypes from 'prop-types';
import omit from 'lodash/omit';
import { _ } from '@splunk/ui-utils/i18n';
import Link from '@splunk/react-ui/Link';
import { createTestHook } from '@splunk/base-lister/utils/TestSupport';
import EditThresholdsModal from 'views/health_manager/modals/EditThresholds';

/**
 * Actions column component.
 * It consists of a single link for editing the threshold of the feature.
 * This component is responsible for rendering the modal for the action taken by the user.
 */
class HealthActions extends Component {
    /**
     * See base-lister/src/Main.jsx for propTypes definition.
     */
    static propTypes = {
        object: PropTypes.shape({}).isRequired,
        idAttribute: PropTypes.string.isRequired,
        handleRefreshListing: PropTypes.func.isRequired,
    };

    static defaultProps = {};

    constructor(...args) {
        super(...args);

        this.state = {
            /**
             * 'action' parameter for the default ModalEditTitleOrDescription modal.
             * Can be one of the following:
             *  - 'edit_threshold'
             *  - 'edit_alert' (future option)
             */
            action: 'edit_threshold',
            /** boolean indicating whether the current action modal is open */
            isModalOpen: false,
            /** current action modal component to open when the user clicks an action */
            modalToOpen: null,
            /** Indicates whether the listing should refresh when a modal is closed */
            shouldRefreshOnClose: false,
        };
    }

    /**
     * Sets refreshing on close to be true.
     */
    setShouldRefreshOnClose = () => {
        this.setState({
            shouldRefreshOnClose: true,
        });
    };

    /**
     * Handles the close action of the currently opened Modal (this.state.modalToOpen).
     */
    handleRequestClose = () => {
        if (this.state.shouldRefreshOnClose) {
            this.props.handleRefreshListing();
        } else {
            this.setState({
                modalToOpen: null,
                shouldRefreshOnClose: false,
                isModalOpen: false,
            });
        }
    };

    /**
     * Handles the open modal click for the Edit Threshold action.
     */
    handleEditThresholdClicked = () => {
        this.setState({
            isModalOpen: true,
            action: 'edit_threshold',
            modalToOpen: EditThresholdsModal,
        });
    };

    /**
     * Renders the element.
     * @returns {XML} Markup of the Actions column.
     */
    render() {
        const {
            object,
            idAttribute,
            ...otherProps
        } = this.props;
        const { action, isModalOpen } = this.state;
        return (
            <div
                style={{
                    textAlign: 'left',
                    padding: '4px 12px',
                }}
                {...createTestHook(__filename)}
            >
                <Link
                    data-test-name={'edit-threshold'}
                    key={'edit'}
                    style={{ whiteSpace: 'nowrap' }}
                    onClick={this.handleEditThresholdClicked}
                >
                    {_('Edit Thresholds')}
                </Link>
                {this.state.modalToOpen && (
                    <this.state.modalToOpen
                        object={object}
                        idAttribute={idAttribute}
                        isBulk={false}
                        action={action}
                        open={isModalOpen}
                        selectedRows={[]}
                        handleRequestClose={this.handleRequestClose}
                        setShouldRefreshOnClose={this.setShouldRefreshOnClose}
                        {...omit(
                            otherProps,
                            'ModalChangeStatus',
                            'ModalEditThreshold',
                        )}
                    />
                )}
            </div>
        );
    }
}

export default HealthActions;