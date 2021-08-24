import PropTypes from 'prop-types';
import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';
import { createTestHook } from 'util/test_support';

// This component is mainly used for showing form validation errors/warnings.

const FormMessage = ({
    active,
    type,
    message,
}) => (
    active ? (
        <ControlGroup label="" controlsLayout="none" {...createTestHook(module.id)}>
            <Message type={type}>{message}</Message>
        </ControlGroup>
    ) : null);

FormMessage.propTypes = {
    active: PropTypes.bool.isRequired,
    type: PropTypes.string.isRequired,
    message: PropTypes.string.isRequired,
};

export default FormMessage;
