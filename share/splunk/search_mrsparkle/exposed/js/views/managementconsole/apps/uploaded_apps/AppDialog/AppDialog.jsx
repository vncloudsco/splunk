import PropTypes from 'prop-types';
import React from 'react';
import Modal from '@splunk/react-ui/Modal';
import Body from './Body';
import Footer from './Footer';

// Since this component only has the render function,
// it has been written as a React Pure Component
const AppDialog = props =>
    <Modal
        open={props.open}
        onRequestClose={props.onRequestClose}
        style={{ width: '500px' }}
        data-test="UploadedApps-AppDialog"
    >
        <Modal.Header
            title={props.title}
            onRequestClose={props.onRequestClose}
        />
        {props.children}
    </Modal>;

AppDialog.Footer = Footer;
AppDialog.Body = Body;

AppDialog.propTypes = {
    open: PropTypes.bool.isRequired,
    title: PropTypes.string,
    children: PropTypes.node,
    onRequestClose: PropTypes.func,
};

AppDialog.defaultProps = {
    title: undefined,
    children: undefined,
    onRequestClose: undefined,
};

export default AppDialog;
