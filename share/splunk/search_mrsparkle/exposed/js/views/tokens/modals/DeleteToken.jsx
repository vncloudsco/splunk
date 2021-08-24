import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';
import Tooltip from '@splunk/react-ui/Tooltip';
import { _ } from '@splunk/ui-utils/i18n';
import { createTestHook } from '@splunk/base-lister/utils/TestSupport';
import { smartTrim, sprintf } from '@splunk/ui-utils/format';

const DeleteToken = props => (
    <div>
        <Modal
            onRequestClose={props.handleClose}
            open={props.open}
            style={{ minWidth: '500px' }}
            {...createTestHook('DeleteTokenModal')}
        >
            <Modal.Header
                title={_('Delete Token')}
                onRequestClose={props.handleClose}
            />
            <Modal.Body>
                {props.errorMessage && (<Message type="error">{props.errorMessage}</Message>)}
                <div data-test="delete-modal-content">
                    {`${_('Are you sure you want to delete token')} `}
                    <Tooltip
                        content={props.tokenId}
                        data-test="delete-modal-tooltip"
                    >
                        { sprintf(_("'%(tokenId)s'"), { tokenId: smartTrim(props.tokenId, 12) }) }
                    </Tooltip>
                    {` ${sprintf(_('for user %(tokenOwner)s?'), { tokenOwner: props.tokenOwner })}`}
                    <div
                        style={{ paddingTop: '1px' }}
                        data-test="confirm-msg"
                    >
                        {_('You cannot undo this action.')}
                    </div>
                </div>
            </Modal.Body>
            <Modal.Footer>
                <Button
                    data-test-name={'cancel-btn'}
                    onClick={props.handleClose}
                    label={_('Cancel')}
                    autoFocus
                />
                <Button
                    appearance="primary"
                    data-test-name={'delete-btn'}
                    disabled={props.isWorking}
                    onClick={props.handleDelete}
                    label={props.isWorking ? _('Deleting...') : _('Delete')}
                />
            </Modal.Footer>
        </Modal>
    </div>
);

DeleteToken.propTypes = {
    open: PropTypes.bool,
    isWorking: PropTypes.bool,
    errorMessage: PropTypes.string,
    handleClose: PropTypes.func.isRequired,
    handleDelete: PropTypes.func.isRequired,
    tokenId: PropTypes.string.isRequired,
    tokenOwner: PropTypes.string.isRequired,
};

DeleteToken.defaultProps = {
    open: false,
    isWorking: false,
    errorMessage: '',
};

export default DeleteToken;
