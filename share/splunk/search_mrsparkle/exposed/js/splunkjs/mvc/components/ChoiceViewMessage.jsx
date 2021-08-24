import React from 'react';
import PropTypes from 'prop-types';
import Tooltip from '@splunk/react-ui/Tooltip';
import { createTestHook } from 'util/test_support';

const ChoiceViewMessage = ({
    message,
    originalMessage,
}) => (
    <Tooltip
        content={originalMessage}
        {...createTestHook(module.id)}
    >
        <div
            style={{
                fontSize: 11,
                height: 0,
                overflow: 'visible',
            }}
        >{message}</div>
    </Tooltip>
);

ChoiceViewMessage.propTypes = {
    message: PropTypes.string,
    originalMessage: PropTypes.string,
};

ChoiceViewMessage.defaultProps = {
    message: '',
    originalMessage: '',
};

export default ChoiceViewMessage;
