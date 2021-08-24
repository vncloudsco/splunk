import React, { Component } from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';
import { sprintf } from '@splunk/ui-utils/format';
import { _ } from '@splunk/ui-utils/i18n';

import { getDeleteRoleUrl } from '../Utils';

class DeleteRole extends Component {

    static propTypes = {
        object: PropTypes.shape({
            name: PropTypes.string.isRequired,
        }).isRequired,
        open: PropTypes.bool.isRequired,
        nameAttribute: PropTypes.string.isRequired,
        handleRequestClose: PropTypes.func.isRequired,
        /** Handler to update page after delete action */
        handleDeleteChange: PropTypes.func.isRequired,
        setShouldRefreshOnClose: PropTypes.func.isRequired,
        callDeleteRole: PropTypes.func.isRequired,
    };

    constructor(props, context) {
        super(props, context);
        this.state = {
            /** Boolean indicating whether the page is working (saving, deleting, ...). Used to disable button. */
            isWorking: false,
            /** String containing the error message, if any */
            errorMessage: '',
            /** Name of the role */
            title: this.props.object[this.props.nameAttribute] || '',
        };
    }

    /**
     * Call the Delete Role endpoint and process the promise returned.
     */
    handleDelete = () => {
        this.setState({ isWorking: true });
        this.props.callDeleteRole(getDeleteRoleUrl(this.state.title))
            .then(() => {
                /**
                 * handleDeleteChange takes care of updating current page after the delete action.
                 * Pass 1 as argument to represent single deletion mode.
                 */
                this.props.handleDeleteChange(1);
                this.props.setShouldRefreshOnClose();
                this.handleClose();
            })
            .catch((response) => {
                this.setState({
                    isWorking: false,
                    errorMessage: response.message,
                });
            });
    }

    /**
     * Handler for modal close action.
     */
    handleClose = () => {
        this.setState({
            isWorking: false,
            errorMessage: '',
        });
        this.props.handleRequestClose();
    };

    render() {
        return (
            <div>
                <Modal
                    data-test-name="delete-role-modal"
                    onRequestClose={this.handleClose}
                    open={this.props.open}
                    style={{ width: '25%' }}
                >
                    <Modal.Header
                        data-test-name="delete-modal-header"
                        title={_('Delete Role')}
                        onRequestClose={this.handleClose}
                    />
                    <Modal.Body data-test-name="delete-modal-body">
                        {this.state.errorMessage && (<Message type="error">{this.state.errorMessage}</Message>)}
                        <div
                            data-test-name="delete-modal-content"
                            style={{ wordBreak: 'break-word' }}
                        >
                            {sprintf(_('Are you sure you want to delete %s?'), this.state.title)}
                        </div>
                    </Modal.Body>
                    <Modal.Footer data-test-name="delete-modal-footer">
                        <Button
                            data-test-name="delete-cancel-btn"
                            onClick={this.handleClose}
                            label={_('Cancel')}
                        />
                        <Button
                            appearance="primary"
                            data-test-name="delete-btn"
                            disabled={this.state.isWorking}
                            onClick={this.handleDelete}
                            label={this.state.isWorking ? _('Deleting...') : _('Delete')}
                        />
                    </Modal.Footer>
                </Modal>
            </div>
        );
    }
}

export default DeleteRole;
