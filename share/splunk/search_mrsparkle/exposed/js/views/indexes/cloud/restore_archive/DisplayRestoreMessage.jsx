import React from 'react';
import PropTypes from 'prop-types';
import Message from '@splunk/react-ui/Message';

const DisplayRestoreMessage = (props) => {
    const { retrieveMsg } = props;
    return (
        <div>
            <Message
                fill
                type={retrieveMsg.type}
            >
                {retrieveMsg.msg}
            </Message>
        </div>
    );
};

DisplayRestoreMessage.propTypes = {
    retrieveMsg: PropTypes.shape({
        type: PropTypes.string,
        msg: PropTypes.string,
    }),
};

DisplayRestoreMessage.defaultProps = {
    retrieveMsg: {
        type: 'info',
        msg: '',
    },
};

export default DisplayRestoreMessage;