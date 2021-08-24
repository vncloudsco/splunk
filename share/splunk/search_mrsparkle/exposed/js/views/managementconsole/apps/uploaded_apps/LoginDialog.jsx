import _ from 'underscore';
import PropTypes from 'prop-types';
import React, { Component } from 'react';
import Text from '@splunk/react-ui/Text';
import Link from '@splunk/react-ui/Link';
import Switch from '@splunk/react-ui/Switch';
import Button from '@splunk/react-ui/Button';
import AppDialog from './AppDialog/AppDialog';

const STRINGS = {
    CANCEL_BUTTON: _('Cancel').t(),
    LOGIN_BUTTON: _('Login').t(),
    DIALOG_TITLE: _('Login and Upload').t(),
};

class LoginDialog extends Component {
    constructor(props) {
        super(props);

        this.state = {
            username: '',
            password: '',
            disabled: false,
        };
    }

    componentWillReceiveProps(nextProps) {
        // This will be called every time LoginDialog is passed new props
        // Clear the username and password textboxes every time the modal is opened
        if (!this.props.loginDialogOpen && nextProps.loginDialogOpen) {
            this.setState({
                username: '',
                password: '',
                disabled: false,
            });
        }
    }

    handleLogin = (e) => {
        e.preventDefault();
        // disable button during login
        this.setState({ disabled: true });
        this.props.onLogin(this.state.username, this.state.password)
            .always(() => {
                this.setState({ disabled: false });
            });
    }

    handleFormChange = (e, { value }) => {
        if (e.target.name === 'username') {
            this.setState({
                username: value,
            });
        } else if (e.target.name === 'password') {
            this.setState({
                password: value,
            });
        } else {
            this.props.onConsentToggle('consent');
        }
    }

    render() {
        const {
            consent,
            loginDialogOpen,
            status,
            responseMessage,
            onRequestClose,
        } = this.props;

        const cancelButtonProps = {
            label: STRINGS.CANCEL_BUTTON,
            onClick: onRequestClose,
        };

        const loginButtonProps = {
            label: STRINGS.LOGIN_BUTTON,
            onClick: this.handleLogin,
            appearance: 'primary',
            disabled: this.state.disabled || !consent ||
                !this.state.username || !this.state.password,
        };

        const appDialogProps = {
            title: STRINGS.DIALOG_TITLE,
            open: loginDialogOpen,
            onRequestClose,
        };

        const appDialogBodyProps = {
            status,
            responseMessage,
        };

        return (
            <div data-test="UploadedApps-LoginDialog" >
                <AppDialog {...appDialogProps} >
                    <AppDialog.Body {...appDialogBodyProps}>
                        Enter your Splunk.com username and password to upload an app. These credentials are required
                        so that Splunk can complete a pre-installation validation of your app.
                        <br />
                        <br />
                        <Text
                            placeholder="Username"
                            name="username"
                            value={this.state.username}
                            onChange={this.handleFormChange}
                            style={{ width: '250px', marginBottom: '10px' }}
                            autoFocus
                            data-test="UploadedApps-LoginDialog-Username"
                        />
                        <Text
                            placeholder="Password"
                            name="password"
                            value={this.state.password}
                            onChange={this.handleFormChange}
                            style={{ width: '250px' }}
                            type="password"
                            data-test="UploadedApps-LoginDialog-Password"
                        />
                        <Link
                            to="http://www.splunk.com/page/lost_password"
                            openInNewContext
                        >
                            Forgot your password?
                        </Link>
                        <br />
                        <br />
                        You agree that your upload and submission is subject to the Splunk Cloud Terms of Service and
                        Splunk’s review, testing or installation approval will not relieve you of any of your
                        responsibilities thereunder. By uploading your app, you hereby grant Splunk a worldwide,
                        royalty free, non-exclusive license to access, use, reproduce, perform, display, and test your
                        app to complete a pre-installation validation of your app. Splunk disclaims any warranty
                        related to its review, testing or installation approval of your app.
                        <br />
                        <br />
                        <Switch
                            onClick={this.handleFormChange}
                            appearance="checkbox"
                            size="medium"
                            selected={consent}
                            value="Consent"
                        >
                            <div style={{ width: '420px' }}>
                                I have read the above terms and conditions and agree to be bound by them. I accept that
                                Splunk will securely send my login credentials over the Internet to splunk.com
                            </div>
                        </Switch>
                    </AppDialog.Body>
                    <AppDialog.Footer>
                        <Button data-test="UploadedApps-LoginDialog-CancelButton" {...cancelButtonProps} />
                        <Button data-test="UploadedApps-LoginDialog-LoginButton" {...loginButtonProps} />
                    </AppDialog.Footer>
                </AppDialog>
            </div>
        );
    }
}

LoginDialog.propTypes = {
    loginDialogOpen: PropTypes.bool,
    responseMessage: PropTypes.oneOfType([PropTypes.string, PropTypes.array]),
    status: PropTypes.string,
    consent: PropTypes.bool,
    onLogin: PropTypes.func.isRequired,
    onConsentToggle: PropTypes.func.isRequired,
    onRequestClose: PropTypes.func.isRequired,
};

LoginDialog.defaultProps = {
    consent: false,
    loginDialogOpen: false,
    responseMessage: '',
    status: undefined,
};

export default LoginDialog;
