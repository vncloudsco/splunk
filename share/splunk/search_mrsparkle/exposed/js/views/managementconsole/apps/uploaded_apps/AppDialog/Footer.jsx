import PropTypes from 'prop-types';
import React from 'react';
import Modal from '@splunk/react-ui/Modal';

// Since this component only has the render function,
// it has been written as a React Pure Component
const Footer = props =>
    <Modal.Footer data-test="UploadedApps-AppDialog-Footer">
        {props.children}
    </Modal.Footer>;

Footer.propTypes = {
    children: PropTypes.node,
};

Footer.defaultProps = {
    children: undefined,
};

export default Footer;
