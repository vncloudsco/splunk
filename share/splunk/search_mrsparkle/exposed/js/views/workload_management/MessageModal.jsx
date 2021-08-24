import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';

const MessageModal = (props) => {
    const {
        messageModalState,
        handleMessageModalClose,
    } = props;

    let body = null;
    if (messageModalState.open) {
        body = (
            <Modal.Body>
                <Message type={messageModalState.type}>{_(messageModalState.message).t()}</Message>
            </Modal.Body>
        );
    }

    return (
        <div {...createTestHook(module.id)} className="workload-message-modal">
            { messageModalState.closeable ?
                <Modal
                    onRequestClose={handleMessageModalClose}
                    open={messageModalState.open}
                    style={{ width: '500px' }}
                >
                    <Modal.Header title={_(messageModalState.title).t()} onRequestClose={handleMessageModalClose} />
                    { body }
                </Modal>
            :
                <Modal open={messageModalState.open} style={{ width: '500px' }} >
                    <Modal.Header title={_(messageModalState.title).t()} />
                    { body }
                </Modal>
            }
        </div>
    );
};

MessageModal.propTypes = {
    messageModalState: PropTypes.shape({}).isRequired,
    handleMessageModalClose: PropTypes.func.isRequired,
};

export default MessageModal;