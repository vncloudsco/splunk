import React from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Tooltip from '@splunk/react-ui/Tooltip';
import { createTestHook } from '@splunk/base-lister/utils/TestSupport';
import { sprintf, smartTrim } from '@splunk/ui-utils/format';

const TokenStatusModal = props => (
    <Modal
        onRequestClose={props.handleClose}
        open={props.open}
        style={{ minWidth: '500px' }}
        {...createTestHook('TokenStatusModal')}
    >
        <Modal.Header title={props.modalTitle} onRequestClose={props.handleClose} />
        <Modal.Body>
            {props.errorMessage && (
                <Message type="error">{props.errorMessage}</Message>
            )}
            <div data-test="status-modal-content" >
                {sprintf(
                    `${_('Are you sure you want to %(enableOrDisable)s token')} `,
                    { enableOrDisable: props.enableOrDisable })
                }
                <Tooltip
                    content={props.tokenId}
                    data-test="status-modal-tooltip"
                >
                    { sprintf(_("'%(tokenId)s'"), { tokenId: smartTrim(props.tokenId, 12) }) }
                </Tooltip>
                {` ${sprintf(_('for user %(tokenOwner)s?'), { tokenOwner: props.tokenOwner })}`}
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
                data-test-name={'change-status-btn'}
                disabled={props.isWorking}
                onClick={props.handleChangeStatus}
                label={props.changeStatusButtonLabel}
            />
        </Modal.Footer>
    </Modal>
);

TokenStatusModal.propTypes = {
    open: PropTypes.bool,
    isWorking: PropTypes.bool,
    errorMessage: PropTypes.string,
    changeStatusButtonLabel: PropTypes.string.isRequired,
    modalTitle: PropTypes.string.isRequired,
    handleClose: PropTypes.func.isRequired,
    handleChangeStatus: PropTypes.func.isRequired,
    tokenId: PropTypes.string.isRequired,
    tokenOwner: PropTypes.string.isRequired,
    enableOrDisable: PropTypes.string.isRequired,
};

TokenStatusModal.defaultProps = {
    open: false,
    isWorking: false,
    errorMessage: '',
};

export default TokenStatusModal;
