import _ from 'underscore';
import PropTypes from 'prop-types';
import React, { Component } from 'react';
import File from '@splunk/react-ui/File';
import Button from '@splunk/react-ui/Button';
import AppDialog from './AppDialog/AppDialog';
import LoginDialog from './LoginDialog';

const STRINGS = {
    UPLOAD_APP: _('Upload App').t(),
    CLOSE: _('Close').t(),
};

class UploadAppButton extends Component {
    handleUploadButtonClick = (e) => {
        e.preventDefault();
        this.props.onLoginOpen();
    }

    handleAddFiles = (files) => {
        // Adding a file is allowed only if upload is not in progress
        // ie this.props.fileUploadPercent is undefined/non-zero
        if (!this.props.fileUploadPercent) {
            this.props.onAddFile(files[0]);
        }
    }

    handleUpload = (e) => {
        e.preventDefault();
        if (this.props.buttonLabel === STRINGS.CLOSE) {
            this.props.onRequestClose();
        } else {
            this.props.onRequestUpload();
        }
    }

    render() {
        const uploadButtonProps = {
            label: this.props.buttonLabel,
            onClick: this.handleUpload,
            appearance: 'primary',
            disabled: !this.props.filename || !!this.props.fileUploadPercent,
        };

        let appDialogProps = {
            title: STRINGS.UPLOAD_APP,
            open: this.props.uploadDialogOpen,
            dialogType: 'upload',
        };

        // Closing the modal allowed only if upload is not in progress
        // ie this.props.fileUploadPercent is undefined/non-zero
        if (!this.props.fileUploadPercent) {
            appDialogProps = {
                ...appDialogProps,
                onRequestClose: this.props.onRequestClose,
            };
        }

        const appDialogBodyProps = {
            status: this.props.status,
            responseMessage: this.props.responseMessage,
        };

        const loginDialogProps = {
            loginDialogOpen: this.props.loginDialogOpen,
            consent: this.props.consent,
            status: this.props.status,
            responseMessage: this.props.responseMessage,
            onLoginOpen: this.props.onLoginOpen,
            onLogin: this.props.onLogin,
            onConsentToggle: this.props.onConsentToggle,
            onRequestClose: this.props.onRequestClose,
        };

        return (
            <div data-test="UploadedApps-UploadAppButton">
                <div>
                    <Button onClick={this.handleUploadButtonClick} label={STRINGS.UPLOAD_APP} appearance="primary" />
                    &nbsp;
                </div>
                <AppDialog {...appDialogProps}>
                    <AppDialog.Body {...appDialogBodyProps}>
                        {
                            this.props.status !== 'success' &&
                            <File
                                onRequestAdd={this.handleAddFiles}
                                onRequestRemove={this.props.onRemoveFile}
                            >
                                {
                                    this.props.filename &&
                                    <File.Item
                                        error={this.props.status === 'error'}
                                        name={this.props.filename}
                                        uploadPercentage={this.props.fileUploadPercent}
                                    />
                                }
                            </File>
                        }
                    </AppDialog.Body>
                    <AppDialog.Footer>
                        <div>
                            <Button
                                {...uploadButtonProps}
                                data-test="UploadedApps-UploadCloseButton"
                            />
                            &nbsp;
                        </div>
                    </AppDialog.Footer>
                </AppDialog>
                <LoginDialog {...loginDialogProps} />
            </div>
        );
    }
}

UploadAppButton.propTypes = {
    uploadDialogOpen: PropTypes.bool.isRequired,
    status: PropTypes.string,
    responseMessage: PropTypes.oneOfType([PropTypes.string, PropTypes.array]),
    filename: PropTypes.string,
    fileUploadPercent: PropTypes.number,
    buttonLabel: PropTypes.string,
    loginDialogOpen: PropTypes.bool,
    consent: PropTypes.bool,
    onRequestUpload: PropTypes.func.isRequired,
    onRequestClose: PropTypes.func.isRequired,
    onAddFile: PropTypes.func.isRequired,
    onRemoveFile: PropTypes.func.isRequired,
    onLoginOpen: PropTypes.func.isRequired,
    onLogin: PropTypes.func.isRequired,
    onConsentToggle: PropTypes.func.isRequired,
};

UploadAppButton.defaultProps = {
    status: undefined,
    filename: '',
    responseMessage: '',
    fileUploadPercent: undefined,
    buttonLabel: undefined,
    consent: false,
    loginDialogOpen: false,
};

export default UploadAppButton;
