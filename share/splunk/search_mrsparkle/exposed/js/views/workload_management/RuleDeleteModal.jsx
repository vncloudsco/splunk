import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import P from '@splunk/react-ui/Paragraph';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import Message from '@splunk/react-ui/Message';

const RuleDeleteModal = (props) => {
    const {
        ruleDeleteModalOpen,
        ruleDeleteModalState,
        handleRuleDeleteModalClose,
        handleRuleDeleteModalSubmit,
    } = props;

    return (
        <div {...createTestHook(module.id)} className="workload-rule-delete-modal">
            <Modal
                onRequestClose={ruleDeleteModalState.wait ? null : handleRuleDeleteModalClose}
                open={ruleDeleteModalOpen}
                style={{ width: '500px' }}
            >
                <Modal.Header
                    title={ruleDeleteModalState.title}
                    onRequestClose={ruleDeleteModalState.wait ? null : handleRuleDeleteModalClose}
                />
                <Modal.Body>
                    {ruleDeleteModalState.backendErrorMsg ?
                        <Message fill type="error">
                            {ruleDeleteModalState.backendErrorMsg}
                        </Message> : null
                    }
                    <P>{_('Are you sure about deleting this rule?').t()}</P>
                </Modal.Body>
                { ruleDeleteModalState.wait ?
                    <Modal.Footer>
                        <WaitSpinner size="medium" />
                    </Modal.Footer> :
                    <Modal.Footer>
                        <Button
                            appearance="secondary"
                            onClick={handleRuleDeleteModalClose}
                            label={_('Cancel').t()}
                        />
                        <Button
                            appearance="primary"
                            value={ruleDeleteModalState.ruleModel}
                            onClick={handleRuleDeleteModalSubmit}
                            label={_('Delete').t()}
                        />
                    </Modal.Footer>
                }
            </Modal>
        </div>
    );
};

RuleDeleteModal.propTypes = {
    ruleDeleteModalOpen: PropTypes.bool,
    ruleDeleteModalState: PropTypes.shape({}).isRequired,
    handleRuleDeleteModalClose: PropTypes.func.isRequired,
    handleRuleDeleteModalSubmit: PropTypes.func.isRequired,
};

RuleDeleteModal.defaultProps = {
    ruleDeleteModalOpen: false,
};

export default RuleDeleteModal;
