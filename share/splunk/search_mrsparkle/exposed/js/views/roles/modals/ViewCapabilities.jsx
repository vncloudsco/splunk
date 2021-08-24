import React from 'react';
import PropTypes from 'prop-types';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import { _ } from '@splunk/ui-utils/i18n';
import ViewCapabilities from '@splunk/view-capabilities';

const ViewCapabilitiesModal = props => (
    <div>
        <Modal
            data-test-name="view-capabilities-modal"
            onRequestClose={props.handleRequestClose}
            open={props.open}
            style={{ width: '80%' }}
        >
            <Modal.Header
                data-test-name="view-capabilities-modal-header"
                title={_('View Capabilities')}
                onRequestClose={props.handleRequestClose}
            />
            <Modal.Body
                data-test-name="view-capabilities-modal-body"
                style={{ backgroundColor: '#f2f5f4', paddingTop: 0 }}
            >
                <ViewCapabilities
                    entityType={'roles'}
                    entity={props.object[props.nameAttribute] || ''}
                />
            </Modal.Body>
            <Modal.Footer>
                <Button
                    data-test-name="view-capabilities-cancel"
                    onClick={props.handleRequestClose}
                    label={_('Cancel')}
                />
            </Modal.Footer>
        </Modal>
    </div>
);


ViewCapabilitiesModal.propTypes = {
    open: PropTypes.bool,
    object: PropTypes.shape({
        name: PropTypes.string.isRequired,
    }).isRequired,
    nameAttribute: PropTypes.string.isRequired,
    handleRequestClose: PropTypes.func.isRequired,
};

ViewCapabilitiesModal.defaultProps = {
    open: false,
};

export default ViewCapabilitiesModal;
