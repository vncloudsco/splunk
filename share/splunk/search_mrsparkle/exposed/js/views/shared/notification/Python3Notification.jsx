import React from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import P from '@splunk/react-ui/Paragraph';
import Link from '@splunk/react-ui/Link';

const cssStyles = {
    paragraph: {
        textAlign: 'justify',
    },
};

const Python3Notification = ({ open, docLink, handleClose }) => (
    <Modal
        open={open}
        onRequestClose={() => handleClose()}
        data-test-name="python3-notification-modal"
    >
        <Modal.Header
            title={_('Important changes coming!')}
            onRequestClose={() => handleClose()}
        />
        <Modal.Body>
            <P style={cssStyles.paragraph}>
                {`${_('To prepare for the End of Life of Python 2.7 in January 2020, Splunk will migrate its \n' +
                'code base to support Python 3.7. We are working to make the transition to Python 3.7 \n' +
                'as seamless as possible, but some changes might affect your deployment and your \n' +
                'use of apps in future releases of Splunk software. We recommend that you read through our')} `}
                <Link
                    to={docLink}
                    openInNewContext
                >
                    {_('Python Migration documentation')}
                </Link>
                {` ${_('and')} `}
                <Link to="https://answers.splunk.com/topics/python3.html" openInNewContext>
                    {_('this Splunk Answers topic')}
                </Link>
                {` ${_('to stay informed of important information related to this migration and other related \n' +
                'changes.')}`}
            </P>
        </Modal.Body>
        <Modal.Footer>
            <Button
                appearance="secondary"
                onClick={() => handleClose('false')}
                label={_("Don't show me this again")}
            />
            <Button
                appearance="primary"
                onClick={() => handleClose()}
                label={_('Remind me in 2 weeks')}
            />
        </Modal.Footer>
    </Modal>
);

Python3Notification.propTypes = {
    open: PropTypes.bool.isRequired,
    docLink: PropTypes.string.isRequired,
    handleClose: PropTypes.func.isRequired,
};

export default Python3Notification;