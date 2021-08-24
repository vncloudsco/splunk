import React from 'react';
import PropTypes from 'prop-types';

/**
 * Since all form inputs started to use React, we need to make sure the Message component is
 * rendered in React as well, otherwise it cause errors on React v16.
 *
 * However, we still need to keep the old messages.js {Backbone.View} for non-input views.
 *
 * We should consolidate messages.js and Message.jsx eventually.
 */
const Message = ({
    level,
    message,
    compact,
}) => (
    <div className={`splunk-message-container ${compact ? 'compact' : ''}`}>
        <div className={`alert alert-${level}`}>
            <i className="icon-alert" />
            {message}
        </div>
    </div>
);

Message.propTypes = {
    level: PropTypes.string.isRequired,
    message: PropTypes.string.isRequired,
    compact: PropTypes.bool,
};

Message.defaultProps = {
    compact: false,
};

export default Message;
