import React from 'react';
import PropTypes from 'prop-types';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';
import Button from '@splunk/react-ui/Button';
import { _ } from '@splunk/ui-utils/i18n';
import { createTestHook } from 'util/test_support';

const Confirmation = (props) => {
    const { open, confirmMsg, confirmButtonLabel } = props;
    return (
        <Modal
            onRequestClose={props.onConfirmCancel}
            open={open}
            style={{ width: '400px' }}
            {...createTestHook(null, 'ArchiveRestoreConfirmationModal')}
        >
            <Modal.Header
                title={_('Confirmation')}
                onRequestClose={props.onConfirmCancel}
            />
            <Modal.Body>
                <Message type="warning">
                    {confirmMsg}
                </Message>
                <div style={{ textAlign: 'right' }}>
                    <Button
                        appearance="secondary"
                        onClick={props.onConfirmCancel}
                        size="small"
                        label={_('Cancel')}
                        {...createTestHook(null, 'ArchiveRestoreConfirmationCancelBtn')}
                    />
                    <Button
                        appearance="primary"
                        onClick={props.onConfirm}
                        size="small"
                        disabled={props.processing}
                        label={confirmButtonLabel}
                        {...createTestHook(null, 'ArchiveRestoreConfirmationConfirmBtn')}
                    />
                </div>
            </Modal.Body>
        </Modal>
    );
};

Confirmation.propTypes = {
    open: PropTypes.bool,
    processing: PropTypes.bool,
    confirmMsg: PropTypes.string,
    confirmButtonLabel: PropTypes.string,
    onConfirmCancel: PropTypes.func.isRequired,
    onConfirm: PropTypes.func.isRequired,
};

Confirmation.defaultProps = {
    open: false,
    processing: false,
    confirmMsg: _('Are you sure?'),
    confirmButtonLabel: _('Ok'),
};

export default Confirmation;