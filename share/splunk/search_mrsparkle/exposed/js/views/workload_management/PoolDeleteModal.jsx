import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import P from '@splunk/react-ui/Paragraph';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import Message from '@splunk/react-ui/Message';

const PoolDeleteModal = (props) => {
    const {
        poolDeleteModalOpen,
        poolDeleteModalState,
        handlePoolDeleteModalClose,
        handlePoolDeleteModalSubmit,
    } = props;

    return (
        <div {...createTestHook(module.id)} className="workload-pool-delete-modal">
            <Modal
                onRequestClose={poolDeleteModalState.wait ? null : handlePoolDeleteModalClose}
                open={poolDeleteModalOpen}
                style={{ width: '500px' }}
            >
                <Modal.Header
                    title={poolDeleteModalState.title}
                    onRequestClose={poolDeleteModalState.wait ? null : handlePoolDeleteModalClose}
                />
                <Modal.Body>
                    {poolDeleteModalState.backendErrorMsg ?
                        <Message fill type="error">
                            {poolDeleteModalState.backendErrorMsg}
                        </Message> : null
                    }
                    <P>{_('Are you sure about deleting this pool?').t()}</P>
                </Modal.Body>
                { poolDeleteModalState.wait ?
                    <Modal.Footer>
                        <WaitSpinner size="medium" />
                    </Modal.Footer> :
                    <Modal.Footer>
                        <Button
                            appearance="secondary"
                            onClick={handlePoolDeleteModalClose}
                            label={_('Cancel').t()}
                        />
                        <Button
                            appearance="primary"
                            value={poolDeleteModalState.poolModel}
                            onClick={handlePoolDeleteModalSubmit}
                            label={_('Delete').t()}
                        />
                    </Modal.Footer>
                }
            </Modal>
        </div>
    );
};

PoolDeleteModal.propTypes = {
    poolDeleteModalOpen: PropTypes.bool,
    poolDeleteModalState: PropTypes.shape({}).isRequired,
    handlePoolDeleteModalClose: PropTypes.func.isRequired,
    handlePoolDeleteModalSubmit: PropTypes.func.isRequired,
};

PoolDeleteModal.defaultProps = {
    poolDeleteModalOpen: false,
};

export default PoolDeleteModal;
