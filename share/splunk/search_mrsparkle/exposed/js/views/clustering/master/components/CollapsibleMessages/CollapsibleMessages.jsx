import React from 'react';
import PropTypes from 'prop-types';
import CollapsiblePanel from '@splunk/react-ui/CollapsiblePanel';
import _ from 'underscore';
import P from '@splunk/react-ui/Paragraph';
import { createTestHook } from 'util/test_support';

const CollapsibleMessages = (props) => {
    let messages = props.messages;
    messages = _.isEmpty(messages) ? _('No messages').t() : messages;
    const pStyle = {
        padding: '10px',
        whiteSpace: 'pre-wrap',
        maxHeight: '200px',
        overflowY: 'auto',
    };

    return (
        <CollapsiblePanel
            title="Rolling Status Messages"
            {...createTestHook(null, 'messages-panel')}
        >
            <P
                style={pStyle}
                {...createTestHook(null, 'messages')}
            >{messages}</P>
        </CollapsiblePanel>
    );
};

CollapsibleMessages.propTypes = {
    messages: PropTypes.string,
};

CollapsibleMessages.defaultProps = {
    messages: '',
};

export default CollapsibleMessages;